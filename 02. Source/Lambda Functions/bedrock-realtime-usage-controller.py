#!/usr/bin/env python3
"""
AWS Bedrock Realtime Usage Controller - bedrock-realtime-usage-controller

This Lambda function merges the functionality of:
1. bedrock-realtime-logger-fixed (CloudTrail event processing, RDS MySQL, automatic blocking)
2. bedrock-policy-manager-enhanced (API event handling, manual operations, enhanced email service)

ENHANCED FEATURES:
- Handles both CloudTrail events (automatic blocking) and API events (manual operations)
- Uses RDS MySQL with pymysql for consistent data storage
- Enhanced email service integration via separate Lambda function
- Administrative protection workflow for manual operations
- Status checking endpoint for dashboard integration
- Proper CET timezone handling throughout
- Complete blocking/unblocking audit trail

Function Name: bedrock-realtime-usage-controller
Author: AWS Bedrock Usage Control System
Version: 3.0.0 (Enhanced Merged Version)
"""

import json
import boto3
import pymysql
import os
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Dict, Any, Optional, Tuple
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
iam = boto3.client('iam')
sns = boto3.client('sns')
lambda_client = boto3.client('lambda')

# RDS connection parameters
RDS_HOST = os.environ['RDS_ENDPOINT']
RDS_USER = os.environ['RDS_USERNAME']
RDS_PASSWORD = os.environ['RDS_PASSWORD']
RDS_DB = os.environ['RDS_DATABASE']

# SNS configuration for notifications
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', f'arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts')

# Enhanced email service configuration
EMAIL_SERVICE_LAMBDA_NAME = os.environ.get('EMAIL_SERVICE_LAMBDA_NAME', 'bedrock-email-service')
EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'

# CET timezone
CET = pytz.timezone('Europe/Madrid')

# Gmail SMTP configuration (fallback)
GMAIL_SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "user": "cline.aws.noreply@gmail.com",
    "password": "lozs wwqa vfpn nlup",
    "use_tls": True
}

EMAIL_SETTINGS = {
    "default_language": "es",
    "timezone": "Europe/Madrid",
    "reply_to": "cline.aws.noreply@gmail.com"
}

# Policy configuration for manual operations
BEDROCK_POLICY_SUFFIX = "_BedrockPolicy"
DENY_STATEMENT_SID = "DailyLimitBlock"

# Connection pool
connection_pool = None

def get_current_cet_time() -> datetime:
    """Get current time in CET timezone"""
    return datetime.now(CET)

def get_cet_timestamp_string() -> str:
    """Get current CET timestamp as string for database"""
    return get_current_cet_time().strftime('%Y-%m-%d %H:%M:%S')

def convert_utc_to_cet(utc_timestamp_str: str) -> str:
    """Convert UTC timestamp string to CET timestamp string"""
    try:
        if utc_timestamp_str.endswith('Z'):
            utc_timestamp_str = utc_timestamp_str[:-1]
        
        utc_dt = datetime.fromisoformat(utc_timestamp_str.replace('Z', '+00:00'))
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # Convert to CET
        cet_dt = utc_dt.astimezone(CET)
        cet_timestamp_str = cet_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"🕐 Converted UTC {utc_timestamp_str} to CET {cet_timestamp_str}")
        return cet_timestamp_str
        
    except Exception as e:
        logger.error(f"Failed to convert timestamp {utc_timestamp_str} to CET: {str(e)}")
        return get_cet_timestamp_string()

def get_mysql_connection():
    """Create MySQL connection with connection pooling"""
    global connection_pool
    
    if connection_pool is None:
        connection_pool = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5
        )
    
    try:
        connection_pool.ping(reconnect=True)
        return connection_pool
    except Exception as e:
        logger.error(f"Connection failed, creating new one: {str(e)}")
        connection_pool = pymysql.connect(
            host=RDS_HOST,
            user=RDS_USER,
            password=RDS_PASSWORD,
            database=RDS_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5
        )
        return connection_pool

def extract_user_from_arn(user_arn: str) -> Optional[str]:
    """Extract username from user ARN"""
    if not user_arn:
        return None
    
    # Pattern: arn:aws:iam::account:user/username
    match = re.search(r'arn:aws:iam::\d+:user/(.+)', user_arn)
    if match:
        return match.group(1)
    
    # Pattern: arn:aws:sts::account:assumed-role/role-name/username
    match = re.search(r'arn:aws:sts::\d+:assumed-role/[^/]+/(.+)', user_arn)
    if match:
        return match.group(1)
    
    return None

def get_user_team(user_id: str) -> str:
    """Get user's team from IAM tags"""
    try:
        response = iam.list_user_tags(UserName=user_id)
        
        for tag in response['Tags']:
            if tag['Key'].lower() in ['team', 'Team']:
                team_value = tag['Value']
                logger.info(f"Found Team tag for user {user_id}: {team_value}")
                return team_value
        
        logger.warning(f"No Team tag found for user {user_id}, trying groups as fallback")
        try:
            groups_response = iam.get_groups_for_user(UserName=user_id)
            groups = [group['GroupName'] for group in groups_response['Groups']]
            
            team_groups = [g for g in groups if g.startswith('yo_leo_')]
            
            if team_groups:
                logger.info(f"Found team group for user {user_id}: {team_groups[0]}")
                return team_groups[0]
        except Exception as group_error:
            logger.warning(f"Failed to get groups for user {user_id}: {str(group_error)}")
        
        logger.warning(f"No Team tag or team group found for user {user_id}, using 'unknown'")
        return 'unknown'
            
    except Exception as e:
        logger.error(f"Failed to get team for user {user_id}: {str(e)}")
        return 'unknown'

def get_user_person_tag(user_id: str) -> str:
    """Get user's person tag from IAM tags"""
    try:
        response = iam.list_user_tags(UserName=user_id)
        
        for tag in response['Tags']:
            if tag['Key'].lower() in ['person', 'Person']:
                person_value = tag['Value']
                logger.info(f"Found Person tag for user {user_id}: {person_value}")
                return person_value
        
        logger.warning(f"No Person tag found for user {user_id}, using 'Unknown'")
        return 'Unknown'
            
    except Exception as e:
        logger.error(f"Failed to get person tag for user {user_id}: {str(e)}")
        return 'Unknown'

