#!/usr/bin/env python3
"""
Investigation script for lcorp_007 dashboard issue
=================================================

This script investigates why user lcorp_007 and team_lcorp_group data
is not appearing in the dashboard despite being stored in DynamoDB.

The issue seems to be in the data flow between:
1. DynamoDB storage (working)
2. CloudWatch metrics publishing (potentially broken)
3. Dashboard data retrieval (not getting the data)
"""

import boto3
import json
from datetime import datetime, date, timedelta
from decimal import Decimal

# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def investigate_lcorp_007_issue():
    """
    Comprehensive investigation of lcorp_007 dashboard issue
    """
    print("=" * 60)
    print("INVESTIGATING LCORP_007 DASHBOARD ISSUE")
    print("=" * 60)
    
    # AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    iam = boto3.client('iam', region_name='eu-west-1')
    
    # Target user and team
    target_user = 'lcorp_007'
    target_team = 'team_lcorp_group'
    
    print(f"\n1. CHECKING DYNAMODB DATA FOR {target_user}")
    print("-" * 50)
    
    # Check DynamoDB table for recent data
    table = dynamodb.Table('bedrock_user_daily_usage')
    
    # Check last 7 days of data
    for days_back in range(7):
        check_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        try:
            response = table.get_item(
                Key={
                    'user_id': target_user,
                    'date': check_date
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                print(f"  {check_date}: {item.get('request_count', 0)} requests, team: {item.get('team', 'unknown')}, status: {item.get('status', 'unknown')}")
            else:
                print(f"  {check_date}: No data found")
                
        except Exception as e:
            print(f"  {check_date}: Error - {str(e)}")
    
    print(f"\n2. CHECKING IAM GROUP MEMBERSHIP FOR {target_team}")
    print("-" * 50)
    
    try:
        # Check if user is in the IAM group
        group_response = iam.get_group(GroupName=target_team)
        users_in_group = [user['UserName'] for user in group_response['Users']]
        
        print(f"  Users in {target_team}: {users_in_group}")
        
        if target_user in users_in_group:
            print(f"  ✓ {target_user} is correctly in {target_team}")
        else:
            print(f"  ✗ {target_user} is NOT in {target_team}")
            
        # Check user tags
        try:
            user_tags_response = iam.list_user_tags(UserName=target_user)
            user_tags = {tag['Key']: tag['Value'] for tag in user_tags_response['Tags']}
            print(f"  {target_user} tags: {user_tags}")
        except Exception as e:
            print(f"  Error getting user tags: {str(e)}")
            
    except Exception as e:
        print(f"  Error checking IAM group: {str(e)}")
    
    print(f"\n3. CHECKING CLOUDWATCH METRICS FOR {target_user}")
    print("-" * 50)
    
    # Check CloudWatch metrics for the last 7 days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        # Check user-level metrics
        user_metrics = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': target_user
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        print(f"  User metrics datapoints: {len(user_metrics['Datapoints'])}")
        for datapoint in sorted(user_metrics['Datapoints'], key=lambda x: x['Timestamp']):
            print(f"    {datapoint['Timestamp'].strftime('%Y-%m-%d')}: {datapoint['Sum']} requests")
            
    except Exception as e:
        print(f"  Error getting user metrics: {str(e)}")
    
    try:
        # Check team-level metrics
        team_metrics = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'Team',
                    'Value': target_team
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        print(f"  Team metrics datapoints: {len(team_metrics['Datapoints'])}")
        for datapoint in sorted(team_metrics['Datapoints'], key=lambda x: x['Timestamp']):
            print(f"    {datapoint['Timestamp'].strftime('%Y-%m-%d')}: {datapoint['Sum']} requests")
            
    except Exception as e:
        print(f"  Error getting team metrics: {str(e)}")
    
    print(f"\n4. CHECKING ALL USERS IN {target_team}")
    print("-" * 50)
    
    try:
        group_response = iam.get_group(GroupName=target_team)
        all_users_in_team = [user['UserName'] for user in group_response['Users']]
        
        for user in all_users_in_team:
            print(f"\n  Checking user: {user}")
            
            # Check DynamoDB data for today
            today = date.today().isoformat()
            try:
                response = table.get_item(
                    Key={
                        'user_id': user,
                        'date': today
                    }
                )
                
                if 'Item' in response:
                    item = response['Item']
                    print(f"    DynamoDB today: {item.get('request_count', 0)} requests, team: {item.get('team', 'unknown')}")
                else:
                    print(f"    DynamoDB today: No data")
                    
            except Exception as e:
                print(f"    DynamoDB error: {str(e)}")
            
            # Check CloudWatch metrics for today
            try:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = datetime.utcnow()
                
                user_metrics_today = cloudwatch.get_metric_statistics(
                    Namespace='UserMetrics',
                    MetricName='BedrockUsage',
                    Dimensions=[
                        {
                            'Name': 'User',
                            'Value': user
                        }
                    ],
                    StartTime=today_start,
                    EndTime=today_end,
                    Period=3600,  # 1 hour
                    Statistics=['Sum']
                )
                
                total_today = sum(dp['Sum'] for dp in user_metrics_today['Datapoints'])
                print(f"    CloudWatch today: {total_today} requests ({len(user_metrics_today['Datapoints'])} datapoints)")
                
            except Exception as e:
                print(f"    CloudWatch error: {str(e)}")
    
    except Exception as e:
        print(f"  Error checking team users: {str(e)}")
    
    print(f"\n5. DASHBOARD DATA RETRIEVAL SIMULATION")
    print("-" * 50)
    
    # Simulate what the dashboard does to fetch data
    try:
        # Get first day of current month
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        
        print(f"  Simulating dashboard query from {start_of_month} to {now}")
        
        # Query metrics like the dashboard does
        monthly_metrics = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': target_user
                }
            ],
            StartTime=start_of_month,
            EndTime=now,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        total_monthly = sum(dp['Sum'] for dp in monthly_metrics['Datapoints'])
        print(f"  Dashboard would see: {total_monthly} total requests for {target_user} this month")
        print(f"  Datapoints: {len(monthly_metrics['Datapoints'])}")
        
        if len(monthly_metrics['Datapoints']) == 0:
            print(f"  ⚠️  NO CLOUDWATCH DATAPOINTS FOUND - This is the issue!")
            
    except Exception as e:
        print(f"  Dashboard simulation error: {str(e)}")
    
    print(f"\n6. COMPARING WITH WORKING USER (sap_003)")
    print("-" * 50)
    
    working_user = 'sap_003'
    
    try:
        # Check DynamoDB for working user
        today = date.today().isoformat()
        response = table.get_item(
            Key={
                'user_id': working_user,
                'date': today
            }
        )
        
        if 'Item' in response:
            item = response['Item']
            print(f"  {working_user} DynamoDB today: {item.get('request_count', 0)} requests, team: {item.get('team', 'unknown')}")
        else:
            print(f"  {working_user} DynamoDB today: No data")
        
        # Check CloudWatch for working user
        monthly_metrics_working = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': working_user
                }
            ],
            StartTime=start_of_month,
            EndTime=now,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        total_monthly_working = sum(dp['Sum'] for dp in monthly_metrics_working['Datapoints'])
        print(f"  {working_user} CloudWatch monthly: {total_monthly_working} requests ({len(monthly_metrics_working['Datapoints'])} datapoints)")
        
    except Exception as e:
        print(f"  Error comparing with working user: {str(e)}")
    
    print(f"\n7. DIAGNOSIS AND RECOMMENDATIONS")
    print("-" * 50)
    
    print("  Based on the investigation:")
    print("  1. If DynamoDB has data but CloudWatch doesn't → CloudWatch metrics publishing issue")
    print("  2. If IAM group membership is wrong → User provisioning issue")
    print("  3. If team field in DynamoDB is wrong → Team assignment issue")
    print("  4. If CloudWatch has data but dashboard doesn't show it → Dashboard query issue")
    
    print(f"\n  Next steps:")
    print(f"  - Check Lambda function logs for {target_user} requests")
    print(f"  - Verify CloudWatch metrics publishing in bedrock_usage_monitor")
    print(f"  - Check if team assignment is being updated correctly")
    print(f"  - Verify dashboard IAM permissions for CloudWatch access")

if __name__ == "__main__":
    investigate_lcorp_007_issue()
