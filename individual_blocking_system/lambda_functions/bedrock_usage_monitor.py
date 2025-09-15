#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Usage Monitor Lambda
=============================================================

This Lambda function monitors Bedrock API calls via CloudTrail events and:
1. Updates daily usage counters in DynamoDB
2. Auto-provisions new users with intelligent configuration
3. Evaluates daily limits and triggers blocking when exceeded
4. Sends notifications for warnings and blocks

Author: AWS Bedrock Usage Control System
Version: 1.0.0
"""

import json
import boto3
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional
import os

# Custom JSON encoder for Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'bedrock_user_daily_usage')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:bedrock-usage-alerts')
POLICY_MANAGER_FUNCTION = os.environ.get('POLICY_MANAGER_FUNCTION', 'bedrock-policy-manager')

# Load configuration from file or environment
DEFAULT_CONFIG = {
    "daily_limits": {
        "default_user_limit": 50,
        "default_warning_threshold": 40,
        "reset_time_utc": "00:00:00",
        "grace_period_minutes": 5
    },
    "blocking_system": {
        "enabled": True,
        "dry_run_mode": False,
        "notification_channels": ["sns"],
        "auto_unblock": True,
        "emergency_override_users": ["admin_user"]
    },
    "auto_provisioning": {
        "enabled": True,
        "default_team_daily_limit": 50,
        "team_limit_division_factor": 10,
        "notification_on_new_user": True
    }
}

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for processing Bedrock API events
    
    Args:
        event: CloudWatch Events event containing CloudTrail data
        context: Lambda context object
        
    Returns:
        Dict with status code and processing results
    """
    try:
        logger.info(f"Processing event: {json.dumps(event, default=str)}")
        
        # Parse CloudTrail event
        if 'detail' not in event:
            logger.error("Invalid event format - missing 'detail' field")
            return {'statusCode': 400, 'body': 'Invalid event format'}
        
        detail = event['detail']
        
        # Extract user information
        user_info = extract_user_info(detail)
        if not user_info:
            logger.warning("Could not extract user information from event")
            return {'statusCode': 200, 'body': 'No user info found'}
        
        logger.info(f"Processing request for user: {user_info['user_id']}")
        
        # Update usage counter with auto-provisioning
        usage_record = update_daily_usage(user_info)
        
        # Evaluate limits and take action
        action_taken = evaluate_limits_and_act(user_info['user_id'], usage_record)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_info['user_id'],
                'current_usage': usage_record['request_count'],
                'daily_limit': usage_record['daily_limit'],
                'status': usage_record['status'],
                'action_taken': action_taken
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}, cls=DecimalEncoder)
        }