def get_user_email(user_id: str) -> Optional[str]:
    """Get user's email from IAM tags"""
    try:
        response = iam.list_user_tags(UserName=user_id)
        
        for tag in response['Tags']:
            if tag['Key'].lower() in ['email', 'Email']:
                email_value = tag['Value']
                logger.info(f"Found Email tag for user {user_id}: {email_value}")
                return email_value
        
        logger.warning(f"No Email tag found for user {user_id}")
        return None
            
    except Exception as e:
        logger.error(f"Failed to get email tag for user {user_id}: {str(e)}")
        return None

def send_gmail_email(to_email: str, subject: str, body_text: str, body_html: str) -> bool:
    """Send email using Gmail SMTP"""
    try:
        logger.info(f"📧 Attempting to send Gmail email to {to_email}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = GMAIL_SMTP_CONFIG['user']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Reply-To'] = EMAIL_SETTINGS['reply_to']
        
        # Create text and HTML parts
        text_part = MIMEText(body_text, 'plain', 'utf-8')
        html_part = MIMEText(body_html, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(GMAIL_SMTP_CONFIG['server'], GMAIL_SMTP_CONFIG['port'])
        
        if GMAIL_SMTP_CONFIG['use_tls']:
            server.starttls()
        
        # Login and send email
        server.login(GMAIL_SMTP_CONFIG['user'], GMAIL_SMTP_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✅ Successfully sent Gmail email to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send Gmail email to {to_email}: {str(e)}")
        return False

def parse_bedrock_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse CloudTrail event for Bedrock API call"""
    try:
        logger.info(f"🔍 Starting to parse event: {event.get('eventName', 'Unknown')}")
        
        event_name = event.get('eventName', '')
        user_identity = event.get('userIdentity', {})
        request_parameters = event.get('requestParameters', {})
        source_ip = event.get('sourceIPAddress', '')
        user_agent = event.get('userAgent', '')
        request_id = event.get('requestID', '')
        event_time = event.get('eventTime', '')
        region = event.get('awsRegion', 'us-east-1')
        
        logger.info(f"📋 Event details - Name: {event_name}, User: {user_identity.get('userName', 'Unknown')}")
        
        cet_timestamp = convert_utc_to_cet(event_time)
        logger.info(f"🕐 Event time converted from UTC {event_time} to CET {cet_timestamp}")
        
        user_arn = user_identity.get('arn', '')
        user_id = extract_user_from_arn(user_arn)
        
        if not user_id:
            logger.warning(f"❌ Could not extract user ID from ARN: {user_arn}")
            return None
        
        logger.info(f"✅ Extracted user ID: {user_id}")
        
        model_id = request_parameters.get('modelId', '')
        if not model_id:
            logger.warning(f"❌ No model ID found in request parameters: {request_parameters}")
            return None
        
        logger.info(f"📱 Found model ID: {model_id}")
        
        # Process model ID
        actual_model_id = model_id
        if model_id.startswith('arn:aws:bedrock:'):
            if '/eu.anthropic.claude-sonnet-4-' in model_id:
                actual_model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
            elif '/anthropic.claude-' in model_id:
                parts = model_id.split('/')
                if len(parts) > 1:
                    actual_model_id = parts[-1]
                    if actual_model_id.startswith('eu.'):
                        actual_model_id = actual_model_id[3:]
        
        logger.info(f"Original model ID: {model_id}, Processed model ID: {actual_model_id}")
        
        model_name_mapping = {
            'anthropic.claude-3-opus-20240229-v1:0': 'Claude 3 Opus',
            'anthropic.claude-3-sonnet-20240229-v1:0': 'Claude 3 Sonnet',
            'anthropic.claude-3-haiku-20240307-v1:0': 'Claude 3 Haiku',
            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'Claude 3.5 Sonnet',
            'anthropic.claude-sonnet-4-20250514-v1:0': 'Claude 3.5 Sonnet',
            'amazon.titan-text-express-v1': 'Amazon Titan Text Express',
            'amazon.titan-text-lite-v1': 'Amazon Titan Text Lite'
        }
        
        model_name = model_name_mapping.get(actual_model_id, actual_model_id)
        
        request_type = 'invoke'
        if 'stream' in event_name.lower():
            request_type = 'invoke-stream'
        elif 'converse' in event_name.lower():
            request_type = 'converse-stream' if 'stream' in event_name.lower() else 'converse'
        
        response_time_ms = 0
        if 'responseTime' in event:
            response_time_ms = int(event['responseTime'])
        
        status_code = 200
        error_message = None
        if event.get('errorCode'):
            status_code = 400
            error_message = event.get('errorMessage', 'Unknown error')
        
        return {
            'user_id': user_id,
            'model_id': model_id,
            'model_name': model_name,
            'request_type': request_type,
            'region': region,
            'source_ip': source_ip,
            'user_agent': user_agent,
            'request_id': request_id,
            'response_time_ms': response_time_ms,
            'status_code': status_code,
            'error_message': error_message,
            'event_time': event_time,
            'cet_timestamp': cet_timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to parse Bedrock event: {str(e)}")
        return None

def check_user_blocking_status(connection, user_id: str) -> Tuple[bool, Optional[str]]:
    """Check if user is currently blocked and if block has expired"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT is_blocked, blocked_until, blocked_reason
                FROM user_blocking_status 
                WHERE user_id = %s
            """, [user_id])
            
            result = cursor.fetchone()
            if not result:
                return False, None
            
            is_blocked = result['is_blocked'] == 'Y'
            blocked_until = result['blocked_until']
            blocked_reason = result['blocked_reason']
            
            if not is_blocked:
                return False, None
            
            # Check if block has expired (compare with CET time)
            if blocked_until:
                current_cet_time = get_current_cet_time()
                # Convert blocked_until to CET if it's not timezone-aware
                if blocked_until.tzinfo is None:
                    blocked_until = CET.localize(blocked_until)
                
                if current_cet_time >= blocked_until:
                    logger.info(f"Block expired for user {user_id}, initiating automatic unblock")
                    execute_user_unblocking(connection, user_id)
                    return False, None
            
            return True, blocked_reason
            
    except Exception as e:
        logger.error(f"Failed to check user blocking status: {str(e)}")
        return False, None

def check_user_limits_with_protection(connection, user_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Check if user should be blocked based on current usage with administrative protection"""
    try:
        with connection.cursor() as cursor:
            # Get user limits and administrative protection
            cursor.execute("""
                SELECT daily_request_limit, monthly_request_limit, administrative_safe
                FROM user_limits 
                WHERE user_id = %s
            """, [user_id])
            
            limits_result = cursor.fetchone()
            if not limits_result:
                logger.warning(f"No limits found for user {user_id}, using defaults")
                daily_limit = 350
                monthly_limit = 5000
                administrative_safe = 'N'
            else:
                daily_limit = int(limits_result['daily_request_limit'])
                monthly_limit = int(limits_result['monthly_request_limit'])
                administrative_safe = limits_result.get('administrative_safe', 'N')
            
            # Check administrative protection
            if administrative_safe == 'Y':
                logger.info(f"User {user_id} has administrative protection - blocking disabled")
                return False, None, {
                    'daily_requests_used': 0,
                    'monthly_requests_used': 0,
                    'daily_percent': 0,
                    'monthly_percent': 0,
                    'daily_limit': daily_limit,
                    'monthly_limit': monthly_limit,
                    'administrative_safe': True
                }
            
            # Get current daily usage
            cursor.execute("""
                SELECT COUNT(*) as daily_requests_used
                FROM bedrock_requests 
                WHERE user_id = %s 
                AND DATE(request_timestamp) = CURDATE()
            """, [user_id])
            
            daily_result = cursor.fetchone()
            daily_requests_used = int(daily_result['daily_requests_used']) if daily_result else 0
            
            # Get current monthly usage
            cursor.execute("""
                SELECT COUNT(*) as monthly_requests_used
                FROM bedrock_requests 
                WHERE user_id = %s 
                AND DATE(request_timestamp) >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
            """, [user_id])
            
            monthly_result = cursor.fetchone()
            monthly_requests_used = int(monthly_result['monthly_requests_used']) if monthly_result else 0
            
            # Check if blocking is needed
            should_block = False
            block_reason = None
            
            if daily_requests_used >= daily_limit:
                should_block = True
                block_reason = 'Daily limit exceeded'
            elif monthly_requests_used >= monthly_limit:
                should_block = True
                block_reason = 'Monthly limit exceeded'
            
            daily_percent = (daily_requests_used / daily_limit) * 100 if daily_limit > 0 else 0
            monthly_percent = (monthly_requests_used / monthly_limit) * 100 if monthly_limit > 0 else 0
            
            usage_info = {
                'daily_requests_used': daily_requests_used,
                'monthly_requests_used': monthly_requests_used,
                'daily_percent': daily_percent,
                'monthly_percent': monthly_percent,
                'daily_limit': daily_limit,
                'monthly_limit': monthly_limit,
                'administrative_safe': False
            }
            
            logger.info(f"User {user_id} limits check: daily={daily_requests_used}/{daily_limit}, monthly={monthly_requests_used}/{monthly_limit}, should_block={should_block}, admin_safe={administrative_safe}")
            
            return should_block, block_reason, usage_info
            
    except Exception as e:
        logger.error(f"Failed to check user limits: {str(e)}")
        return False, None, {}

def execute_user_blocking(connection, user_id: str, block_reason: str, usage_info: Dict[str, Any]) -> bool:
    """Execute complete user blocking workflow with CET timestamps"""
    try:
        logger.info(f"🚫 EXECUTING USER BLOCKING for {user_id}: {block_reason}")
        
        current_cet_time = get_current_cet_time()
        current_cet_string = get_cet_timestamp_string()
        
        # Block until tomorrow at 00:00 CET
        blocked_until_cet = (current_cet_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        blocked_until_string = blocked_until_cet.strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"🕐 Blocking times - Current: {current_cet_string} CET, Until: {blocked_until_string} CET")
        
        # 1. Update USER_BLOCKING_STATUS table
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_blocking_status 
                    (user_id, is_blocked, blocked_reason, blocked_at, blocked_until, 
                     requests_at_blocking, last_request_at, created_at, updated_at)
                    VALUES (%s, 'Y', %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    is_blocked = 'Y',
                    blocked_reason = VALUES(blocked_reason),
                    blocked_at = VALUES(blocked_at),
                    blocked_until = VALUES(blocked_until),
                    requests_at_blocking = VALUES(requests_at_blocking),
                    last_request_at = VALUES(last_request_at),
                    updated_at = VALUES(updated_at)
                """, [
                    user_id, block_reason, current_cet_string, blocked_until_string,
                    usage_info['daily_requests_used'], current_cet_string, current_cet_string, current_cet_string
                ])
            logger.info(f"✅ Step 1: Updated USER_BLOCKING_STATUS for {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 1 FAILED: USER_BLOCKING_STATUS update for {user_id}: {str(e)}")
            return False
        
        # 2. Log to BLOCKING_AUDIT_LOG
        try:
            with connection.cursor() as cursor:
                # Calculate usage percentage
                usage_percentage = (usage_info['daily_requests_used'] / usage_info['daily_limit']) * 100 if usage_info['daily_limit'] > 0 else 0
                
                cursor.execute("""
                    INSERT INTO blocking_audit_log 
                    (user_id, operation_type, operation_reason, performed_by, operation_timestamp,
                     daily_requests_at_operation, daily_limit_at_operation, usage_percentage,
                     iam_policy_updated, email_sent, created_at)
                    VALUES (%s, 'BLOCK', %s, 'system', %s, %s, %s, %s, 'Y', 'Y', %s)
                """, [
                    user_id, block_reason, current_cet_string,
                    usage_info['daily_requests_used'], usage_info['daily_limit'], 
                    round(usage_percentage, 2), current_cet_string
                ])
            logger.info(f"✅ Step 2: Created BLOCKING_AUDIT_LOG entry for {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 2 FAILED: BLOCKING_AUDIT_LOG creation for {user_id}: {str(e)}")
            # Continue with other steps even if audit log fails
        
        # 3. Create IAM deny policy
        try:
            success = implement_iam_blocking(user_id)
            if success:
                logger.info(f"✅ Step 3: Created IAM deny policy for {user_id}")
            else:
                logger.error(f"❌ Step 3 FAILED: IAM policy creation for {user_id}")
                # Continue with email step even if IAM fails
        except Exception as e:
            logger.error(f"❌ Step 3 EXCEPTION: IAM policy creation for {user_id}: {str(e)}")
        
        # 4. Send Gmail notification
        try:
            success = send_blocking_email_gmail(user_id, block_reason, usage_info, blocked_until_cet)
            if success:
                logger.info(f"✅ Step 4: Sent blocking Gmail for {user_id}")
            else:
                logger.error(f"❌ Step 4 FAILED: Gmail sending for {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 4 EXCEPTION: Gmail sending for {user_id}: {str(e)}")
        
        logger.info(f"✅ Successfully executed complete blocking for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to execute user blocking for {user_id}: {str(e)}")
        return False

def execute_user_unblocking(connection, user_id: str) -> bool:
    """Execute complete user unblocking workflow with CET timestamps"""
    try:
        logger.info(f"🔓 EXECUTING USER UNBLOCKING for {user_id}")
        
        current_cet_string = get_cet_timestamp_string()
        
        # 1. Update USER_BLOCKING_STATUS table
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE user_blocking_status 
                    SET is_blocked = 'N',
                        blocked_reason = 'Automatic unblock',
                        blocked_until = NULL,
                        last_request_at = %s,
                        last_reset_at = %s,
                        updated_at = %s
                    WHERE user_id = %s
                """, [current_cet_string, current_cet_string, current_cet_string, user_id])
            logger.info(f"✅ Step 1: Updated USER_BLOCKING_STATUS for unblocking {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 1 FAILED: USER_BLOCKING_STATUS update for unblocking {user_id}: {str(e)}")
            return False
        
        # 2. Log to BLOCKING_AUDIT_LOG
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO blocking_audit_log 
                    (user_id, operation_type, operation_reason, performed_by, operation_timestamp, created_at)
                    VALUES (%s, 'UNBLOCK', 'Automatic unblock', 'system', %s, %s)
                """, [user_id, current_cet_string, current_cet_string])
            logger.info(f"✅ Step 2: Created BLOCKING_AUDIT_LOG entry for unblocking {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 2 FAILED: BLOCKING_AUDIT_LOG creation for unblocking {user_id}: {str(e)}")
        
        # 3. Modify IAM policy to allow
        try:
            success = implement_iam_unblocking(user_id)
            if success:
                logger.info(f"✅ Step 3: Modified IAM policy for unblocking {user_id}")
            else:
                logger.error(f"❌ Step 3 FAILED: IAM policy modification for unblocking {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 3 EXCEPTION: IAM policy modification for unblocking {user_id}: {str(e)}")
        
        # 4. Send unblocking Gmail
        try:
            success = send_unblocking_email_gmail(user_id)
            if success:
                logger.info(f"✅ Step 4: Sent unblocking Gmail for {user_id}")
            else:
                logger.error(f"❌ Step 4 FAILED: Gmail sending for unblocking {user_id}")
        except Exception as e:
            logger.error(f"❌ Step 4 EXCEPTION: Gmail sending for unblocking {user_id}: {str(e)}")
        
        logger.info(f"✅ Successfully executed complete unblocking for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to execute user unblocking for {user_id}: {str(e)}")
        return False

def implement_iam_blocking(user_id: str) -> bool:
    """Create IAM deny policy for user blocking"""
    try:
        policy_name = f"{user_id}_BedrockPolicy"
        
        deny_statement = {
            "Sid": "DailyLimitBlock",
            "Effect": "Deny",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:username": user_id
                }
            }
        }
        
        try:
            response = iam.get_user_policy(UserName=user_id, PolicyName=policy_name)
            current_policy = response['PolicyDocument']
            
            # Remove any existing deny statements
            current_policy['Statement'] = [
                stmt for stmt in current_policy['Statement'] 
                if stmt.get('Sid') != 'DailyLimitBlock'
            ]
            
            # Add new deny statement at the beginning
            current_policy['Statement'].insert(0, deny_statement)
            
        except iam.exceptions.NoSuchEntityException:
            current_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    deny_statement,
                    {
                        "Sid": "BedrockAccess",
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:InvokeModel",
                            "bedrock:InvokeModelWithResponseStream"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        
        iam.put_user_policy(
            UserName=user_id,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(current_policy, separators=(',', ':'))
        )
        
        logger.info(f"✅ Successfully created IAM deny policy for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create IAM deny policy for user {user_id}: {str(e)}")
        return False

def implement_iam_unblocking(user_id: str) -> bool:
    """Modify IAM policy to allow access for user unblocking"""
    try:
        policy_name = f"{user_id}_BedrockPolicy"
        
        try:
            response = iam.get_user_policy(UserName=user_id, PolicyName=policy_name)
            current_policy = response['PolicyDocument']
            
            # Remove deny statements
            current_policy['Statement'] = [
                stmt for stmt in current_policy['Statement'] 
                if stmt.get('Sid') != 'DailyLimitBlock'
            ]
            
            # Ensure there's at least an allow statement
            has_allow = any(stmt.get('Effect') == 'Allow' for stmt in current_policy['Statement'])
            if not has_allow:
                current_policy['Statement'].append({
                    "Sid": "BedrockAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    "Resource": "*"
                })
            
            iam.put_user_policy(
                UserName=user_id,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(current_policy, separators=(',', ':'))
            )
            
            logger.info(f"✅ Successfully modified IAM policy to allow access for user {user_id}")
            return True
            
        except iam.exceptions.NoSuchEntityException:
            logger.info(f"No existing policy found for user {user_id}, no action needed")
            return True
        
    except Exception as e:
        logger.error(f"❌ Failed to modify IAM policy for user {user_id}: {str(e)}")
        return False

def send_blocking_email_gmail(user_id: str, block_reason: str, usage_info: Dict[str, Any], blocked_until: datetime) -> bool:
    """Send blocking notification email using Gmail SMTP"""
    try:
        user_email = get_user_email(user_id)
        if not user_email:
            logger.warning(f"No email found for user {user_id}, skipping email notification")
            return False
        
        current_cet_string = get_cet_timestamp_string()
        blocked_until_string = blocked_until.strftime('%Y-%m-%d %H:%M:%S')
        
        subject = f"🚫 AWS Bedrock Access Blocked - {user_id}"
        
        body_html = f"""
        <html>
        <body>
            <h2>🚫 AWS Bedrock Access Blocked</h2>
            <p>Estimado/a {user_id},</p>
            
            <p>Su acceso a los servicios de AWS Bedrock ha sido temporalmente bloqueado debido a que ha superado los límites de uso establecidos.</p>
            
            <h3>Detalles del Bloqueo:</h3>
            <ul>
                <li><strong>Motivo:</strong> {block_reason}</li>
                <li><strong>Bloqueado el:</strong> {current_cet_string} CET</li>
                <li><strong>Bloqueado hasta:</strong> {blocked_until_string} CET</li>
            </ul>
            
            <h3>Uso Actual:</h3>
            <ul>
                <li><strong>Peticiones diarias:</strong> {usage_info['daily_requests_used']}/{usage_info['daily_limit']} ({usage_info['daily_percent']:.1f}%)</li>
                <li><strong>Peticiones mensuales:</strong> {usage_info['monthly_requests_used']}/{usage_info['monthly_limit']} ({usage_info['monthly_percent']:.1f}%)</li>
            </ul>
            
            <p>Su acceso será automáticamente restaurado el {blocked_until_string} CET.</p>
            
            <p>Si cree que esto es un error o necesita acceso inmediato, por favor contacte con su administrador del sistema.</p>
            
            <p>Saludos cordiales,<br>Sistema de Control de Uso de AWS Bedrock</p>
        </body>
        </html>
        """
        
        body_text = f"""
        🚫 AWS Bedrock Access Blocked
        
        Estimado/a {user_id},
        
        Su acceso a los servicios de AWS Bedrock ha sido temporalmente bloqueado debido a que ha superado los límites de uso establecidos.
        
        Detalles del Bloqueo:
        - Motivo: {block_reason}
        - Bloqueado el: {current_cet_string} CET
        - Bloqueado hasta: {blocked_until_string} CET
        
        Uso Actual:
        - Peticiones diarias: {usage_info['daily_requests_used']}/{usage_info['daily_limit']} ({usage_info['daily_percent']:.1f}%)
        - Peticiones mensuales: {usage_info['monthly_requests_used']}/{usage_info['monthly_limit']} ({usage_info['monthly_percent']:.1f}%)
        
        Su acceso será automáticamente restaurado el {blocked_until_string} CET.
        
        Si cree que esto es un error o necesita acceso inmediato, por favor contacte con su administrador del sistema.
        
        Saludos cordiales,
        Sistema de Control de Uso de AWS Bedrock
        """
        
        return send_gmail_email(user_email, subject, body_text, body_html)
        
    except Exception as e:
        logger.error(f"Failed to send blocking Gmail for user {user_id}: {str(e)}")
        return False

def send_unblocking_email_gmail(user_id: str) -> bool:
    """Send unblocking notification email using Gmail SMTP"""
    try:
        user_email = get_user_email(user_id)
        if not user_email:
            logger.warning(f"No email found for user {user_id}, skipping email notification")
            return False
        
        current_cet_string = get_cet_timestamp_string()
        
        subject = f"✅ AWS Bedrock Access Restored - {user_id}"
        
        body_html = f"""
        <html>
        <body>
            <h2>✅ AWS Bedrock Access Restored</h2>
            <p>Estimado/a {user_id},</p>
            
            <p>Su acceso a los servicios de AWS Bedrock ha sido automáticamente restaurado.</p>
            
            <h3>Detalles del Desbloqueo:</h3>
            <ul>
                <li><strong>Motivo:</strong> Desbloqueo automático</li>
                <li><strong>Restaurado el:</strong> {current_cet_string} CET</li>
            </ul>
            
            <p>Por favor, recuerde usar los servicios de AWS Bedrock de manera responsable y dentro de los límites asignados.</p>
            
            <p>Si tiene alguna pregunta sobre sus límites de uso, por favor contacte con su administrador del sistema.</p>
            
            <p>Saludos cordiales,<br>Sistema de Control de Uso de AWS Bedrock</p>
        </body>
        </html>
        """
        
        body_text = f"""
        ✅ AWS Bedrock Access Restored
        
        Estimado/a {user_id},
        
        Su acceso a los servicios de AWS Bedrock ha sido automáticamente restaurado.
        
        Detalles del Desbloqueo:
        - Motivo: Desbloqueo automático
        - Restaurado el: {current_cet_string} CET
        
        Por favor, recuerde usar los servicios de AWS Bedrock de manera responsable y dentro de los límites asignados.
        
        Si tiene alguna pregunta sobre sus límites de uso, por favor contacte con su administrador del sistema.
        
        Saludos cordiales,
        Sistema de Control de Uso de AWS Bedrock
        """
        
        return send_gmail_email(user_email, subject, body_text, body_html)
        
    except Exception as e:
        logger.error(f"Failed to send unblocking Gmail for user {user_id}: {str(e)}")
        return False

def log_bedrock_request_cet(connection, request_data: Dict[str, Any], team: str, person: str):
    """Log the Bedrock request to database with CET timestamp"""
    try:
        with connection.cursor() as cursor:
            insert_query = """
                INSERT INTO bedrock_requests (
                    user_id, team, person, model_id, request_id, source_ip, user_agent, aws_region, 
                    response_status, error_message, processing_time_ms, request_timestamp, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            current_cet_timestamp = get_cet_timestamp_string()
            
            cursor.execute(insert_query, [
                request_data['user_id'],
                team,
                person,
                request_data['model_id'],
                request_data['request_id'],
                request_data['source_ip'],
                request_data['user_agent'][:1000] if request_data['user_agent'] else None,
                request_data['region'],
                'success' if request_data['status_code'] == 200 else 'error',
                request_data['error_message'],
                request_data['response_time_ms'],
                request_data['cet_timestamp'],
                current_cet_timestamp
            ])
            
            logger.info(f"✅ Logged request for user {request_data['user_id']}, team {team}, person {person}")
            
    except Exception as e:
        logger.error(f"Failed to log request: {str(e)}")
        raise

def ensure_user_exists(connection, user_id: str, team: str, person: str):
    """Ensure user exists in user_limits table, create if not"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM user_limits WHERE user_id = %s", [user_id])
            if cursor.fetchone():
                return
            
            current_cet_timestamp = get_cet_timestamp_string()
            
            daily_request_limit = 350
            monthly_request_limit = 5000
            
            cursor.execute("""
                INSERT INTO user_limits (user_id, team, person, daily_request_limit, monthly_request_limit, administrative_safe, created_at)
                VALUES (%s, %s, %s, %s, %s, 'N', %s)
            """, [user_id, team, person, daily_request_limit, monthly_request_limit, current_cet_timestamp])
            
            logger.info(f"✅ Created new user limits: {user_id} in team {team}, person: {person}")
            
    except Exception as e:
        logger.error(f"Failed to ensure user exists: {str(e)}")

def lambda_handler(event, context):
    """
    Enhanced Lambda handler supporting both CloudTrail and API events
    
    Args:
        event: Event containing either CloudTrail data or API action parameters
        context: Lambda context object
        
    Returns:
        Dict with status code and operation results
    """
    logger.info(f"🚀 Processing event with ENHANCED MERGED FUNCTIONALITY: {json.dumps(event, default=str)}")
    
    # NEW: Check if this is an API event (manual operation)
    if 'action' in event and 'user_id' in event:
        logger.info("🔧 Processing API event (manual operation)")
        return handle_api_event(event, context)
    
    # EXISTING: Handle CloudTrail events (automatic blocking)
    logger.info("📊 Processing CloudTrail event (automatic blocking)")
    return handle_cloudtrail_event(event, context)

def handle_api_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle manual admin operations from dashboard"""
    try:
        logger.info(f"Processing API event: {json.dumps(event, default=str)}")
        
        # Validate required parameters
        if 'action' not in event or 'user_id' not in event:
            logger.error("Missing required parameters: action and user_id")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters: action and user_id'})
            }
        
        action = event['action']
        user_id = event['user_id']
        reason = event.get('reason', 'unspecified')
        
        logger.info(f"Processing {action} action for user {user_id}, reason: {reason}")
        
        # Route to appropriate handler
        if action == 'block':
            result = manual_block_user(event)
        elif action == 'unblock':
            result = manual_unblock_user(event)
        elif action == 'check_status':
            result = check_user_status(event)
        else:
            logger.error(f"Invalid action: {action}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid action: {action}'})
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing API event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def manual_block_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle manual admin blocking"""
    try:
        user_id = event['user_id']
        reason = event.get('reason', 'Manual admin block')
        performed_by = event.get('performed_by', 'admin')
        
        logger.info(f"🚫 Manual blocking user {user_id} by {performed_by}")
        
        connection = get_mysql_connection()
        
        # Get current usage from RDS
        usage_info = get_user_current_usage(connection, user_id)
        
        # Execute blocking with admin expiration (24 hours)
        success = execute_admin_blocking(connection, user_id, reason, performed_by, usage_info)
        
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': f'User {user_id} blocked successfully' if success else 'Blocking failed',
                'action': 'block',
                'user_id': user_id,
                'performed_by': performed_by,
                'blocked_at': get_cet_timestamp_string()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in manual_block_user: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error blocking user {user_id}: {str(e)}',
                'action': 'block',
                'user_id': user_id
            })
        }

def manual_unblock_user(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle manual admin unblocking"""
    try:
        user_id = event['user_id']
        reason = event.get('reason', 'Manual admin unblock')
        performed_by = event.get('performed_by', 'admin')
        
        logger.info(f"🔓 Manual unblocking user {user_id} by {performed_by}")
        
        connection = get_mysql_connection()
        
        # Execute unblocking with admin protection
        success = execute_admin_unblocking(connection, user_id, reason, performed_by)
        
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': f'User {user_id} unblocked successfully' if success else 'Unblocking failed',
                'action': 'unblock',
                'user_id': user_id,
                'performed_by': performed_by,
                'unblocked_at': get_cet_timestamp_string()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in manual_unblock_user: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error unblocking user {user_id}: {str(e)}',
                'action': 'unblock',
                'user_id': user_id
            })
        }

def check_user_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Check user blocking status for dashboard"""
    try:
        user_id = event['user_id']
        
        logger.info(f"🔍 Checking status for user {user_id}")
        
        connection = get_mysql_connection()
        
        with connection.cursor() as cursor:
            # Get blocking status
            cursor.execute("""
                SELECT is_blocked, blocked_reason, blocked_at, blocked_until, 
                       performed_by, block_type
                FROM user_blocking_status 
                WHERE user_id = %s
            """, [user_id])
            
            status_result = cursor.fetchone()
            
            # Get usage info
            cursor.execute("""
                SELECT daily_request_limit, administrative_safe
                FROM user_limits 
                WHERE user_id = %s
            """, [user_id])
            
            limits_result = cursor.fetchone()
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'user_id': user_id,
                    'is_blocked': status_result['is_blocked'] == 'Y' if status_result else False,
                    'block_reason': status_result['blocked_reason'] if status_result else None,
                    'blocked_since': status_result['blocked_at'].isoformat() if status_result and status_result['blocked_at'] else None,
                    'expires_at': status_result['blocked_until'].isoformat() if status_result and status_result['blocked_until'] else None,
                    'block_type': status_result.get('block_type', 'None') if status_result else 'None',
                    'performed_by': status_result.get('performed_by') if status_result else None,
                    'administrative_safe': limits_result['administrative_safe'] == 'Y' if limits_result else False,
                    'checked_at': datetime.utcnow().isoformat()
                })
            }
            
    except Exception as e:
        logger.error(f"Error checking user status: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'user_id': user_id})
        }

def handle_cloudtrail_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle CloudTrail events (automatic blocking) - Original functionality"""
    connection = None
    processed_requests = 0
    blocked_requests = 0
    unblocked_requests = 0
    
    try:
        connection = get_mysql_connection()
        logger.info("✅ Successfully connected to MySQL database")
        
        events_to_process = []
        
        if 'detail' in event and 'Records' not in event:
            logger.info("🔍 Processing direct CloudWatch event")
            events_to_process = [event['detail']]
        else:
            logger.info("🔍 Processing Records-based event")
            records = event.get('Records', [])
            for record in records:
                if 's3' in record:
                    logger.info("S3 CloudTrail delivery not implemented yet")
                    continue
                detail = record.get('detail', record)
                events_to_process.append(detail)
        
        logger.info(f"📋 Found {len(events_to_process)} events to process")
        
        for i, detail in enumerate(events_to_process):
            try:
                logger.info(f"🔍 Processing event {i+1}/{len(events_to_process)}")
                
                request_data = parse_bedrock_event(detail)
                if not request_data:
                    logger.warning(f"❌ Failed to parse request data for event {i+1}")
                    continue
                
                user_id = request_data['user_id']
                
                team = get_user_team(user_id)
                person = get_user_person_tag(user_id)
                
                ensure_user_exists(connection, user_id, team, person)
                
                # 1. Check if user is currently blocked and handle automatic unblocking
                is_blocked, block_reason = check_user_blocking_status(connection, user_id)
                if is_blocked:
                    logger.warning(f"🚫 User {user_id} is currently blocked: {block_reason}")
                    continue  # Don't process requests from blocked users
                
                # 2. Check if user should be blocked (with administrative protection)
                should_block, new_block_reason, usage_info = check_user_limits_with_protection(connection, user_id)
                
                if should_block:
                    blocked_requests += 1
                    logger.warning(f"🚫 User {user_id} should be blocked: {new_block_reason}")
                    
                    # Execute complete blocking workflow
                    blocking_success = execute_user_blocking(connection, user_id, new_block_reason, usage_info)
                    
                    if blocking_success:
                        logger.info(f"✅ Successfully executed complete blocking for user {user_id}")
                    else:
                        logger.error(f"❌ Failed to execute complete blocking for user {user_id}")
                    
                    # Don't log the request that triggered the block
                    continue
                
                # 3. Log the request normally
                log_bedrock_request_cet(connection, request_data, team, person)
                processed_requests += 1
                
                logger.info(f"User {user_id} usage: {usage_info['daily_requests_used']}/{usage_info['daily_limit']} daily requests ({usage_info['daily_percent']:.1f}%), "
                           f"{usage_info['monthly_requests_used']}/{usage_info['monthly_limit']} monthly requests ({usage_info['monthly_percent']:.1f}%)")
                
            except Exception as record_error:
                logger.error(f"Failed to process record: {str(record_error)}")
                continue
        
        logger.info(f"✅ Processed {processed_requests} requests, BLOCKED {blocked_requests} users, UNBLOCKED {unblocked_requests} users")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed Bedrock requests with ENHANCED MERGED FUNCTIONALITY',
                'processed_requests': processed_requests,
                'blocked_requests': blocked_requests,
                'unblocked_requests': unblocked_requests
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process Bedrock requests'
            })
        }
    
    finally:
        # Don't close connection - keep it for reuse
        pass

