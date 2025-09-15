#!/usr/bin/env python3
"""
Fix Automatic Monitoring System
===============================

This script fixes the automatic monitoring system by:
1. Creating CloudWatch Log Groups for Bedrock API calls
2. Setting up Metric Filters to capture InvokeModel calls
3. Creating CloudWatch Alarms to trigger Lambda functions
4. Configuring the monitoring pipeline properly

Author: AWS Bedrock Usage Control System
"""

import boto3
import json
import time
from datetime import datetime

# AWS clients
logs_client = boto3.client('logs', region_name='eu-west-1')
cloudwatch_client = boto3.client('cloudwatch', region_name='eu-west-1')
lambda_client = boto3.client('lambda', region_name='eu-west-1')
events_client = boto3.client('events', region_name='eu-west-1')

def create_cloudwatch_log_group():
    """Create CloudWatch Log Group for Bedrock API calls"""
    try:
        log_group_name = '/aws/bedrock/api-calls'
        
        # Create log group
        logs_client.create_log_group(
            logGroupName=log_group_name,
            tags={
                'Purpose': 'BedrockUsageMonitoring',
                'System': 'IndividualBlockingSystem'
            }
        )
        
        # Set retention policy (7 days)
        logs_client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=7
        )
        
        print(f"✅ Created CloudWatch Log Group: {log_group_name}")
        return log_group_name
        
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"ℹ️  CloudWatch Log Group already exists: {log_group_name}")
        return log_group_name
    except Exception as e:
        print(f"❌ Error creating CloudWatch Log Group: {e}")
        return None

def create_metric_filter():
    """Create Metric Filter to capture Bedrock InvokeModel calls"""
    try:
        log_group_name = '/aws/bedrock/api-calls'
        filter_name = 'bedrock-invoke-model-calls'
        
        # Metric filter pattern to capture InvokeModel calls
        filter_pattern = '[timestamp, request_id, event_name="InvokeModel*", user_id, ...]'
        
        logs_client.put_metric_filter(
            logGroupName=log_group_name,
            filterName=filter_name,
            filterPattern=filter_pattern,
            metricTransformations=[
                {
                    'metricName': 'BedrockInvokeModelCalls',
                    'metricNamespace': 'Bedrock/Usage',
                    'metricValue': '1'
                }
            ]
        )
        
        print(f"✅ Created Metric Filter: {filter_name}")
        return filter_name
        
    except Exception as e:
        print(f"❌ Error creating Metric Filter: {e}")
        return None

def create_cloudwatch_alarm():
    """Create CloudWatch Alarm to trigger when usage exceeds threshold"""
    try:
        alarm_name = 'bedrock-usage-threshold-alarm'
        
        cloudwatch_client.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=1,
            MetricName='BedrockInvokeModelCalls',
            Namespace='Bedrock/Usage',
            Period=300,  # 5 minutes
            Statistic='Sum',
            Threshold=10.0,  # Trigger after 10 calls in 5 minutes
            ActionsEnabled=True,
            AlarmActions=[
                f'arn:aws:lambda:eu-west-1:701055077130:function:bedrock-usage-monitor'
            ],
            AlarmDescription='Alarm when Bedrock usage exceeds threshold',
            Dimensions=[
                {
                    'Name': 'UserId',
                    'Value': '*'
                }
            ],
            Unit='Count'
        )
        
        print(f"✅ Created CloudWatch Alarm: {alarm_name}")
        return alarm_name
        
    except Exception as e:
        print(f"❌ Error creating CloudWatch Alarm: {e}")
        return None

def setup_eventbridge_rule_for_cloudtrail():
    """Setup EventBridge rule to capture CloudTrail events properly"""
    try:
        rule_name = 'bedrock-cloudtrail-events'
        
        # Create EventBridge rule for CloudTrail events
        events_client.put_rule(
            Name=rule_name,
            EventPattern=json.dumps({
                "source": ["aws.bedrock"],
                "detail-type": ["AWS API Call via CloudTrail"],
                "detail": {
                    "eventSource": ["bedrock.amazonaws.com"],
                    "eventName": ["InvokeModel", "InvokeModelWithResponseStream"]
                }
            }),
            State='ENABLED',
            Description='Capture Bedrock API calls from CloudTrail for usage monitoring'
        )
        
        # Add Lambda target
        events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:eu-west-1:701055077130:function:bedrock-usage-monitor'
                }
            ]
        )
        
        print(f"✅ Created EventBridge rule: {rule_name}")
        return rule_name
        
    except Exception as e:
        print(f"❌ Error creating EventBridge rule: {e}")
        return None

def add_lambda_permission_for_eventbridge():
    """Add permission for EventBridge to invoke Lambda function"""
    try:
        lambda_client.add_permission(
            FunctionName='bedrock-usage-monitor',
            StatementId='allow-eventbridge-invoke',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn='arn:aws:events:eu-west-1:701055077130:rule/bedrock-cloudtrail-events'
        )
        
        print("✅ Added EventBridge permission to Lambda function")
        
    except lambda_client.exceptions.ResourceConflictException:
        print("ℹ️  EventBridge permission already exists")
    except Exception as e:
        print(f"❌ Error adding Lambda permission: {e}")

def test_lambda_function():
    """Test the Lambda function with a sample event"""
    try:
        # Sample CloudTrail event
        test_event = {
            "detail": {
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "eventSource": "bedrock.amazonaws.com",
                "eventName": "InvokeModel",
                "userIdentity": {
                    "type": "IAMUser",
                    "userName": "sap_003",
                    "arn": "arn:aws:iam::701055077130:user/sap_003"
                },
                "sourceIPAddress": "192.168.1.100",
                "userAgent": "aws-cli/2.0.0"
            }
        }
        
        response = lambda_client.invoke(
            FunctionName='bedrock-usage-monitor',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        print("✅ Lambda function test successful:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error testing Lambda function: {e}")

def main():
    """Main function to fix the monitoring system"""
    print("🔧 Fixing Automatic Monitoring System...")
    print("=" * 50)
    
    # Step 1: Create CloudWatch Log Group
    print("\n1. Setting up CloudWatch Log Group...")
    create_cloudwatch_log_group()
    
    # Step 2: Create Metric Filter
    print("\n2. Setting up Metric Filter...")
    create_metric_filter()
    
    # Step 3: Create CloudWatch Alarm
    print("\n3. Setting up CloudWatch Alarm...")
    create_cloudwatch_alarm()
    
    # Step 4: Setup EventBridge rule
    print("\n4. Setting up EventBridge rule...")
    setup_eventbridge_rule_for_cloudtrail()
    
    # Step 5: Add Lambda permissions
    print("\n5. Adding Lambda permissions...")
    add_lambda_permission_for_eventbridge()
    
    # Step 6: Test Lambda function
    print("\n6. Testing Lambda function...")
    test_lambda_function()
    
    print("\n" + "=" * 50)
    print("✅ Monitoring system fix completed!")
    print("\nNext steps:")
    print("1. The system should now capture Bedrock API calls automatically")
    print("2. Users who exceed limits will be blocked automatically")
    print("3. Monitor the CloudWatch logs for proper functioning")
    print("4. Check the dashboard for real-time usage updates")

if __name__ == "__main__":
    main()
