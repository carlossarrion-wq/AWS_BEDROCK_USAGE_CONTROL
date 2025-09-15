#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Daily Reset Lambda
===========================================================

This Lambda function performs daily reset operations including:
1. Resetting daily usage counters for all users
2. Unblocking all currently blocked users
3. Archiving previous day's data (optional)
4. Sending daily summary notifications
5. Preparing system for new day operations

Triggered by CloudWatch Events cron schedule at 00:00 UTC daily.

Author: AWS Bedrock Usage Control System
Version: 1.0.0
"""

import json
import boto3
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from boto3.dynamodb.conditions import Key, Attr
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'bedrock_user_daily_usage')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', f'arn:aws:sns:{REGION}:{ACCOUNT_ID}:bedrock-usage-alerts')
POLICY_MANAGER_FUNCTION = os.environ.get('POLICY_MANAGER_FUNCTION', 'bedrock-policy-manager')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for daily reset operations
    
    Args:
        event: CloudWatch Events cron event or manual trigger
        context: Lambda context object
        
    Returns:
        Dict with status code and reset results
    """
    try:
        logger.info(f"Starting daily reset at {datetime.utcnow().isoformat()}")
        logger.info(f"Event: {json.dumps(event, default=str)}")
        
        reset_results = {
            'reset_timestamp': datetime.utcnow().isoformat(),
            'users_processed': 0,
            'users_unblocked': 0,
            'users_reset': 0,
            'errors': [],
            'summary': {}
        }
        
        # Step 1: Get all users from yesterday's records
        yesterday_users = get_yesterday_users()
        logger.info(f"Found {len(yesterday_users)} users from yesterday")
        
        # Step 2: Generate daily summary before reset
        daily_summary = generate_daily_summary(yesterday_users)
        reset_results['summary'] = daily_summary
        
        # Step 3: Unblock all currently blocked users
        unblock_results = unblock_all_users(yesterday_users)
        reset_results['users_unblocked'] = unblock_results['unblocked_count']
        reset_results['errors'].extend(unblock_results['errors'])
        
        # Step 4: Reset daily counters for all users
        reset_counter_results = reset_daily_counters(yesterday_users)
        reset_results['users_reset'] = reset_counter_results['reset_count']
        reset_results['errors'].extend(reset_counter_results['errors'])
        
        # Step 5: Archive yesterday's data (optional)
        archive_results = archive_yesterday_data(yesterday_users)
        reset_results['users_processed'] = len(yesterday_users)
        
        # Step 6: Send daily summary notifications
        send_daily_summary_notification(daily_summary, reset_results)
        
        logger.info(f"Daily reset completed successfully: {reset_results}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily reset completed successfully',
                'results': reset_results
            })
        }
        
    except Exception as e:
        logger.error(f"Error during daily reset: {str(e)}", exc_info=True)
        
        # Send error notification
        send_error_notification(str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Daily reset failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def get_yesterday_users() -> List[Dict[str, Any]]:
    """
    Get all user records from yesterday
    
    Returns:
        List of user records from yesterday
    """
    try:
        table = dynamodb.Table(TABLE_NAME)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        logger.info(f"Scanning for users from date: {yesterday}")
        
        # Scan for yesterday's records
        response = table.scan(
            FilterExpression=Key('date').eq(yesterday)
        )
        
        users = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=Key('date').eq(yesterday),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            users.extend(response['Items'])
        
        logger.info(f"Retrieved {len(users)} user records from yesterday")
        return users
        
    except Exception as e:
        logger.error(f"Error getting yesterday's users: {str(e)}")
        return []

def generate_daily_summary(users: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate daily summary statistics
    
    Args:
        users: List of user records from yesterday
        
    Returns:
        Dict with daily summary statistics
    """
    try:
        summary = {
            'date': (date.today() - timedelta(days=1)).isoformat(),
            'total_users': len(users),
            'total_requests': 0,
            'blocked_users': 0,
            'warning_users': 0,
            'active_users': 0,
            'teams': {},
            'top_users': [],
            'limit_exceeded_users': []
        }
        
        # Process each user record
        for user in users:
            user_id = user.get('user_id', 'unknown')
            request_count = int(user.get('request_count', 0))
            status = user.get('status', 'ACTIVE')
            team = user.get('team', 'unknown')
            daily_limit = int(user.get('daily_limit', 50))
            
            # Aggregate totals
            summary['total_requests'] += request_count
            
            # Count by status
            if status == 'BLOCKED':
                summary['blocked_users'] += 1
                summary['limit_exceeded_users'].append({
                    'user_id': user_id,
                    'requests': request_count,
                    'limit': daily_limit,
                    'team': team
                })
            elif status == 'WARNING':
                summary['warning_users'] += 1
            else:
                summary['active_users'] += 1
            
            # Aggregate by team
            if team not in summary['teams']:
                summary['teams'][team] = {
                    'users': 0,
                    'requests': 0,
                    'blocked': 0,
                    'warnings': 0
                }
            
            summary['teams'][team]['users'] += 1
            summary['teams'][team]['requests'] += request_count
            if status == 'BLOCKED':
                summary['teams'][team]['blocked'] += 1
            elif status == 'WARNING':
                summary['teams'][team]['warnings'] += 1
        
        # Generate top users list
        sorted_users = sorted(users, key=lambda x: int(x.get('request_count', 0)), reverse=True)
        summary['top_users'] = [
            {
                'user_id': user.get('user_id'),
                'requests': int(user.get('request_count', 0)),
                'limit': int(user.get('daily_limit', 50)),
                'team': user.get('team', 'unknown'),
                'status': user.get('status', 'ACTIVE')
            }
            for user in sorted_users[:10]  # Top 10 users
        ]
        
        logger.info(f"Generated daily summary: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}")
        return {
            'date': (date.today() - timedelta(days=1)).isoformat(),
            'error': str(e)
        }

def unblock_all_users(users: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Unblock all currently blocked users
    
    Args:
        users: List of user records
        
    Returns:
        Dict with unblock results
    """
    try:
        results = {
            'unblocked_count': 0,
            'errors': [],
            'unblocked_users': []
        }
        
        # Find all blocked users
        blocked_users = [user for user in users if user.get('status') == 'BLOCKED']
        
        logger.info(f"Found {len(blocked_users)} blocked users to unblock")
        
        for user in blocked_users:
            user_id = user.get('user_id')
            
            try:
                # Invoke policy manager to unblock user
                response = lambda_client.invoke(
                    FunctionName=POLICY_MANAGER_FUNCTION,
                    InvocationType='RequestResponse',  # Synchronous call
                    Payload=json.dumps({
                        'action': 'unblock',
                        'user_id': user_id,
                        'reason': 'daily_reset'
                    })
                )
                
                # Parse response
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload.get('statusCode') == 200:
                    results['unblocked_count'] += 1
                    results['unblocked_users'].append(user_id)
                    logger.info(f"Successfully unblocked user {user_id}")
                else:
                    error_msg = f"Failed to unblock user {user_id}: {response_payload.get('body', 'Unknown error')}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                
            except Exception as e:
                error_msg = f"Error unblocking user {user_id}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Unblock operation completed: {results['unblocked_count']} users unblocked")
        return results
        
    except Exception as e:
        logger.error(f"Error in unblock_all_users: {str(e)}")
        return {
            'unblocked_count': 0,
            'errors': [str(e)],
            'unblocked_users': []
        }

def reset_daily_counters(users: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reset daily counters for all users
    
    Args:
        users: List of user records from yesterday
        
    Returns:
        Dict with reset results
    """
    try:
        table = dynamodb.Table(TABLE_NAME)
        today = date.today().isoformat()
        
        results = {
            'reset_count': 0,
            'errors': [],
            'reset_users': []
        }
        
        logger.info(f"Resetting counters for {len(users)} users to date: {today}")
        
        for user in users:
            user_id = user.get('user_id')
            
            try:
                # Create today's record with reset counters (clear admin protection)
                today_record = {
                    'user_id': user_id,
                    'date': today,
                    'request_count': 0,
                    'status': 'ACTIVE',
                    'daily_limit': user.get('daily_limit', 50),
                    'warning_threshold': user.get('warning_threshold', 40),
                    'team': user.get('team', 'unknown'),
                    'last_request_time': None,
                    'first_seen': user.get('first_seen'),  # Preserve original first_seen
                    'reset_at': datetime.utcnow().isoformat(),
                    'ttl': int((datetime.utcnow().timestamp() + 86400 * 7)),  # 7 days TTL
                    # Clear administrative protection flags for new day
                    'admin_protection': False,
                    'admin_protection_by': None,
                    'admin_protection_at': None
                }
                
                # Put the new record
                table.put_item(Item=today_record)
                
                results['reset_count'] += 1
                results['reset_users'].append(user_id)
                logger.debug(f"Reset counter for user {user_id}")
                
            except Exception as e:
                error_msg = f"Error resetting counter for user {user_id}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Counter reset completed: {results['reset_count']} users reset")
        return results
        
    except Exception as e:
        logger.error(f"Error in reset_daily_counters: {str(e)}")
        return {
            'reset_count': 0,
            'errors': [str(e)],
            'reset_users': []
        }

def archive_yesterday_data(users: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Archive yesterday's data (optional - data will be automatically deleted by TTL)
    
    Args:
        users: List of user records from yesterday
        
    Returns:
        Dict with archive results
    """
    try:
        # For now, we rely on TTL for automatic cleanup
        # In the future, we could implement archiving to S3 or another storage
        
        logger.info(f"Data archiving skipped - relying on TTL for cleanup of {len(users)} records")
        
        return {
            'archived_count': 0,
            'method': 'ttl_cleanup',
            'message': 'Relying on DynamoDB TTL for automatic data cleanup'
        }
        
    except Exception as e:
        logger.error(f"Error in archive_yesterday_data: {str(e)}")
        return {
            'archived_count': 0,
            'error': str(e)
        }

def send_daily_summary_notification(summary: Dict[str, Any], reset_results: Dict[str, Any]) -> None:
    """
    Send daily summary notification
    
    Args:
        summary: Daily summary statistics
        reset_results: Results from reset operations
    """
    try:
        message = {
            'event_type': 'daily_reset_summary',
            'reset_timestamp': reset_results['reset_timestamp'],
            'summary': summary,
            'reset_results': {
                'users_processed': reset_results['users_processed'],
                'users_unblocked': reset_results['users_unblocked'],
                'users_reset': reset_results['users_reset'],
                'error_count': len(reset_results['errors'])
            }
        }
        
        # Create human-readable summary
        readable_summary = f"""
Daily Bedrock Usage Reset Summary - {summary.get('date', 'Unknown')}

📊 USAGE STATISTICS:
• Total Users: {summary.get('total_users', 0)}
• Total Requests: {summary.get('total_requests', 0):,}
• Blocked Users: {summary.get('blocked_users', 0)}
• Warning Users: {summary.get('warning_users', 0)}
• Active Users: {summary.get('active_users', 0)}

🔄 RESET OPERATIONS:
• Users Processed: {reset_results['users_processed']}
• Users Unblocked: {reset_results['users_unblocked']}
• Users Reset: {reset_results['users_reset']}
• Errors: {len(reset_results['errors'])}

🏆 TOP USERS (by requests):
"""
        
        for i, user in enumerate(summary.get('top_users', [])[:5], 1):
            readable_summary += f"{i}. {user['user_id']}: {user['requests']} requests ({user['team']})\n"
        
        if summary.get('limit_exceeded_users'):
            readable_summary += f"\n⚠️  USERS WHO EXCEEDED LIMITS:\n"
            for user in summary.get('limit_exceeded_users', [])[:5]:
                readable_summary += f"• {user['user_id']}: {user['requests']}/{user['limit']} ({user['team']})\n"
        
        if reset_results['errors']:
            readable_summary += f"\n❌ ERRORS:\n"
            for error in reset_results['errors'][:3]:
                readable_summary += f"• {error}\n"
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Bedrock Daily Reset Summary - {summary.get('date')}",
            Message=readable_summary
        )
        
        logger.info("Sent daily summary notification")
        
    except Exception as e:
        logger.error(f"Error sending daily summary notification: {str(e)}")

def send_error_notification(error_message: str) -> None:
    """
    Send error notification when daily reset fails
    
    Args:
        error_message: Error message to send
    """
    try:
        message = {
            'event_type': 'daily_reset_error',
            'error_timestamp': datetime.utcnow().isoformat(),
            'error_message': error_message
        }
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="🚨 Bedrock Daily Reset FAILED",
            Message=f"""
CRITICAL: Bedrock Daily Reset Failed

Timestamp: {datetime.utcnow().isoformat()}
Error: {error_message}

This requires immediate attention as users may remain blocked and counters may not reset properly.

Please check CloudWatch logs for detailed error information.
"""
        )
        
        logger.info("Sent error notification")
        
    except Exception as e:
        logger.error(f"Error sending error notification: {str(e)}")

# For testing purposes
if __name__ == "__main__":
    # Test event (CloudWatch Events cron trigger)
    test_event = {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "701055077130",
        "time": "2025-01-16T00:00:00Z",
        "region": "eu-west-1",
        "resources": [
            "arn:aws:events:eu-west-1:701055077130:rule/bedrock-individual-daily-reset"
        ],
        "detail": {}
    }
    
    # Manual test event
    manual_test_event = {
        "source": "manual",
        "action": "daily_reset",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "bedrock-daily-reset"
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = "arn:aws:lambda:eu-west-1:701055077130:function:bedrock-daily-reset"
    
    # Test the handler
    print("Testing daily reset operation:")
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