# NEW FUNCTIONS FOR MANUAL OPERATIONS

def get_user_current_usage(connection, user_id: str) -> Dict[str, Any]:
    """Get current usage information for user"""
    try:
        with connection.cursor() as cursor:
            # Get user limits
            cursor.execute("""
                SELECT daily_request_limit, monthly_request_limit, administrative_safe
                FROM user_limits 
                WHERE user_id = %s
            """, [user_id])
            
            limits_result = cursor.fetchone()
            if not limits_result:
                daily_limit = 350
                monthly_limit = 5000
                administrative_safe = 'N'
            else:
                daily_limit = int(limits_result['daily_request_limit'])
                monthly_limit = int(limits_result['monthly_request_limit'])
                administrative_safe = limits_result.get('administrative_safe', 'N')
            
            # Get current daily usage
            cursor.execute("""
                SELECT COUNT(*) as daily_requests_used
                FROM bedrock_requests 
                WHERE user_id = %s 
                AND DATE(request_timestamp) = CURDATE()
            """, [user_id])
            
            daily_result = cursor.fetchone()
            daily_requests_used = int(daily_result['daily_requests_used']) if daily_result else 0
            
            # Get current monthly usage
            cursor.execute("""
                SELECT COUNT(*) as monthly_requests_used
                FROM bedrock_requests 
                WHERE user_id = %s 
                AND DATE(request_timestamp) >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
            """, [user_id])
            
            monthly_result = cursor.fetchone()
            monthly_requests_used = int(monthly_result['monthly_requests_used']) if monthly_result else 0
            
            daily_percent = (daily_requests_used / daily_limit) * 100 if daily_limit > 0 else 0
            monthly_percent = (monthly_requests_used / monthly_limit) * 100 if monthly_limit > 0 else 0
            
            return {
                'daily_requests_used': daily_requests_used,
                'monthly_requests_used': monthly_requests_used,
                'daily_percent': daily_percent,
                'monthly_percent': monthly_percent,
                'daily_limit': daily_limit,
                'monthly_limit': monthly_limit,
                'administrative_safe': administrative_safe == 'Y'
            }
            
    except Exception as e:
        logger.error(f"Failed to get user current usage: {str(e)}")
        return {
            'daily_requests_used': 0,
            'monthly_requests_used': 0,
            'daily_percent': 0,
            'monthly_percent': 0,
            'daily_limit': 350,
            'monthly_limit': 5000,
            'administrative_safe': False
        }

