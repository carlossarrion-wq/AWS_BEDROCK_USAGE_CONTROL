#!/usr/bin/env python3
"""
AWS Bedrock Individual Blocking System - Blocking History Lambda
===============================================================

This Lambda function manages the history of blocking operations:
1. Logging blocking/unblocking operations
2. Retrieving operation history
3. Providing audit trail for compliance

Author: AWS Bedrock Usage Control System
Version: 1.0.0
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, List
import uuid
import os
from decimal import Decimal

# Custom JSON encoder for DynamoDB Decimal types
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

# Configuration
REGION = os.environ.get('AWS_REGION', 'eu-west-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '701055077130')
HISTORY_TABLE_NAME = os.environ.get('HISTORY_TABLE', 'bedrock_blocking_operations')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for blocking history management
    
    Args:
        event: Event containing action and parameters
        context: Lambda context object
        
    Returns:
        Dict with status code and results
    """
    try:
        logger.info(f"Processing blocking history event: {json.dumps(event, default=str)}")
        
        action = event.get('action')
        
        if action == 'get_history':
            return get_blocking_history(event.get('limit', 50))
        elif action == 'log_operation':
            return log_blocking_operation(event.get('operation', {}))
        elif action == 'get_user_history':
            return get_user_blocking_history(event.get('user_id'))
        else:
            logger.error(f"Invalid action: {action}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid action: {action}'})
            }
            
    except Exception as e:
        logger.error(f"Error processing blocking history event: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_blocking_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get recent blocking operations history
    
    Args:
        limit: Maximum number of operations to return
        
    Returns:
        Dict with operations list
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Scan table and sort by timestamp (most recent first)
        response = table.scan(
            Limit=limit
        )
        
        operations = response.get('Items', [])
        
        # Sort by timestamp descending
        operations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Take only the requested limit
        operations = operations[:limit]
        
        logger.info(f"Retrieved {len(operations)} blocking operations")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'operations': operations,
                'count': len(operations)
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error getting blocking history: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def log_blocking_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log a blocking operation to the history table
    
    Args:
        operation: Operation details to log
        
    Returns:
        Dict with operation result
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Prepare operation record
        operation_record = {
            'operation_id': operation_id,
            'timestamp': operation.get('timestamp', datetime.utcnow().isoformat()),
            'user_id': operation.get('user_id'),
            'operation': operation.get('operation'),  # 'BLOCK' or 'UNBLOCK'
            'reason': operation.get('reason'),
            'block_type': operation.get('block_type', ''),
            'duration': operation.get('duration', ''),
            'expires_at': operation.get('expires_at', ''),
            'performed_by': operation.get('performed_by'),
            'status': operation.get('status'),  # 'SUCCESS' or 'FAILED'
            'details': operation.get('details', ''),
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 90))  # 90 days TTL
        }
        
        # Store operation
        table.put_item(Item=operation_record)
        
        logger.info(f"Logged blocking operation: {operation_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Operation logged successfully',
                'operation_id': operation_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error logging blocking operation: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_user_blocking_history(user_id: str) -> Dict[str, Any]:
    """
    Get blocking history for a specific user
    
    Args:
        user_id: User ID to get history for
        
    Returns:
        Dict with user's blocking history
    """
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Query operations for specific user
        response = table.scan(
            FilterExpression='user_id = :user_id',
            ExpressionAttributeValues={
                ':user_id': user_id
            }
        )
        
        operations = response.get('Items', [])
        
        # Sort by timestamp descending
        operations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"Retrieved {len(operations)} operations for user {user_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_id,
                'operations': operations,
                'count': len(operations)
            })
        }
        
    except Exception as e:
        logger.error(f"Error getting user blocking history: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

# For testing purposes
if __name__ == "__main__":
    # Test events
    test_log_event = {
        "action": "log_operation",
        "operation": {
            "user_id": "test_user_001",
            "operation": "BLOCK",
            "reason": "daily_limit_exceeded",
            "performed_by": "system",
            "status": "SUCCESS",
            "details": "User exceeded daily limit of 50 requests"
        }
    }
    
    test_get_history_event = {
        "action": "get_history",
        "limit": 10
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = "bedrock-blocking-history"
            self.memory_limit_in_mb = 256
    
    # Test the handlers
    print("Testing log operation:")
    result = lambda_handler(test_log_event, MockContext())
    print(json.dumps(result, indent=2))
    
    print("\nTesting get history:")
    result = lambda_handler(test_get_history_event, MockContext())
    print(json.dumps(result, indent=2))
