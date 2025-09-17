#!/usr/bin/env python3
"""
Investigate Data Discrepancy: CloudWatch vs DynamoDB
===================================================

This script compares data between CloudWatch and DynamoDB to understand
why CloudWatch might have more historical data than DynamoDB.

Possible scenarios:
1. DynamoDB records are being deleted/expired (TTL)
2. CloudWatch has data from a different source
3. DynamoDB table was recreated but CloudWatch retained old data
4. Different systems are writing to CloudWatch vs DynamoDB
"""

import boto3
import json
from datetime import datetime, date, timedelta
from decimal import Decimal

def investigate_data_discrepancy(days_back=30):
    """
    Compare CloudWatch and DynamoDB data to find discrepancies
    
    Args:
        days_back: Number of days to compare
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    
    table = dynamodb.Table('bedrock_user_daily_usage')
    
    print(f"🔍 INVESTIGATING DATA DISCREPANCY: CloudWatch vs DynamoDB")
    print("=" * 70)
    print(f"📅 Analyzing last {days_back} days")
    print()
    
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Get all users from both sources
    cloudwatch_users = get_cloudwatch_users(cloudwatch, start_date, end_date)
    dynamodb_users = get_dynamodb_users(table, start_date, end_date)
    
    all_users = set(cloudwatch_users.keys()) | set(dynamodb_users.keys())
    
    print(f"📊 DATA SUMMARY")
    print("-" * 50)
    print(f"CloudWatch users found: {len(cloudwatch_users)}")
    print(f"DynamoDB users found: {len(dynamodb_users)}")
    print(f"Total unique users: {len(all_users)}")
    print()
    
    # Analyze each user
    discrepancies = []
    
    for user_id in sorted(all_users):
        print(f"👤 ANALYZING USER: {user_id}")
        print("-" * 40)
        
        cw_data = cloudwatch_users.get(user_id, {})
        db_data = dynamodb_users.get(user_id, {})
        
        cw_total = sum(cw_data.values())
        db_total = sum(db_data.values())
        
        print(f"CloudWatch total: {cw_total}")
        print(f"DynamoDB total: {db_total}")
        print(f"Difference: {cw_total - db_total}")
        
        if cw_total != db_total:
            discrepancies.append({
                'user_id': user_id,
                'cloudwatch_total': cw_total,
                'dynamodb_total': db_total,
                'difference': cw_total - db_total,
                'cloudwatch_days': len(cw_data),
                'dynamodb_days': len(db_data)
            })
        
        # Show day-by-day comparison
        all_dates = set(cw_data.keys()) | set(db_data.keys())
        if all_dates:
            print("Day-by-day comparison:")
            for date_str in sorted(all_dates):
                cw_value = cw_data.get(date_str, 0)
                db_value = db_data.get(date_str, 0)
                status = "✅" if cw_value == db_value else "❌"
                print(f"  {date_str}: CW={cw_value:3d}, DB={db_value:3d} {status}")
        
        print()
    
    # Summary of discrepancies
    print("🚨 DISCREPANCY ANALYSIS")
    print("=" * 50)
    
    if not discrepancies:
        print("✅ No discrepancies found - CloudWatch and DynamoDB data match!")
        return
    
    print(f"Found {len(discrepancies)} users with data discrepancies:")
    print()
    
    for disc in discrepancies:
        print(f"👤 {disc['user_id']}:")
        print(f"   CloudWatch: {disc['cloudwatch_total']} requests over {disc['cloudwatch_days']} days")
        print(f"   DynamoDB:   {disc['dynamodb_total']} requests over {disc['dynamodb_days']} days")
        print(f"   Difference: {disc['difference']:+d} (CloudWatch - DynamoDB)")
        
        if disc['difference'] > 0:
            print(f"   🔍 CloudWatch has MORE data than DynamoDB")
        else:
            print(f"   🔍 DynamoDB has MORE data than CloudWatch")
        print()
    
    # Analyze patterns
    print("🔍 PATTERN ANALYSIS")
    print("-" * 30)
    
    cw_more = [d for d in discrepancies if d['difference'] > 0]
    db_more = [d for d in discrepancies if d['difference'] < 0]
    
    print(f"Users where CloudWatch > DynamoDB: {len(cw_more)}")
    print(f"Users where DynamoDB > CloudWatch: {len(db_more)}")
    
    if cw_more:
        print("\n🔍 POSSIBLE REASONS CloudWatch has more data:")
        print("1. DynamoDB TTL is deleting old records")
        print("2. DynamoDB table was recreated but CloudWatch retained data")
        print("3. Multiple systems are writing to CloudWatch")
        print("4. CloudWatch data includes data from before DynamoDB implementation")
        
        # Check for TTL
        check_dynamodb_ttl(table)
    
    if db_more:
        print("\n🔍 POSSIBLE REASONS DynamoDB has more data:")
        print("1. Recent data hasn't been published to CloudWatch yet")
        print("2. CloudWatch publishing is failing for some users")
        print("3. CloudWatch metrics have expired or been deleted")

def get_cloudwatch_users(cloudwatch, start_date, end_date):
    """Get all users and their daily usage from CloudWatch"""
    
    print("📊 Scanning CloudWatch metrics...")
    
    users_data = {}
    
    try:
        # List all metrics in UserMetrics namespace
        response = cloudwatch.list_metrics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage'
        )
        
        user_dimensions = []
        for metric in response['Metrics']:
            for dimension in metric['Dimensions']:
                if dimension['Name'] == 'User':
                    user_dimensions.append(dimension['Value'])
        
        # Remove duplicates
        users = list(set(user_dimensions))
        print(f"Found {len(users)} users in CloudWatch")
        
        # Get data for each user
        for user_id in users:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='UserMetrics',
                    MetricName='BedrockUsage',
                    Dimensions=[
                        {
                            'Name': 'User',
                            'Value': user_id
                        }
                    ],
                    StartTime=datetime.combine(start_date, datetime.min.time()),
                    EndTime=datetime.combine(end_date, datetime.max.time()),
                    Period=86400,  # 1 day
                    Statistics=['Sum']
                )
                
                user_data = {}
                for datapoint in response['Datapoints']:
                    date_str = datapoint['Timestamp'].strftime('%Y-%m-%d')
                    user_data[date_str] = int(datapoint['Sum'])
                
                if user_data:
                    users_data[user_id] = user_data
                    
            except Exception as e:
                print(f"Error getting CloudWatch data for {user_id}: {str(e)}")
        
    except Exception as e:
        print(f"Error listing CloudWatch metrics: {str(e)}")
    
    return users_data

def get_dynamodb_users(table, start_date, end_date):
    """Get all users and their daily usage from DynamoDB"""
    
    print("📊 Scanning DynamoDB table...")
    
    users_data = {}
    
    try:
        # Scan the table for records in date range
        response = table.scan(
            FilterExpression='attribute_exists(request_count) AND request_count > :zero',
            ExpressionAttributeValues={':zero': 0}
        )
        
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression='attribute_exists(request_count) AND request_count > :zero',
                ExpressionAttributeValues={':zero': 0}
            )
            items.extend(response['Items'])
        
        print(f"Found {len(items)} records in DynamoDB")
        
        # Process items
        for item in items:
            try:
                user_id = item['user_id']
                date_str = item['date']
                request_count = int(item['request_count']) if isinstance(item['request_count'], Decimal) else item['request_count']
                
                # Filter by date range
                record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if start_date <= record_date <= end_date:
                    if user_id not in users_data:
                        users_data[user_id] = {}
                    users_data[user_id][date_str] = request_count
                    
            except Exception as e:
                print(f"Error processing DynamoDB item: {str(e)}")
        
    except Exception as e:
        print(f"Error scanning DynamoDB table: {str(e)}")
    
    return users_data

def check_dynamodb_ttl(table):
    """Check if DynamoDB table has TTL enabled"""
    
    print("\n🔍 Checking DynamoDB TTL settings...")
    
    try:
        dynamodb_client = boto3.client('dynamodb', region_name='eu-west-1')
        
        response = dynamodb_client.describe_time_to_live(
            TableName=table.table_name
        )
        
        ttl_description = response.get('TimeToLiveDescription', {})
        ttl_status = ttl_description.get('TimeToLiveStatus', 'DISABLED')
        
        if ttl_status == 'ENABLED':
            ttl_attribute = ttl_description.get('AttributeName', 'unknown')
            print(f"⚠️  TTL is ENABLED on attribute '{ttl_attribute}'")
            print("   This could explain why DynamoDB has less historical data!")
            
            # Check a sample record to see TTL values
            try:
                sample_response = table.scan(Limit=1)
                if sample_response['Items']:
                    sample_item = sample_response['Items'][0]
                    if ttl_attribute in sample_item:
                        ttl_value = sample_item[ttl_attribute]
                        ttl_date = datetime.fromtimestamp(int(ttl_value))
                        print(f"   Sample TTL expiration: {ttl_date}")
                        
                        days_until_expiry = (ttl_date - datetime.now()).days
                        print(f"   Days until expiry: {days_until_expiry}")
            except Exception as e:
                print(f"   Error checking TTL values: {str(e)}")
        else:
            print("✅ TTL is DISABLED - not the cause of data discrepancy")
            
    except Exception as e:
        print(f"Error checking TTL: {str(e)}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Investigate data discrepancy between CloudWatch and DynamoDB')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
    
    args = parser.parse_args()
    
    investigate_data_discrepancy(args.days)

if __name__ == "__main__":
    main()
