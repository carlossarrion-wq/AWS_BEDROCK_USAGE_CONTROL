#!/usr/bin/env python3
"""
Verify that the lcorp_001 fix worked and check if it appears in dashboard
"""

import boto3
import time
from datetime import datetime, date, timedelta

def verify_fix():
    """Verify the lcorp_001 fix worked"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    user_id = 'lcorp_001'
    
    print(f"VERIFYING LCORP_001 FIX")
    print("=" * 50)
    
    # Wait a moment for CloudWatch to propagate
    print("⏳ Waiting 10 seconds for CloudWatch metrics to propagate...")
    time.sleep(10)
    
    # Check CloudWatch metrics with different time ranges
    time_ranges = [
        ("Last 1 day", timedelta(days=1)),
        ("Last 7 days", timedelta(days=7)),
        ("Last 30 days", timedelta(days=30))
    ]
    
    for range_name, delta in time_ranges:
        print(f"\n🔍 Checking {range_name}:")
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - delta
            
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
                print(f"   ✅ Found {total} total requests")
                print(f"   ✅ Number of data points: {len(response['Datapoints'])}")
                
                # Show datapoints
                sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
                for dp in sorted_datapoints:
                    print(f"      - {dp['Timestamp'].strftime('%Y-%m-%d')}: {dp['Sum']} requests")
            else:
                print(f"   ❌ No metrics found")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Check if metrics were published today specifically
    print(f"\n🔍 Checking today's metrics specifically:")
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': user_id
                }
            ],
            StartTime=today,
            EndTime=tomorrow,
            Period=3600,  # 1 hour periods
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            total = sum(dp['Sum'] for dp in response['Datapoints'])
            print(f"   ✅ Found {total} requests today")
            print(f"   ✅ Number of hourly data points: {len(response['Datapoints'])}")
        else:
            print(f"   ❌ No metrics found for today")
            
    except Exception as e:
        print(f"   ❌ Error checking today's metrics: {str(e)}")
    
    # Final recommendation
    print(f"\n📋 DASHBOARD STATUS:")
    print(f"   The dashboard fetches metrics using the same CloudWatch API calls.")
    print(f"   If metrics are showing above, lcorp_001 should appear in the dashboard.")
    print(f"   If not, there may be a CloudWatch propagation delay (up to 15 minutes).")
    print(f"   \n   🔄 Try refreshing the dashboard in a few minutes.")

if __name__ == "__main__":
    verify_fix()
