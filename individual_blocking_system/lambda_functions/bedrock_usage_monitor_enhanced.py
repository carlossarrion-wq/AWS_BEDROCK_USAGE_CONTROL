#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Enhanced Usage Monitor Lambda
======================================================================

This Lambda function monitors Bedrock API calls via CloudTrail events and:
1. Updates daily usage counters in DynamoDB
2. Auto-provisions new users with intelligent configuration
3. Evaluates daily limits and triggers blocking when exceeded
4. Sends comprehensive email notifications for all 5 scenarios

Enhanced with comprehensive email delivery functionality for:
- Warning emails (80% quota reached)
- Blocking emails (100% quota exceeded)
- Unblocking emails (daily reset)
- Admin blocking emails (manual admin block)
- Admin unblocking emails (manual admin unblock)

Author: AWS Bedrock Usage Control System
Version: 2.0.0
"""

import json
import boto3
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional
import os

# Import the enhanced email service
from bedrock_email_service import create_email_service

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
cloudwatch = boto3.client('cloudwatch')

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'bedrock_user_daily_usage')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:bedrock-usage-alerts')
POLICY_MANAGER_FUNCTION = os.environ.get('POLICY_MANAGER_FUNCTION', 'bedrock-policy-manager')

# Email configuration
EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'

# Load configuration from file or environment
DEFAULT_CONFIG = {
    "daily_limits": {
        "default_user_limit": 250,
        "default_warning_threshold": 150,
        "reset_time_utc": "00:00:00",
        "grace_period_minutes": 5
    },
    "blocking_system": {
        "enabled": True,
        "dry_run_mode": False,
        "notification_channels": ["sns", "email"],
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

# Initialize enhanced email service if enabled
email_service = None
if EMAIL_NOTIFICATIONS_ENABLED:
    try:
        email_service = create_email_service()
        logger.info("Enhanced email service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize email service: {str(e)}")
        email_service = None

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
        
        # Publish metrics to CloudWatch for real-time dashboard updates
        publish_cloudwatch_metrics(user_info['user_id'], usage_record)
        
        # Evaluate limits and take action
        action_taken = evaluate_limits_and_act(user_info['user_id'], usage_record)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_info['user_id'],
                'current_usage': int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count'],
                'daily_limit': int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit'],
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
        # ALWAYS update team field to ensure consistency with current IAM tags
        response = table.update_item(
            Key={'user_id': user_id, 'date': today},
            UpdateExpression='''
                ADD request_count :inc 
                SET #status = if_not_exists(#status, :active),
                    daily_limit = if_not_exists(daily_limit, :limit),
                    warning_threshold = if_not_exists(warning_threshold, :warning),
                    last_request_time = :now,
                    team = :team,
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
    Priority: quota_config.json explicit config > IAM tag-based team config > defaults
    
    Args:
        user_id: The user ID to get configuration for
        
    Returns:
        Dictionary with user configuration (daily_limit, warning_threshold, team)
    """
    try:
        # Try to load quota_config.json from the parent directory
        quota_config = load_quota_config()
        
        # ALWAYS get IAM tags first for consistent team assignment
        iam_team_name = 'unknown'
        try:
            user_tags_response = iam.list_user_tags(UserName=user_id)
            user_tags = {tag['Key']: tag['Value'] for tag in user_tags_response['Tags']}
            iam_team_name = user_tags.get('Team', 'unknown')
            logger.info(f"Retrieved IAM team for {user_id}: {iam_team_name}")
        except Exception as e:
            logger.warning(f"Could not retrieve IAM tags for user {user_id}: {str(e)}")
        
        # Check if user exists in current quota_config.json
        if user_id in quota_config.get('users', {}):
            user_config = quota_config['users'][user_id]
            
            # Use explicit config but OVERRIDE team with IAM tag for consistency
            # This ensures team assignment is always based on current IAM tags
            config_team = user_config.get('team', 'unknown')
            final_team = iam_team_name if iam_team_name != 'unknown' else config_team
            
            logger.info(f"User {user_id} found in quota_config with team '{config_team}', using IAM team '{final_team}' for consistency")
            
            # Use default values (250 daily, 150 warning) even if user exists in quota_config
            return {
                'daily_limit': 250,  # Always use default 250
                'warning_threshold': 150,  # Always use default 150 (60% of 250)
                'team': final_team
            }
        
        # Auto-discover user information from IAM if not in quota_config
        try:
            # Check if team exists in quota_config.json teams section
            team_config = quota_config.get('teams', {}).get(iam_team_name, {})
            
            # Always use default limits (250 daily, 150 warning) regardless of team config
            config = DEFAULT_CONFIG
            user_daily_limit = config['daily_limits']['default_user_limit']  # 250
            user_warning_threshold = config['daily_limits']['default_warning_threshold']  # 150
            
            if team_config:
                logger.info(f"Auto-configured user {user_id} with defaults (ignoring team '{iam_team_name}' monthly limit): daily_limit={user_daily_limit}, warning={user_warning_threshold}")
            else:
                logger.info(f"Auto-configured user {user_id} with defaults (team '{iam_team_name}' not found in config): daily_limit={user_daily_limit}, warning={user_warning_threshold}")
            
            return {
                'daily_limit': user_daily_limit,
                'warning_threshold': user_warning_threshold,
                'team': iam_team_name
            }
            
        except Exception as e:
            logger.warning(f"Could not auto-discover config for user {user_id}: {str(e)}")
            # Fallback to defaults
            config = DEFAULT_CONFIG
            return {
                'daily_limit': config['daily_limits']['default_user_limit'],
                'warning_threshold': config['daily_limits']['default_warning_threshold'],
                'team': iam_team_name  # Use IAM team even in fallback
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
        # Load quota_config.json from the root of the Lambda package
        import os
        
        # Try multiple possible locations for the config file
        possible_paths = [
            'quota_config.json',  # Root of Lambda package
            '../../quota_config.json',  # Relative path from lambda_functions directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quota_config.json'),  # Same directory as Lambda function
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if not config_path:
            logger.warning("quota_config.json not found in any expected location, using empty config")
            return {'users': {}, 'teams': {}}
        
        logger.info(f"Loading quota config from {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        logger.info(f"Successfully loaded quota config with {len(config.get('users', {}))} users and {len(config.get('teams', {}))} teams")
        return config
        
    except FileNotFoundError:
        logger.warning("quota_config.json not found, using empty config")
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
        
        # NEW: Check if user is blocked but block has expired
        if current_status == 'BLOCKED':
            if check_and_handle_expired_block(user_id, usage_record):
                logger.info(f"User {user_id} block has expired - automatically unblocked")
                # Update the status in our local record for further processing
                usage_record['status'] = 'ACTIVE'
                current_status = 'ACTIVE'
        
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
                'usage_record': usage_record,
                'performed_by': 'system'  # Explicitly set system as performer for automatic blocks
            }, cls=DecimalEncoder)
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

def check_and_handle_expired_block(user_id: str, usage_record: Dict[str, Any]) -> bool:
    """
    Check if user's block has expired and automatically unblock if so
    
    Args:
        user_id: The user ID to check
        usage_record: Current usage record from DynamoDB
        
    Returns:
        True if user was unblocked due to expiration, False otherwise
    """
    try:
        expires_at = usage_record.get('expires_at')
        
        # If no expiration date or set to 'Indefinite', don't auto-unblock
        if not expires_at or expires_at == 'Indefinite':
            logger.debug(f"User {user_id} has no expiration date or indefinite block")
            return False
        
        # Parse expiration date
        from datetime import datetime
        try:
            # Handle different datetime formats
            if expires_at.endswith('Z'):
                expiration_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            else:
                expiration_time = datetime.fromisoformat(expires_at)
        except ValueError as e:
            logger.error(f"Invalid expiration date format for user {user_id}: {expires_at} - {str(e)}")
            return False
        
        # Check if block has expired
        current_time = datetime.utcnow().replace(tzinfo=expiration_time.tzinfo) if expiration_time.tzinfo else datetime.utcnow()
        
        if current_time >= expiration_time:
            logger.info(f"Block for user {user_id} has expired (expired at: {expires_at}, current: {current_time.isoformat()})")
            
            # Automatically unblock the user
            try:
                response = lambda_client.invoke(
                    FunctionName=POLICY_MANAGER_FUNCTION,
                    InvocationType='RequestResponse',  # Synchronous call for immediate result
                    Payload=json.dumps({
                        'action': 'unblock',
                        'user_id': user_id,
                        'reason': 'automatic_expiration',
                        'performed_by': 'system'
                    })
                )
                
                # Parse response
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload.get('statusCode') == 200:
                    logger.info(f"Successfully auto-unblocked expired user {user_id}")
                    
                    # Send notification about automatic unblock
                    send_notification(user_id, 'AUTO_UNBLOCKED', usage_record)
                    
                    return True
                else:
                    logger.error(f"Failed to auto-unblock expired user {user_id}: {response_payload.get('body', 'Unknown error')}")
                    return False
                    
            except Exception as unblock_error:
                logger.error(f"Error auto-unblocking expired user {user_id}: {str(unblock_error)}")
                return False
        else:
            logger.debug(f"Block for user {user_id} has not yet expired (expires at: {expires_at}, current: {current_time.isoformat()})")
            return False
            
    except Exception as e:
        logger.error(f"Error checking block expiration for {user_id}: {str(e)}")
        return False

def publish_cloudwatch_metrics(user_id: str, usage_record: Dict[str, Any]) -> None:
    """
    Publish real-time metrics to CloudWatch for dashboard consumption
    
    Args:
        user_id: The user ID
        usage_record: Current usage record from DynamoDB
    """
    try:
        current_count = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        team = usage_record.get('team', 'unknown')
        
        # Get current timestamp
        timestamp = datetime.utcnow()
        
        # Prepare metric data for individual user
        metric_data = [
            {
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'User',
                        'Value': user_id
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            }
        ]
        
        # Add team-level metric if team is known
        if team != 'unknown':
            metric_data.append({
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'Team',
                        'Value': team
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            })
            
            # Add combined user+team metric for detailed analysis
            metric_data.append({
                'MetricName': 'BedrockUsage',
                'Dimensions': [
                    {
                        'Name': 'User',
                        'Value': user_id
                    },
                    {
                        'Name': 'Team',
                        'Value': team
                    }
                ],
                'Value': 1,  # Each call represents 1 request
                'Unit': 'Count',
                'Timestamp': timestamp
            })
        
        # Publish metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='UserMetrics',
            MetricData=metric_data
        )
        
        logger.info(f"Published CloudWatch metrics for user {user_id} (team: {team})")
        
    except Exception as e:
        logger.error(f"Error publishing CloudWatch metrics for {user_id}: {str(e)}")

