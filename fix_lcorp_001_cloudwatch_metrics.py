#!/usr/bin/env python3
"""
Fix lcorp_001 CloudWatch metrics by manually publishing missing data from DynamoDB
"""

import boto3
import json
from datetime import datetime, date, timedelta

def fix_lcorp_001_metrics():
    """Manually publish CloudWatch metrics for lcorp_001 based on DynamoDB data"""
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    
    user_id = 'lcorp_001'
    
    print(f"FIXING CLOUDWATCH METRICS FOR {user_id}")
    print("=" * 60)
    
    # Get the last 7 days of DynamoDB data
    table = dynamodb.Table('bedrock_user_daily_usage')
    
    for days_back in range(7):  # Last 7 days
        target_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        try:
            # Get DynamoDB data for this date
            response = table.get_item(
                Key={'user_id': user_id, 'date': target_date}
            )
            
            if 'Item' in response:
                item = response['Item']
                request_count = item.get('request_count', 0)
                
                if request_count > 0:
                    print(f"📅 {target_date}: Found {request_count} requests in DynamoDB")
                    
                    # Check if CloudWatch metric already exists for this date
                    metric_date = datetime.strptime(target_date, '%Y-%m-%d')
                    start_time = metric_date
                    end_time = metric_date + timedelta(days=1)
                    
                    cw_response = cloudwatch.get_metric_statistics(
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
                    
                    existing_metric = 0
                    if cw_response['Datapoints']:
                        existing_metric = sum(dp['Sum'] for dp in cw_response['Datapoints'])
                    
                    if existing_metric == 0 or existing_metric < request_count:
                        print(f"   🔧 Publishing CloudWatch metric: {request_count} requests")
                        
                        # Publish the metric to CloudWatch
                        cloudwatch.put_metric_data(
                            Namespace='UserMetrics',
                            MetricData=[
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
                        )
                        
                        print(f"   ✅ Successfully published metric for {target_date}")
                    else:
                        print(f"   ✅ CloudWatch metric already exists: {existing_metric} requests")
                else:
                    print(f"📅 {target_date}: No requests in DynamoDB")
            else:
                print(f"📅 {target_date}: No DynamoDB record")
                
        except Exception as e:
            print(f"❌ Error processing {target_date}: {str(e)}")
    
    # Verify the fix worked
    print(f"\n🔍 VERIFYING FIX - CHECKING UPDATED CLOUDWATCH METRICS")
    print("-" * 50)
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)  # Last 30 days
        
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
            total = sum(dp['Sum'] for dp in response['Datapoints'])
            print(f"✅ Updated CloudWatch metrics for {user_id}:")
            print(f"   - Total requests this month: {total}")
            print(f"   - Number of data points: {len(response['Datapoints'])}")
            
            # Show recent datapoints
            sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
            for dp in sorted_datapoints[:5]:  # Show last 5 days
                print(f"   - {dp['Timestamp'].strftime('%Y-%m-%d')}: {dp['Sum']} requests")
                
            print(f"\n🎉 SUCCESS! {user_id} should now appear in the dashboard!")
        else:
            print(f"❌ Still no CloudWatch metrics found for {user_id}")
            
    except Exception as e:
        print(f"❌ Error verifying fix: {str(e)}")

if __name__ == "__main__":
    fix_lcorp_001_metrics()