def execute_admin_blocking(connection, user_id: str, reason: str, performed_by: str, usage_info: Dict[str, Any]) -> bool:
    """Execute admin blocking with 24-hour expiration"""
    try:
        current_cet_time = get_current_cet_time()
        current_cet_string = get_cet_timestamp_string()
        
        # Admin blocks expire in 24 hours, not at daily reset
        blocked_until_cet = current_cet_time + timedelta(hours=24)
        blocked_until_string = blocked_until_cet.strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"🚫 Admin blocking {user_id} until {blocked_until_string} CET")
        
        # Update blocking status with admin info
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_blocking_status 
                (user_id, is_blocked, blocked_reason, blocked_at, blocked_until, 
                 performed_by, block_type, created_at, updated_at)
                VALUES (%s, 'Y', %s, %s, %s, %s, 'ADMIN', %s, %s)
                ON DUPLICATE KEY UPDATE
                is_blocked = 'Y', blocked_reason = VALUES(blocked_reason),
                blocked_at = VALUES(blocked_at), blocked_until = VALUES(blocked_until),
                performed_by = VALUES(performed_by), block_type = 'ADMIN',
                updated_at = VALUES(updated_at)
            """, [user_id, reason, current_cet_string, blocked_until_string, 
                  performed_by, current_cet_string, current_cet_string])
        
        # Log to audit
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO blocking_audit_log 
                (user_id, operation_type, operation_reason, performed_by, operation_timestamp, created_at)
                VALUES (%s, 'BLOCK', %s, %s, %s, %s)
            """, [user_id, reason, performed_by, current_cet_string, current_cet_string])
        
        # Create IAM deny policy
        implement_iam_blocking(user_id)
        
        # Send enhanced email notification
        send_enhanced_blocking_email(user_id, reason, usage_info, performed_by)
        
        logger.info(f"✅ Successfully executed admin blocking for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to execute admin blocking for {user_id}: {str(e)}")
        return False