def send_notification(user_id: str, notification_type: str, usage_record: Dict[str, Any]) -> None:
    """
    Send notification via SNS and email
    
    Args:
        user_id: The user ID
        notification_type: Type of notification (WARNING, BLOCKED, UNBLOCKED, etc.)
        usage_record: Current usage record from DynamoDB
    """
    try:
        current_count = int(usage_record['request_count']) if isinstance(usage_record['request_count'], Decimal) else usage_record['request_count']
        daily_limit = int(usage_record['daily_limit']) if isinstance(usage_record['daily_limit'], Decimal) else usage_record['daily_limit']
        team = usage_record.get('team', 'unknown')
        
        # Prepare SNS message
        message = {
            'event_type': notification_type.lower(),
            'user_id': user_id,
            'team': team,
            'current_usage': current_count,
            'daily_limit': daily_limit,
            'timestamp': datetime.utcnow().isoformat(),
            'status': usage_record.get('status', 'UNKNOWN')
        }
        
        # Send SNS notification
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Bedrock Usage Alert: {notification_type} for {user_id}",
                Message=json.dumps(message, indent=2, cls=DecimalEncoder)
            )
            logger.info(f"SNS notification sent for {user_id}: {notification_type}")
        except Exception as e:
            logger.error(f"Failed to send SNS notification: {str(e)}")
        
        # Send email notification if email service is available
        if email_service and EMAIL_NOTIFICATIONS_ENABLED:
            try:
                email_sent = False
                
                if notification_type == 'WARNING':
                    email_sent = email_service.send_warning_email(user_id, usage_record)
                elif notification_type == 'BLOCKED':
                    email_sent = email_service.send_blocking_email(user_id, usage_record)
                elif notification_type == 'UNBLOCKED':
                    email_sent = email_service.send_unblocking_email(user_id)
                elif notification_type == 'AUTO_UNBLOCKED':
                    email_sent = email_service.send_unblocking_email(user_id, 'automatic_expiration')
                elif notification_type == 'ADMIN_BLOCKED':
                    # For admin blocking, we need the admin user info - using system for now
                    email_sent = email_service.send_admin_blocking_email(user_id, 'system', 'manual_admin_block', usage_record)
                elif notification_type == 'ADMIN_UNBLOCKED':
                    # For admin unblocking, we need the admin user info - using system for now
                    email_sent = email_service.send_admin_unblocking_email(user_id, 'system', 'manual_admin_unblock')
                
                if email_sent:
                    logger.info(f"Email notification sent successfully for {user_id}: {notification_type}")
                else:
                    logger.warning(f"Email notification failed for {user_id}: {notification_type}")
                    
            except Exception as e:
                logger.error(f"Error sending email notification for {user_id}: {str(e)}")
        else:
            logger.info(f"Email notifications disabled or service unavailable for {user_id}")
            
    except Exception as e:
        logger.error(f"Error sending notification for {user_id}: {str(e)}")