def extract_user_info(detail: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract user information from CloudTrail event detail
    
    Args:
        detail: CloudTrail event detail section
        
    Returns:
        Dict with user_id and other relevant info, or None if extraction fails
    """
    try:
        user_identity = detail.get('userIdentity', {})
        
        # Handle different user identity types
        if user_identity.get('type') == 'IAMUser':
            user_id = user_identity.get('userName')
            user_arn = user_identity.get('arn')
        elif user_identity.get('type') == 'AssumedRole':
            # Extract user from assumed role ARN
            arn = user_identity.get('arn', '')
            if '/user/' in arn:
                user_id = arn.split('/user/')[-1].split('/')[0]
            else:
                user_id = user_identity.get('userName')
            user_arn = arn
        else:
            logger.warning(f"Unsupported user identity type: {user_identity.get('type')}")
            return None
        
        if not user_id:
            logger.warning("Could not determine user_id from event")
            return None
        
        return {
            'user_id': user_id,
            'user_arn': user_arn,
            'event_time': detail.get('eventTime'),
            'source_ip': detail.get('sourceIPAddress'),
            'user_agent': detail.get('userAgent', '')
        }
        
    except Exception as e:
        logger.error(f"Error extracting user info: {str(e)}")
        return None

def update_daily_usage(user_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Update daily usage counter in DynamoDB with auto-provisioning
    
    Args:
        user_info: Dictionary containing user information
        
    Returns:
        Updated usage record from DynamoDB
    """
    table = dynamodb.Table(TABLE_NAME)
    user_id = user_info['user_id']
    today = date.today().isoformat()
    
    try:
        # Get user configuration with auto-discovery
        user_config = get_user_config_with_autodiscovery(user_id)
        
        # Calculate TTL (7 days from now)
        ttl_timestamp = int((datetime.utcnow().timestamp() + 86400 * 7))
        
        # Update item with auto-provisioning
        response = table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression='''
                ADD request_count :inc 
                SET #status = if_not_exists(#status, :active),
                    daily_limit = if_not_exists(daily_limit, :limit),
                    warning_threshold = if_not_exists(warning_threshold, :warning),
                    last_request_time = :now,
                    team = if_not_exists(team, :team),
                    #ttl = if_not_exists(#ttl, :ttl),
                    first_seen = if_not_exists(first_seen, :first_seen)
            ''',
            ExpressionAttributeNames={
                '#status': 'status',
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues={
                ':inc': 1,
                ':active': 'ACTIVE',
                ':limit': user_config['daily_limit'],
                ':warning': user_config['warning_threshold'],
                ':now': datetime.utcnow().isoformat(),
                ':team': user_config['team'],
                ':ttl': ttl_timestamp,
                ':first_seen': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        usage_record = response['Attributes']
        
        # Check if this is a new user (first time seen today)
        if usage_record.get('request_count', 0) == 1:
            log_new_user_discovery(user_id, user_config, user_info)
        
        logger.info(f"Updated usage for {user_id}: {usage_record['request_count']}/{usage_record['daily_limit']}")
        return usage_record
        
    except Exception as e:
        logger.error(f"Error updating daily usage for {user_id}: {str(e)}")
        raise

def get_user_config_with_autodiscovery(user_id: str) -> Dict[str, Any]:
    """
    Get user configuration with automatic discovery from IAM tags and quota_config.json
    
    Args:
        user_id: The user ID to get configuration for
        
    Returns:
        Dictionary with user configuration (daily_limit, warning_threshold, team)
    """
    try:
        # Try to load quota_config.json from the parent directory
        quota_config = load_quota_config()
        
        # Check if user exists in current quota_config.json
        if user_id in quota_config.get('users', {}):
            user_config = quota_config['users'][user_id]
            return {
                'daily_limit': user_config.get('daily_limit', 50),
                'warning_threshold': int(user_config.get('daily_limit', 50) * user_config.get('warning_threshold', 80) / 100),
                'team': user_config.get('team', 'unknown')
            }
        
        # Auto-discover user information from IAM if not in quota_config
        try:
            # Get user tags to determine team
            user_tags_response = iam.list_user_tags(UserName=user_id)
            user_tags = {tag['Key']: tag['Value'] for tag in user_tags_response['Tags']}
            
            team_name = user_tags.get('Team', 'unknown')
            
            # Check if team exists in quota_config.json
            team_config = quota_config.get('teams', {}).get(team_name, {})
            
            # Calculate user limits based on team configuration or defaults
            if team_config:
                # Use team-based limits (convert monthly to daily: monthly/30)
                team_monthly_limit = team_config.get('monthly_limit', 1500)  # Default 1500/month
                user_daily_limit = max(50, team_monthly_limit // 30)  # Convert to daily, min 50
                warning_percentage = team_config.get('warning_threshold', 80)
                user_warning_threshold = int(user_daily_limit * warning_percentage / 100)
            else:
                # Use default limits from configuration
                config = DEFAULT_CONFIG
                user_daily_limit = config['daily_limits']['default_user_limit']
                user_warning_threshold = config['daily_limits']['default_warning_threshold']
            
            return {
                'daily_limit': user_daily_limit,
                'warning_threshold': user_warning_threshold,
                'team': team_name
            }
            
        except Exception as e:
            logger.warning(f"Could not auto-discover config for user {user_id}: {str(e)}")
            # Fallback to defaults
            config = DEFAULT_CONFIG
            return {
                'daily_limit': config['daily_limits']['default_user_limit'],
                'warning_threshold': config['daily_limits']['default_warning_threshold'],
                'team': 'unknown'
            }
            
    except Exception as e:
        logger.error(f"Error getting user config for {user_id}: {str(e)}")
        # Final fallback
        return {
            'daily_limit': 50,
            'warning_threshold': 40,
            'team': 'unknown'
        }

def load_quota_config() -> Dict[str, Any]:
    """
    Load quota configuration from quota_config.json
    
    Returns:
        Dictionary with quota configuration
    """
    try:
        # In Lambda, we'll need to package this file or load from S3/Parameter Store
        # For now, return empty config and rely on auto-discovery
        logger.info("Loading quota config from environment or defaults")
        return {'users': {}, 'teams': {}}
        
    except Exception as e:
        logger.error(f"Error loading quota_config.json: {str(e)}")
        return {'users': {}, 'teams': {}}

def log_new_user_discovery(user_id: str, user_config: Dict[str, Any], user_info: Dict[str, str]) -> None:
    """
    Log discovery of new user and send notification
    
    Args:
        user_id: The user ID that was discovered
        user_config: The configuration assigned to the user
        user_info: Additional user information from the event
    """
    logger.info(f"Auto-discovered new user: {user_id} with config: {user_config}")
    
    # Send notification about new user discovery
    try:
        config = DEFAULT_CONFIG
        if config['auto_provisioning']['notification_on_new_user']:
            message = {
                'event_type': 'new_user_discovered',
                'user_id': user_id,
                'team': user_config['team'],
                'daily_limit': user_config['daily_limit'],
                'warning_threshold': user_config['warning_threshold'],
                'discovered_at': datetime.utcnow().isoformat(),
                'user_arn': user_info.get('user_arn', ''),
                'source_ip': user_info.get('source_ip', ''),
                'user_agent': user_info.get('user_agent', '')
            }
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"New Bedrock User Discovered: {user_id}",
                Message=json.dumps(message, indent=2)
            )
            
            logger.info(f"Sent new user notification for {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to send new user notification: {str(e)}")

def evaluate_limits_and_act(user_id: str, usage_record: Dict[str, Any]) -> str:
    """
    Evaluate usage limits and take appropriate action (warn or block)
    
    Args:
        user_id: The user ID to evaluate
        usage_record: Current usage record from DynamoDB
        
    Returns:
        String describing the action taken
    """
    try:
        current_count = usage_record['request_count']
        daily_limit = usage_record['daily_limit']
        warning_threshold = usage_record['warning_threshold']
        current_status = usage_record['status']
        
        config = DEFAULT_CONFIG
        
        # Check if blocking is enabled
        if not config['blocking_system']['enabled']:
            logger.info(f"Blocking system disabled - no action taken for {user_id}")
            return "blocking_disabled"
        
        # Check for emergency override users
        if user_id in config['blocking_system']['emergency_override_users']:
            logger.info(f"Emergency override user {user_id} - no limits applied")
            return "emergency_override"
        
        # Check if daily limit exceeded
        if current_count >= daily_limit:
            if current_status != 'BLOCKED':
                # NEW: Check if user has administrative protection (manually unblocked today)
                if has_administrative_protection(user_id, usage_record):
                    logger.info(f"User {user_id} has administrative protection - automatic blocking disabled until tomorrow")
                    send_notification(user_id, 'ADMIN_PROTECTED', usage_record)
                    return "admin_protected"
                
                if config['blocking_system']['dry_run_mode']:
                    logger.info(f"DRY RUN: Would block user {user_id} (usage: {current_count}/{daily_limit})")
                    send_notification(user_id, 'DRY_RUN_BLOCK', usage_record)
                    return "dry_run_block"
                else:
                    logger.warning(f"Blocking user {user_id} - daily limit exceeded ({current_count}/{daily_limit})")
                    block_user(user_id, usage_record)
                    return "blocked"
            else:
                logger.info(f"User {user_id} already blocked")
                return "already_blocked"
        
        # Check warning threshold
        elif current_count >= warning_threshold:
            if current_status != 'WARNING' and current_status != 'BLOCKED':
                logger.info(f"Warning threshold reached for {user_id} ({current_count}/{daily_limit})")
                warn_user(user_id, usage_record)
                return "warning_sent"
        
        # Normal operation
        return "normal"
        
    except Exception as e:
        logger.error(f"Error evaluating limits for {user_id}: {str(e)}")
        return "error"

def block_user(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Block user by updating status and invoking policy manager
    
    Args:
        user_id: The user ID to block
        usage_record: Current usage record
    """
    try:
        # Update status in DynamoDB
        update_user_status(user_id, 'BLOCKED')
        
        # Invoke policy manager to modify IAM policy
        lambda_client.invoke(
            FunctionName=POLICY_MANAGER_FUNCTION,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({
                'action': 'block',
                'user_id': user_id,
                'reason': 'daily_limit_exceeded',
                'usage_record': usage_record
            })
        )
        
        # Send notification
        send_notification(user_id, 'BLOCKED', usage_record)
        
        logger.info(f"Successfully initiated blocking for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error blocking user {user_id}: {str(e)}")
        raise

def warn_user(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Warn user by updating status and sending notification
    
    Args:
        user_id: The user ID to warn
        usage_record: Current usage record
    """
    try:
        # Update status in DynamoDB
        update_user_status(user_id, 'WARNING')
        
        # Send notification
        send_notification(user_id, 'WARNING', usage_record)
        
        logger.info(f"Successfully sent warning to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error warning user {user_id}: {str(e)}")

def update_user_status(user_id: str, status: str) -> None:
    """
    Update user status in DynamoDB
    
    Args:
        user_id: The user ID to update
        status: New status (ACTIVE, WARNING, BLOCKED)
    """
    try:
        table = dynamodb.Table(TABLE_NAME)
        today = date.today().isoformat()
        
        update_expression = 'SET #status = :status, last_status_change = :now'
        expression_values = {
            ':status': status,
            ':now': datetime.utcnow().isoformat()
        }
        
        # Add blocked_at timestamp if blocking
        if status == 'BLOCKED':
            update_expression += ', blocked_at = :blocked_at'
            expression_values[':blocked_at'] = datetime.utcnow().isoformat()
        
        table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Updated status for {user_id} to {status}")
        
    except Exception as e:
        logger.error(f"Error updating status for {user_id}: {str(e)}")
        raise

def has_administrative_protection(user_id: str, usage_record: Dict[str, Any]) -> bool:
    """
    Check if user has administrative protection (manually unblocked by admin today)
    
    Args:
        user_id: The user ID to check
        usage_record: Current usage record from DynamoDB
        
    Returns:
        True if user has administrative protection, False otherwise
    """
    try:
        # Check if user has been manually unblocked today by checking the blocking history
        history_table = dynamodb.Table('bedrock_blocking_history')
        today = date.today().isoformat()
        
        # Query blocking history for today's operations on this user
        response = history_table.query(
            IndexName='user-date-index',  # Assuming we have a GSI on user_id and date
            KeyConditionExpression='user_id = :user_id AND begins_with(#date, :today)',
            ExpressionAttributeNames={
                '#date': 'date'
            },
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':today': today
            },
            ScanIndexForward=False  # Most recent first
        )
        
        operations = response.get('Items', [])
        
        # Look for manual unblock operations today
        for operation in operations:
            if (operation.get('operation') == 'unblock' and 
                operation.get('performed_by') != 'system' and
                operation.get('performed_by') != 'daily_reset'):
                
                logger.info(f"Found administrative unblock for {user_id} by {operation.get('performed_by')} at {operation.get('timestamp')}")
                return True
        
        # Also check if there's an admin_protection flag in the usage record
        if usage_record.get('admin_protection') == True:
            logger.info(f"User {user_id} has admin_protection flag set")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking administrative protection for {user_id}: {str(e)}")
        # In case of error, err on the side of caution and allow blocking
        return False

def send_notification(user_id: str, notification_type: str, usage_record: Dict[str, Any]) -> None:
    """
    Send notification via SNS
    
    Args:
        user_id: The user ID
        notification_type: Type of notification (WARNING, BLOCKED, ADMIN_PROTECTED, etc.)
        usage_record: Current usage record
    """
    try:
        config = DEFAULT_CONFIG
        
        if 'sns' not in config['blocking_system']['notification_channels']:
            logger.info("SNS notifications disabled")
            return
        
        # Prepare notification message
        message = {
            'event_type': notification_type.lower(),
            'user_id': user_id,
            'team': usage_record.get('team', 'unknown'),
            'current_usage': usage_record['request_count'],
            'daily_limit': usage_record['daily_limit'],
            'warning_threshold': usage_record['warning_threshold'],
            'timestamp': datetime.utcnow().isoformat(),
            'date': usage_record.get('date', date.today().isoformat())
        }
        
        # Customize subject based on notification type
        subjects = {
            'WARNING': f"Bedrock Usage Warning: {user_id}",
            'BLOCKED': f"Bedrock User Blocked: {user_id}",
            'DRY_RUN_BLOCK': f"Bedrock Dry Run Block: {user_id}",
            'ADMIN_PROTECTED': f"Bedrock User Protected by Admin: {user_id}"
        }
        
        subject = subjects.get(notification_type, f"Bedrock Notification: {user_id}")
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=json.dumps(message, indent=2)
        )
        
        logger.info(f"Sent {notification_type} notification for {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending notification for {user_id}: {str(e)}")

# For testing purposes
if __name__ == "__main__":
    # Test event structure
    test_event = {
        "detail": {
            "eventTime": "2025-01-15T14:30:00Z",
            "eventSource": "bedrock.amazonaws.com",
            "eventName": "InvokeModel",
            "userIdentity": {
                "type": "IAMUser",
                "userName": "test_user_001",
                "arn": "arn:aws:iam::701055077130:user/test_user_001"
            },
            "sourceIPAddress": "192.168.1.100",
            "userAgent": "aws-cli/2.0.0"
        }
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "bedrock-usage-monitor"
            self.memory_limit_in_mb = 256
            self.invoked_function_arn = "arn:aws:lambda:eu-west-1:701055077130:function:bedrock-usage-monitor"
    
    # Test the handler
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
