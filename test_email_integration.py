#!/usr/bin/env python3
"""
Test script to verify email service integration
"""

import json
import boto3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_service_integration():
    """Test the email service integration"""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda')
    
    # Test payload
    test_payload = {
        "action": "send_blocking_email",
        "user_id": "sdlc_004",
        "usage_record": {
            "request_count": 350,
            "daily_limit": 350,
            "team": "yo_leo_sap_group"
        },
        "reason": "Daily limit exceeded"
    }
    
    try:
        logger.info("Testing email service integration...")
        
        # Invoke the email service
        response = lambda_client.invoke(
            FunctionName='bedrock-email-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Read response
        response_payload = json.loads(response['Payload'].read())
        
        logger.info(f"Response Status Code: {response['StatusCode']}")
        logger.info(f"Response Payload: {json.dumps(response_payload, indent=2)}")
        
        if response['StatusCode'] == 200:
            logger.info("✅ Email service integration test PASSED")
            return True
        else:
            logger.error("❌ Email service integration test FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Email service integration test FAILED with exception: {str(e)}")
        return False

def test_realtime_controller_integration():
    """Test the realtime controller calling email service"""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda')
    
    # Test payload for manual blocking (which should trigger enhanced email)
    test_payload = {
        "action": "block",
        "user_id": "sdlc_004",
        "reason": "Test manual block for email format verification",
        "performed_by": "test_admin"
    }
    
    try:
        logger.info("Testing realtime controller email integration...")
        
        # Invoke the realtime controller
        response = lambda_client.invoke(
            FunctionName='bedrock-realtime-usage-controller',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Read response
        response_payload = json.loads(response['Payload'].read())
        
        logger.info(f"Response Status Code: {response['StatusCode']}")
        logger.info(f"Response Payload: {json.dumps(response_payload, indent=2)}")
        
        if response['StatusCode'] == 200:
            logger.info("✅ Realtime controller integration test PASSED")
            return True
        else:
            logger.error("❌ Realtime controller integration test FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Realtime controller integration test FAILED with exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Starting Email Service Integration Tests")
    print("=" * 50)
    
    # Test 1: Direct email service
    print("\n📧 Test 1: Direct Email Service")
    email_test_result = test_email_service_integration()
    
    # Test 2: Realtime controller integration
    print("\n🔄 Test 2: Realtime Controller Integration")
    controller_test_result = test_realtime_controller_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Direct Email Service: {'✅ PASS' if email_test_result else '❌ FAIL'}")
    print(f"Controller Integration: {'✅ PASS' if controller_test_result else '❌ FAIL'}")
    
    if email_test_result and controller_test_result:
        print("\n🎉 All tests PASSED! Email integration is working correctly.")
        print("📧 You should now receive emails with sophisticated formatting.")
    else:
        print("\n⚠️  Some tests FAILED. Check the logs above for details.")
