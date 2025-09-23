#!/usr/bin/env python3
"""
Test script for manual blocking functionality
This script simulates the Lambda function call that would be made from the dashboard
"""

import json
import boto3
from datetime import datetime

def test_manual_blocking():
    """Test manual blocking functionality"""
    
    # Test payload for manual blocking
    test_payload = {
        "action": "block",
        "user_id": "sap_003",
        "reason": "Manual admin block for testing",
        "performed_by": "dashboard_admin",
        "usage_record": {
            "request_count": 25,
            "daily_limit": 350,
            "team": "yo_leo_sap",
            "date": "2025-09-23"
        }
    }
    
    print("🧪 Testing Manual Blocking Functionality")
    print("=" * 50)
    print(f"📋 Test Payload: {json.dumps(test_payload, indent=2)}")
    print()
    
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name='eu-west-1')
        
        print("🚀 Invoking bedrock-realtime-usage-controller Lambda function...")
        
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName='bedrock-realtime-usage-controller',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print("📥 Lambda Response:")
        print(f"Status Code: {response.get('StatusCode', 'Unknown')}")
        print(f"Response: {json.dumps(response_payload, indent=2)}")
        
        # Check if blocking was successful
        if response_payload.get('statusCode') == 200:
            print("✅ Manual blocking test PASSED!")
            
            # Now test the IAM policy verification
            print("\n🔍 Verifying IAM Policy was applied...")
            test_iam_policy_verification("sap_003")
            
        else:
            print("❌ Manual blocking test FAILED!")
            print(f"Error: {response_payload.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

def test_iam_policy_verification(user_id):
    """Verify that the IAM policy was correctly applied"""
    try:
        iam_client = boto3.client('iam')
        policy_name = f"{user_id}_BedrockPolicy"
        
        # Get the user policy
        response = iam_client.get_user_policy(
            UserName=user_id,
            PolicyName=policy_name
        )
        
        policy_document = response['PolicyDocument']
        print(f"📋 Current IAM Policy for {user_id}:")
        print(json.dumps(policy_document, indent=2))
        
        # Check for deny statement
        deny_statements = [
            stmt for stmt in policy_document['Statement'] 
            if stmt.get('Sid') == 'DailyLimitBlock' and stmt.get('Effect') == 'Deny'
        ]
        
        if deny_statements:
            print("✅ IAM Deny Policy correctly applied!")
            print(f"🚫 Found {len(deny_statements)} deny statement(s)")
        else:
            print("❌ IAM Deny Policy NOT found!")
            
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ No IAM policy found for user {user_id}")
    except Exception as e:
        print(f"❌ Error verifying IAM policy: {str(e)}")

def test_manual_unblocking():
    """Test manual unblocking functionality"""
    
    # Test payload for manual unblocking
    test_payload = {
        "action": "unblock",
        "user_id": "sap_003",
        "reason": "Manual admin unblock for testing",
        "performed_by": "dashboard_admin"
    }
    
    print("\n🧪 Testing Manual Unblocking Functionality")
    print("=" * 50)
    print(f"📋 Test Payload: {json.dumps(test_payload, indent=2)}")
    print()
    
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name='eu-west-1')
        
        print("🚀 Invoking bedrock-realtime-usage-controller Lambda function...")
        
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName='bedrock-realtime-usage-controller',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print("📥 Lambda Response:")
        print(f"Status Code: {response.get('StatusCode', 'Unknown')}")
        print(f"Response: {json.dumps(response_payload, indent=2)}")
        
        # Check if unblocking was successful
        if response_payload.get('statusCode') == 200:
            print("✅ Manual unblocking test PASSED!")
            
            # Now test the IAM policy verification
            print("\n🔍 Verifying IAM Policy was updated...")
            test_iam_policy_after_unblock("sap_003")
            
        else:
            print("❌ Manual unblocking test FAILED!")
            print(f"Error: {response_payload.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

def test_iam_policy_after_unblock(user_id):
    """Verify that the IAM policy deny statement was removed"""
    try:
        iam_client = boto3.client('iam')
        policy_name = f"{user_id}_BedrockPolicy"
        
        # Get the user policy
        response = iam_client.get_user_policy(
            UserName=user_id,
            PolicyName=policy_name
        )
        
        policy_document = response['PolicyDocument']
        print(f"📋 Current IAM Policy for {user_id} after unblock:")
        print(json.dumps(policy_document, indent=2))
        
        # Check for deny statement
        deny_statements = [
            stmt for stmt in policy_document['Statement'] 
            if stmt.get('Sid') == 'DailyLimitBlock' and stmt.get('Effect') == 'Deny'
        ]
        
        if not deny_statements:
            print("✅ IAM Deny Policy correctly removed!")
        else:
            print("❌ IAM Deny Policy still present!")
            print(f"🚫 Found {len(deny_statements)} deny statement(s)")
            
    except iam_client.exceptions.NoSuchEntityException:
        print(f"❌ No IAM policy found for user {user_id}")
    except Exception as e:
        print(f"❌ Error verifying IAM policy: {str(e)}")

if __name__ == "__main__":
    print("🧪 AWS Bedrock Manual Blocking Test Suite")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().isoformat()}")
    print()
    
    # Test manual blocking
    test_manual_blocking()
    
    # Wait for user input before testing unblocking
    input("\n⏸️  Press Enter to test manual unblocking...")
    
    # Test manual unblocking
    test_manual_unblocking()
    
    print("\n🏁 Test suite completed!")