def execute_admin_unblocking(connection, user_id: str, reason: str, performed_by: str) -> bool:
    """Execute admin unblocking with protection flag"""
    try:
        current_cet_string = get_cet_timestamp_string()
        
        logger.info(f"🔓 Admin unblocking {user_id}")
        
        # Update blocking status
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user_blocking_status 
                SET is_blocked = 'N',
                    blocked_reason = %s,
                    blocked_until = NULL,
                    updated_at = %s
                WHERE user_id = %s
            """, [reason, current_cet_string, user_id])
        
        # Set administrative protection to prevent automatic re-blocking today
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user_limits 
                SET administrative_safe = 'Y', 
                    admin_protection_by = %s,
                    admin_protection_at = %s,
                    updated_at = %s
                WHERE user_id = %s
            """, [performed_by, current_cet_string, current_cet_string, user_id])
        
        # Log to audit
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO blocking_audit_log 
                (user_id, operation_type, operation_reason, performed_by, operation_timestamp, created_at)
                VALUES (%s, 'UNBLOCK', %s, %s, %s, %s)
            """, [user_id, reason, performed_by, current_cet_string, current_cet_string])
        
        # Remove IAM deny policy
        implement_iam_unblocking(user_id)
        
        # Send enhanced email notification
        send_enhanced_unblocking_email(user_id, reason, performed_by)
        
        logger.info(f"✅ Successfully executed admin unblocking for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to execute admin unblocking for {user_id}: {str(e)}")
        return False

def send_enhanced_blocking_email(user_id: str, reason: str, usage_info: Dict[str, Any], performed_by: str) -> bool:
    """Send enhanced blocking email via separate Lambda service"""
    try:
        if performed_by != 'system':
            # Admin blocking email
            email_payload = {
                'action': 'send_admin_blocking_email',
                'user_id': user_id,
                'performed_by': performed_by,
                'reason': reason,
                'usage_record': usage_info
            }
        else:
            # Automatic blocking email
            email_payload = {
                'action': 'send_blocking_email',
                'user_id': user_id,
                'usage_record': usage_info,
                'reason': reason
            }
        
        if EMAIL_NOTIFICATIONS_ENABLED:
            response = lambda_client.invoke(
                FunctionName=EMAIL_SERVICE_LAMBDA_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps(email_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            success = response_payload.get('statusCode') == 200
            
            if success:
                logger.info(f"✅ Enhanced email sent for blocking {user_id}")
            else:
                logger.warning(f"⚠️ Enhanced email failed for {user_id}, falling back to Gmail")
                # Fallback to existing Gmail functionality
                return send_blocking_email_gmail(user_id, reason, usage_info, 
                                               get_current_cet_time() + timedelta(hours=24))
            
            return success
        else:
            logger.info("Email notifications disabled")
            return True
        
    except Exception as e:
        logger.error(f"Enhanced email service failed, falling back to Gmail: {str(e)}")
        # Fallback to existing Gmail functionality
        return send_blocking_email_gmail(user_id, reason, usage_info, 
                                       get_current_cet_time() + timedelta(hours=24))

def send_enhanced_unblocking_email(user_id: str, reason: str, performed_by: str) -> bool:
    """Send enhanced unblocking email via separate Lambda service"""
    try:
        if performed_by != 'system' and performed_by != 'daily_reset':
            # Admin unblocking email
            email_payload = {
                'action': 'send_admin_unblocking_email',
                'user_id': user_id,
                'performed_by': performed_by,
                'reason': reason
            }
        else:
            # Automatic unblocking email
            email_payload = {
                'action': 'send_unblocking_email',
                'user_id': user_id,
                'reason': reason
            }
        
        if EMAIL_NOTIFICATIONS_ENABLED:
            response = lambda_client.invoke(
                FunctionName=EMAIL_SERVICE_LAMBDA_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps(email_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            success = response_payload.get('statusCode') == 200
            
            if success:
                logger.info(f"✅ Enhanced email sent for unblocking {user_id}")
            else:
                logger.warning(f"⚠️ Enhanced email failed for {user_id}, falling back to Gmail")
                # Fallback to existing Gmail functionality
                return send_unblocking_email_gmail(user_id)
            
            return success
        else:
            logger.info("Email notifications disabled")
            return True
        
    except Exception as e:
        logger.error(f"Enhanced email service failed, falling back to Gmail: {str(e)}")
        # Fallback to existing Gmail functionality
        return send_unblocking_email_gmail(user_id)
