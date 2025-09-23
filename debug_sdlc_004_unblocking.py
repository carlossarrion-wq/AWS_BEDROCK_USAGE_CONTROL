#!/usr/bin/env python3
"""
Debug script to investigate the unblocking issue for user sdlc_004
"""

import boto3
import json
from datetime import datetime

def check_user_iam_policy(user_id):
    """Check current IAM policy for user"""
    iam = boto3.client('iam', region_name='eu-west-1')
    
    try:
        policy_name = f"{user_id}_BedrockPolicy"
        response = iam.get_user_policy(UserName=user_id, PolicyName=policy_name)
        
        print(f"=== IAM Policy for {user_id} ===")
        print(f"Policy Name: {response['PolicyName']}")
        print(f"Policy Document:")
        print(json.dumps(response['PolicyDocument'], indent=2))
        
        # Check if deny statement exists
        statements = response['PolicyDocument']['Statement']
        deny_statements = [stmt for stmt in statements if stmt.get('Effect') == 'Deny']
        allow_statements = [stmt for stmt in statements if stmt.get('Effect') == 'Allow']
        
        print(f"\nPolicy Analysis:")
        print(f"- Allow statements: {len(allow_statements)}")
        print(f"- Deny statements: {len(deny_statements)}")
        
        if deny_statements:
            print("❌ USER IS BLOCKED - Deny statements found:")
            for stmt in deny_statements:
                print(f"  - Sid: {stmt.get('Sid', 'No Sid')}")
                print(f"  - Actions: {stmt.get('Action', [])}")
        else:
            print("✅ USER IS NOT BLOCKED - No deny statements found")
            
        return len(deny_statements) > 0
        
    except iam.exceptions.NoSuchEntityException:
        print(f"❌ No IAM policy found for user {user_id}")
        return False
    except Exception as e:
        print(f"❌ Error checking IAM policy: {str(e)}")
        return False

def check_lambda_logs():
    """Check recent Lambda logs for unblocking events"""
    logs = boto3.client('logs', region_name='eu-west-1')
    
    try:
        print("\n=== Recent Unblocking Events ===")
        
        # Search for unblocking events in the last 24 hours
        start_time = int((datetime.now().timestamp() - 86400) * 1000)
        
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/bedrock-realtime-usage-controller',
            startTime=start_time,
            filterPattern='EXECUTING USER UNBLOCKING'
        )
        
        events = response.get('events', [])
        print(f"Found {len(events)} unblocking events in the last 24 hours:")
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"- {timestamp}: {event['message'].strip()}")
            
        return events
        
    except Exception as e:
        print(f"❌ Error checking Lambda logs: {str(e)}")
        return []

def check_user_tags(user_id):
    """Check user IAM tags"""
    iam = boto3.client('iam', region_name='eu-west-1')
    
    try:
        print(f"\n=== IAM Tags for {user_id} ===")
        
        response = iam.list_user_tags(UserName=user_id)
        tags = response.get('Tags', [])
        
        for tag in tags:
            print(f"- {tag['Key']}: {tag['Value']}")
            
        # Check for administrative_safe tag
        admin_safe_tags = [tag for tag in tags if tag['Key'].lower() in ['administrative_safe', 'admin_safe']]
        if admin_safe_tags:
            print(f"⚠️  Administrative protection found: {admin_safe_tags[0]['Value']}")
        else:
            print("ℹ️  No administrative protection tag found")
            
        return tags
        
    except Exception as e:
        print(f"❌ Error checking user tags: {str(e)}")
        return []

def main():
    user_id = "sdlc_004"
    
    print(f"🔍 Debugging unblocking issue for user: {user_id}")
    print(f"Current time: {datetime.now()}")
    print("=" * 60)
    
    # Check IAM policy status
    is_blocked_iam = check_user_iam_policy(user_id)
    
    # Check user tags
    check_user_tags(user_id)
    
    # Check recent unblocking events
    unblocking_events = check_lambda_logs()
    
    print("\n" + "=" * 60)
    print("🔍 ANALYSIS SUMMARY:")
    print(f"- IAM Policy Status: {'BLOCKED' if is_blocked_iam else 'NOT BLOCKED'}")
    print(f"- Recent unblocking events: {len(unblocking_events)}")
    
    if not is_blocked_iam and len(unblocking_events) > 0:
        print("✅ CONCLUSION: Unblocking appears to have worked correctly")
        print("   The user has no deny statements in their IAM policy")
    elif is_blocked_iam:
        print("❌ CONCLUSION: User is still blocked at IAM level")
        print("   The unblocking process failed to remove deny statements")
    else:
        print("⚠️  CONCLUSION: Unclear status - no recent unblocking events found")

if __name__ == "__main__":
    main()
