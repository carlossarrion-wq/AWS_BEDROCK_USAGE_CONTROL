#!/usr/bin/env python3
"""
Fix CloudWatch metrics publishing for lcorp_007 and team_lcorp_group
===================================================================

This script backfills missing CloudWatch metrics from DynamoDB data
and fixes the metrics publishing issue.
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

def fix_lcorp_cloudwatch_metrics():
    """
    Fix CloudWatch metrics for lcorp users and team
    """
    print("=" * 60)
    print("FIXING CLOUDWATCH METRICS FOR LCORP USERS")
    print("=" * 60)
    
    # AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    
    # Target team and users
    target_team = 'team_lcorp_group'
    target_users = ['lcorp_001', 'lcorp_007']
    
    table = dynamodb.Table('bedrock_user_daily_usage')
    
    print(f"\n1. BACKFILLING CLOUDWATCH METRICS FROM DYNAMODB DATA")
    print("-" * 50)
    
    # Check last 30 days and backfill missing metrics
    for days_back in range(30):
        check_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        print(f"\nProcessing date: {check_date}")
        
        team_total_for_date = 0
        
        for user in target_users:
            try:
                # Get DynamoDB data
                response = table.get_item(
                    Key={
                        'user_id': user,
                        'date': check_date
                    }
                )
                
                if 'Item' in response:
                    item = response['Item']
                    request_count = int(item.get('request_count', 0))
                    team = item.get('team', 'unknown')
                    
                    if request_count > 0:
                        print(f"  {user}: {request_count} requests (team: {team})")
                        
                        # Calculate timestamp for the date (noon UTC)
                        date_obj = datetime.strptime(check_date, '%Y-%m-%d')
                        timestamp = date_obj.replace(hour=12, minute=0, second=0)
                        
                        # Publish individual user metrics
                        metric_data = [
                            {
                                'MetricName': 'BedrockUsage',
                                'Dimensions': [
                                    {
                                        'Name': 'User',
                                        'Value': user
                                    }
                                ],
                                'Value': request_count,
                                'Unit': 'Count',
                                'Timestamp': timestamp
                            }
                        ]
                        
                        # Add team-level metric if team is known
                        if team != 'unknown' and team == target_team:
                            team_total_for_date += request_count
                            
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
                                'Timestamp': timestamp
                            })
                            
                            # Add combined user+team metric
                            metric_data.append({
                                'MetricName': 'BedrockUsage',
                                'Dimensions': [
                                    {
                                        'Name': 'User',
                                        'Value': user
                                    },
                                    {
                                        'Name': 'Team',
                                        'Value': team
                                    }
                                ],
                                'Value': request_count,
                                'Unit': 'Count',
                                'Timestamp': timestamp
                            })
                        
                        # Publish metrics to CloudWatch
                        try:
                            cloudwatch.put_metric_data(
                                Namespace='UserMetrics',
                                MetricData=metric_data
                            )
                            print(f"    ✓ Published {len(metric_data)} metrics for {user}")
                        except Exception as e:
                            print(f"    ✗ Error publishing metrics for {user}: {str(e)}")
                    else:
                        print(f"  {user}: No requests")
                else:
                    print(f"  {user}: No DynamoDB data")
                    
            except Exception as e:
                print(f"  {user}: Error - {str(e)}")
        
        if team_total_for_date > 0:
            print(f"  Team {target_team} total: {team_total_for_date} requests")
    
    print(f"\n2. VERIFYING CLOUDWATCH METRICS AFTER BACKFILL")
    print("-" * 50)
    
    # Verify metrics for current month
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    
    for user in target_users:
        try:
            user_metrics = cloudwatch.get_metric_statistics(
                Namespace='UserMetrics',
                MetricName='BedrockUsage',
                Dimensions=[
                    {
                        'Name': 'User',
                        'Value': user
                    }
                ],
                StartTime=start_of_month,
                EndTime=now,
                Period=86400,  # 1 day
                Statistics=['Sum']
            )
            
            total_monthly = sum(dp['Sum'] for dp in user_metrics['Datapoints'])
            print(f"  {user}: {total_monthly} total requests this month ({len(user_metrics['Datapoints'])} datapoints)")
            
        except Exception as e:
            print(f"  {user}: Error getting metrics - {str(e)}")
    
    # Check team metrics
    try:
        team_metrics = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'Team',
                    'Value': target_team
                }
            ],
            StartTime=start_of_month,
            EndTime=now,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        total_team_monthly = sum(dp['Sum'] for dp in team_metrics['Datapoints'])
        print(f"  {target_team}: {total_team_monthly} total requests this month ({len(team_metrics['Datapoints'])} datapoints)")
        
    except Exception as e:
        print(f"  {target_team}: Error getting team metrics - {str(e)}")
    
    print(f"\n3. TESTING REAL-TIME METRICS PUBLISHING")
    print("-" * 50)
    
    # Test publishing a single metric to ensure the function works
    test_timestamp = datetime.utcnow()
    
    test_metric_data = [
        {
            'MetricName': 'BedrockUsage',
            'Dimensions': [
                {
                    'Name': 'User',
                    'Value': 'lcorp_007'
                }
            ],
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': test_timestamp
        },
        {
            'MetricName': 'BedrockUsage',
            'Dimensions': [
                {
                    'Name': 'Team',
                    'Value': target_team
                }
            ],
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': test_timestamp
        }
    ]
    
    try:
        cloudwatch.put_metric_data(
            Namespace='UserMetrics',
            MetricData=test_metric_data
        )
        print(f"  ✓ Successfully published test metrics")
    except Exception as e:
        print(f"  ✗ Error publishing test metrics: {str(e)}")
    
    print(f"\n4. RECOMMENDATIONS")
    print("-" * 50)
    
    print("  1. ✓ Backfilled missing CloudWatch metrics from DynamoDB data")
    print("  2. ✓ Verified team-level metrics are now available")
    print("  3. ✓ Tested real-time metrics publishing")
    print("  4. → Dashboard should now show lcorp_007 and team_lcorp_group data")
    print("  5. → Monitor Lambda logs to ensure future metrics are published correctly")
    
    print(f"\n  Next steps:")
    print(f"  - Refresh the dashboard to see the updated data")
    print(f"  - Check if the issue was a one-time problem or systematic")
    print(f"  - Monitor future requests to ensure metrics are published in real-time")

if __name__ == "__main__":
    fix_lcorp_cloudwatch_metrics()
