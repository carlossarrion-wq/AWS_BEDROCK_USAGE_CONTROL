#!/usr/bin/env python3
"""
Backfill CloudWatch Metrics from DynamoDB Data
==============================================

This script reads existing usage data from DynamoDB and publishes it to CloudWatch
to ensure the dashboard shows historical data immediately.

Usage:
    python backfill_cloudwatch_metrics.py [--days N] [--user USER_ID] [--dry-run]

Options:
    --days N        Number of days to backfill (default: 30)
    --user USER_ID  Backfill only for specific user (default: all users)
    --dry-run       Show what would be done without actually publishing metrics
"""

import boto3
import json
import argparse
from datetime import datetime, date, timedelta
from decimal import Decimal
import time

# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def backfill_cloudwatch_metrics(days_back=30, specific_user=None, dry_run=False):
    """
    Backfill CloudWatch metrics from DynamoDB data
    
    Args:
        days_back: Number of days to backfill
        specific_user: If provided, only backfill for this user
        dry_run: If True, show what would be done without actually publishing
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    
    table = dynamodb.Table('bedrock_user_daily_usage')
    
    print(f"🔄 BACKFILLING CLOUDWATCH METRICS")
    print("=" * 60)
    print(f"📅 Days to backfill: {days_back}")
    print(f"👤 User filter: {specific_user or 'All users'}")
    print(f"🧪 Dry run mode: {'Yes' if dry_run else 'No'}")
    print()
    
    total_metrics_published = 0
    total_users_processed = 0
    errors = []
    
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"📊 Processing data from {start_date} to {end_date}")
    print("-" * 60)
    
    # Scan DynamoDB table for all records in date range
    scan_kwargs = {
        'FilterExpression': 'attribute_exists(request_count) AND request_count > :zero',
        'ExpressionAttributeValues': {':zero': 0}
    }
    
    if specific_user:
        scan_kwargs['FilterExpression'] += ' AND user_id = :user_id'
        scan_kwargs['ExpressionAttributeValues'][':user_id'] = specific_user
    
    try:
        # Scan the table
        response = table.scan(**scan_kwargs)
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], **scan_kwargs)
            items.extend(response['Items'])
        
        print(f"📋 Found {len(items)} records to process")
        print()
        
        # Group items by user for better organization
        users_data = {}
        for item in items:
            user_id = item['user_id']
            item_date = item['date']
            
            # Filter by date range
            try:
                record_date = datetime.strptime(item_date, '%Y-%m-%d').date()
                if start_date <= record_date <= end_date:
                    if user_id not in users_data:
                        users_data[user_id] = []
                    users_data[user_id].append(item)
            except ValueError:
                print(f"⚠️  Invalid date format for {user_id}: {item_date}")
                continue
        
        print(f"👥 Processing {len(users_data)} users")
        print()
        
        # Process each user
        for user_id, user_records in users_data.items():
            print(f"🔍 Processing user: {user_id}")
            total_users_processed += 1
            user_metrics_published = 0
            
            # Sort records by date
            user_records.sort(key=lambda x: x['date'])
            
            for record in user_records:
                try:
                    record_date = record['date']
                    request_count = int(record['request_count']) if isinstance(record['request_count'], Decimal) else record['request_count']
                    team = record.get('team', 'unknown')
                    
                    if request_count <= 0:
                        continue
                    
                    # Convert date to datetime for CloudWatch
                    metric_date = datetime.strptime(record_date, '%Y-%m-%d')
                    
                    print(f"   📅 {record_date}: {request_count} requests (team: {team})")
                    
                    if not dry_run:
                        # Check if metric already exists
                        existing_metric = check_existing_metric(cloudwatch, user_id, metric_date)
                        
                        if existing_metric >= request_count:
                            print(f"   ✅ Metric already exists with value {existing_metric}, skipping")
                            continue
                        
                        # Prepare metric data
                        metric_data = [
                            {
                                'MetricName': 'BedrockUsage',
                                'Dimensions': [
                                    {
                                        'Name': 'User',
                                        'Value': user_id
                                    }
                                ],
                                'Value': request_count,
                                'Unit': 'Count',
                                'Timestamp': metric_date
                            }
                        ]
                        
                        # Add team-level metric if team is known
                        if team != 'unknown':
                            metric_data.append({
                                'MetricName': 'BedrockUsage',
                                'Dimensions': [
                                    {
                                        'Name': 'Team',
                                        'Value': team
                                    }
                                ],
                                'Value': request_count,
                                'Unit': 'Count',
                                'Timestamp': metric_date
                            })
                            
                            # Add combined user+team metric
                            metric_data.append({
                                'MetricName': 'BedrockUsage',
                                'Dimensions': [
                                    {
                                        'Name': 'User',
                                        'Value': user_id
                                    },
                                    {
                                        'Name': 'Team',
                                        'Value': team
                                    }
                                ],
                                'Value': request_count,
                                'Unit': 'Count',
                                'Timestamp': metric_date
                            })
                        
                        # Publish metrics to CloudWatch
                        cloudwatch.put_metric_data(
                            Namespace='UserMetrics',
                            MetricData=metric_data
                        )
                        
                        user_metrics_published += len(metric_data)
                        total_metrics_published += len(metric_data)
                        
                        print(f"   ✅ Published {len(metric_data)} metrics")
                        
                        # Rate limiting to avoid throttling
                        time.sleep(0.1)
                    else:
                        print(f"   🧪 Would publish {request_count} requests for {record_date}")
                        user_metrics_published += 1
                        total_metrics_published += 1
                
                except Exception as e:
                    error_msg = f"Error processing {user_id} for date {record.get('date', 'unknown')}: {str(e)}"
                    print(f"   ❌ {error_msg}")
                    errors.append(error_msg)
            
            print(f"   📊 User {user_id}: {user_metrics_published} metrics {'would be ' if dry_run else ''}published")
            print()
    
    except Exception as e:
        print(f"❌ Error scanning DynamoDB table: {str(e)}")
        return False
    
    # Summary
    print("📈 BACKFILL SUMMARY")
    print("=" * 60)
    print(f"👥 Users processed: {total_users_processed}")
    print(f"📊 Total metrics {'would be ' if dry_run else ''}published: {total_metrics_published}")
    print(f"❌ Errors encountered: {len(errors)}")
    
    if errors:
        print("\n🚨 ERRORS:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
    
    if not dry_run and total_metrics_published > 0:
        print(f"\n🎉 SUCCESS! Published {total_metrics_published} metrics to CloudWatch")
        print("📊 Dashboard should now show historical data within 5-15 minutes")
    elif dry_run:
        print(f"\n🧪 DRY RUN COMPLETE! Would publish {total_metrics_published} metrics")
        print("💡 Run without --dry-run to actually publish the metrics")
    
    return len(errors) == 0

def check_existing_metric(cloudwatch, user_id, metric_date):
    """
    Check if a metric already exists for the given user and date
    
    Args:
        cloudwatch: CloudWatch client
        user_id: User ID to check
        metric_date: Date to check
        
    Returns:
        Existing metric value or 0 if not found
    """
    try:
        start_time = metric_date
        end_time = metric_date + timedelta(days=1)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': user_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            return sum(dp['Sum'] for dp in response['Datapoints'])
        
        return 0
        
    except Exception as e:
        print(f"   ⚠️  Error checking existing metric for {user_id}: {str(e)}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Backfill CloudWatch metrics from DynamoDB data')
    parser.add_argument('--days', type=int, default=30, help='Number of days to backfill (default: 30)')
    parser.add_argument('--user', type=str, help='Backfill only for specific user')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually publishing')
    
    args = parser.parse_args()
    
    success = backfill_cloudwatch_metrics(
        days_back=args.days,
        specific_user=args.user,
        dry_run=args.dry_run
    )
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
