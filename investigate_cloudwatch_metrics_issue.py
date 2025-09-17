#!/usr/bin/env python3
"""
Investigate why CloudWatch metrics are missing for lcorp_001 but working for sap_003
"""

import boto3
import json
from datetime import datetime, date, timedelta

def investigate_cloudwatch_issue():
    """Investigate CloudWatch metrics publishing issue"""
    
    # Initialize AWS clients
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    logs = boto3.client('logs', region_name='eu-west-1')
    
    users_to_check = ['lcorp_001', 'sap_003']
    
    print("INVESTIGATING CLOUDWATCH METRICS ISSUE")
    print("=" * 60)
    
    for user_id in users_to_check:
        print(f"\n🔍 CHECKING CLOUDWATCH METRICS FOR: {user_id}")
        print("-" * 50)
        
        # 1. Check if metrics exist in different namespaces
        namespaces_to_check = ['UserMetrics', 'AWS/Bedrock', 'BedrockUsage', 'Custom']
        
        for namespace in namespaces_to_check:
            try:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=30)  # Last 30 days
                
                response = cloudwatch.get_metric_statistics(
                    Namespace=namespace,
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
                    print(f"   ✅ Found metrics in namespace '{namespace}': {total} total requests")
                    
                    # Show recent datapoints
                    sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
                    for dp in sorted_datapoints[:3]:  # Show last 3 days
                        print(f"      - {dp['Timestamp'].strftime('%Y-%m-%d')}: {dp['Sum']} requests")
                else:
                    print(f"   ❌ No metrics found in namespace '{namespace}'")
                    
            except Exception as e:
                print(f"   ❌ Error checking namespace '{namespace}': {str(e)}")
        
        # 2. Check for metrics with different dimension names
        dimension_names_to_check = ['User', 'UserId', 'UserName', 'user_id']
        
        print(f"\n   Checking different dimension names:")
        for dim_name in dimension_names_to_check:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='UserMetrics',
                    MetricName='BedrockUsage',
                    Dimensions=[
                        {
                            'Name': dim_name,
                            'Value': user_id
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Sum']
                )
                
                if response['Datapoints']:
                    total = sum(dp['Sum'] for dp in response['Datapoints'])
                    print(f"   ✅ Found metrics with dimension '{dim_name}': {total} total requests")
                else:
                    print(f"   ❌ No metrics with dimension '{dim_name}'")
                    
            except Exception as e:
                print(f"   ❌ Error checking dimension '{dim_name}': {str(e)}")
        
        # 3. List all metrics for this user to see what exists
        print(f"\n   Listing all available metrics for {user_id}:")
        try:
            response = cloudwatch.list_metrics(
                Dimensions=[
                    {
                        'Name': 'User',
                        'Value': user_id
                    }
                ]
            )
            
            if response['Metrics']:
                print(f"   ✅ Found {len(response['Metrics'])} metric(s):")
                for metric in response['Metrics']:
                    print(f"      - Namespace: {metric['Namespace']}, MetricName: {metric['MetricName']}")
                    for dim in metric['Dimensions']:
                        print(f"        Dimension: {dim['Name']} = {dim['Value']}")
            else:
                print(f"   ❌ No metrics found for user {user_id}")
                
        except Exception as e:
            print(f"   ❌ Error listing metrics: {str(e)}")
    
    # 4. Check CloudWatch Logs for the usage monitor Lambda
    print(f"\n🔍 CHECKING LAMBDA LOGS FOR METRICS PUBLISHING")
    print("-" * 50)
    
    try:
        log_group_name = '/aws/lambda/bedrock-usage-monitor'
        
        # Get recent log streams
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)  # Last 24 hours
        
        response = logs.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            filterPattern='lcorp_001'
        )
        
        if response['events']:
            print(f"✅ Found {len(response['events'])} log events for lcorp_001:")
            for event in response['events'][-5:]:  # Show last 5 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"   - {timestamp}: {event['message']}")
        else:
            print("❌ No log events found for lcorp_001 in Lambda logs")
            
    except Exception as e:
        print(f"❌ Error checking Lambda logs: {str(e)}")
    
    # 5. Check if there's a separate metrics publishing Lambda
    print(f"\n🔍 CHECKING FOR METRICS PUBLISHING ISSUES")
    print("-" * 50)
    
    # Check if metrics are being published by looking for put_metric_data calls
    try:
        response = logs.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            filterPattern='put_metric_data OR PutMetricData OR CloudWatch'
        )
        
        if response['events']:
            print(f"✅ Found {len(response['events'])} CloudWatch publishing events:")
            for event in response['events'][-3:]:  # Show last 3 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"   - {timestamp}: {event['message']}")
        else:
            print("❌ No CloudWatch publishing events found in Lambda logs")
            
    except Exception as e:
        print(f"❌ Error checking CloudWatch publishing logs: {str(e)}")

if __name__ == "__main__":
    investigate_cloudwatch_issue()
