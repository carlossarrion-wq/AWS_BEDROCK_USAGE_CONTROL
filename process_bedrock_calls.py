import json
import boto3
import time
import re
import os

logs_client = boto3.client('logs')
iam_client = boto3.client('iam')

USER_LOG_GROUP = '/aws/bedrock/user_usage'
TEAM_LOG_GROUP = '/aws/bedrock/team_usage'

# Load quota configuration to get user-team mappings
QUOTA_CONFIG_FILE = 'quota_config.json'

# Define the teams we're tracking
TEAMS = [
    'team_darwin_group',
    'team_sap_group',
    'team_mulesoft_group',
    'team_yo_leo_gas_group'
]

# Default tool for API key access
DEFAULT_TOOL = 'Cline Agent'

def load_quota_config():
    """
    Load the quota configuration from the JSON file.
    """
    try:
        with open(QUOTA_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading quota configuration: {str(e)}")
        return {"users": {}, "teams": {}}

# Load user-team mappings from quota config
quota_config = load_quota_config()
USER_TEAM_MAP = {}
for user, user_config in quota_config.get('users', {}).items():
    if 'team' in user_config:
        USER_TEAM_MAP[user] = user_config['team']
    # For backward compatibility with team_darwin_usr_001
    elif user == 'team_darwin_usr_001':
        USER_TEAM_MAP[user] = 'team_darwin_group'

def lambda_handler(event, context):
    print(f"Processing event: {json.dumps(event)}")
    
    # Check if this is a Bedrock API call
    if 'detail' not in event or event['detail'].get('eventSource') != 'bedrock.amazonaws.com':
        print("Not a Bedrock API call, ignoring")
        return
    
    # Extract the user identity
    user_identity = event['detail']['userIdentity']
    user_name = extract_user_name(user_identity)
    
    # Skip if we couldn't determine the user
    if not user_name:
        print("Could not determine user name, ignoring")
        return
    
    # Determine the team for this user
    team_name = get_team_for_user(user_name)
    if not team_name:
        print(f"User {user_name} is not associated with any tracked team, ignoring")
        return
    
    # Determine access method (API key or console)
    access_method = determine_access_method(user_identity)
    
    # For API key access, use the default tool or try to determine from user name
    if access_method == "APIKey":
        tool_name = determine_tool_for_user(user_name)
    else:
        tool_name = "AWSConsole"
    
    # Create the log entry
    log_event = {
        'user': user_name,
        'team': team_name,
        'accessMethod': access_method,
        'tool': tool_name,
        'eventName': event['detail']['eventName'],
        'eventTime': event['detail']['eventTime'],
        'awsRegion': event['detail']['awsRegion'],
        'sourceIPAddress': event['detail']['sourceIPAddress']
    }
    
    # Log to user-level log group
    log_to_cloudwatch(USER_LOG_GROUP, user_name, log_event)
    
    # Also log to team-level log group
    log_to_cloudwatch(TEAM_LOG_GROUP, team_name, log_event)
    
    print(f"Successfully logged Bedrock usage for {user_name} in team {team_name}")

def get_team_for_user(user_name):
    """
    Determine which team a user belongs to.
    """
    # Check if we have a direct mapping in the config
    if user_name in USER_TEAM_MAP:
        return USER_TEAM_MAP[user_name]
    
    # Try to determine team from user name prefix
    for team in TEAMS:
        team_prefix = team.split('_')[1]  # Extract 'darwin' from 'team_darwin_group'
        if user_name.startswith(team_prefix):
            return team
    
    # Default for backward compatibility
    if user_name == 'team_darwin_usr_001':
        return 'team_darwin_group'
    
    return None

def determine_tool_for_user(user_name):
    """
    Determine which tool a user is likely using based on their name or configuration.
    Since tools section has been removed, always return the default tool.
    """
    # Always return the default tool since tools configuration has been removed
    return DEFAULT_TOOL

def extract_user_name(user_identity):
    # Direct IAM user access
    if user_identity.get('type') == 'IAMUser':
        return user_identity.get('userName', '')
    
    # Role assumption
    if user_identity.get('type') == 'AssumedRole' and 'sessionContext' in user_identity:
        role_session = user_identity['sessionContext'].get('sessionIssuer', {})
        if role_session.get('type') == 'Role':
            # For assumed roles, we need to extract the user from the role session name
            principal_id = user_identity.get('principalId', '')
            if ':' in principal_id:
                session_name = principal_id.split(':')[1]
                # Accept session names that start with "team_" (original behavior)
                if session_name.startswith('team_'):
                    return session_name
                # Also accept session names that match users in our quota config
                if session_name in quota_config.get('users', {}):
                    return session_name
                # Also accept session names that match our team prefixes
                for team in TEAMS:
                    team_prefix = team.split('_')[1]  # Extract 'darwin' from 'team_darwin_group'
                    if session_name.startswith(team_prefix):
                        return session_name
    
    # Federated user (session token)
    if user_identity.get('type') == 'FederatedUser' and 'sessionContext' in user_identity:
        # Extract the user from the principalId, similar to assumed roles
        principal_id = user_identity.get('principalId', '')
        if ':' in principal_id:
            session_name = principal_id.split(':')[1]
            # Check if this session name is a known user in our quota config
            if session_name in quota_config.get('users', {}):
                return session_name
            # Check if this session name matches our team prefixes
            for team in TEAMS:
                team_prefix = team.split('_')[1]  # Extract 'darwin' from 'team_darwin_group'
                if session_name.startswith(team_prefix):
                    return session_name
            # If the session name is in the ARN, it's likely the user
            arn = user_identity.get('arn', '')
            if f"federated-user/{session_name}" in arn:
                return session_name
    
    # If we can't determine the user, return None
    return None

def determine_access_method(user_identity):
    # Check if this is API key access
    if user_identity.get('type') == 'IAMUser' and 'sessionContext' not in user_identity:
        return "APIKey"
    
    # Check if this is console access
    elif user_identity.get('type') == 'IAMUser' and 'sessionContext' in user_identity:
        return "Console"
    
    # Check if this is role-based access
    elif user_identity.get('type') == 'AssumedRole':
        return "AssumedRole"
    
    # Check if this is federated user (session token)
    elif user_identity.get('type') == 'FederatedUser':
        return "SessionToken"
    
    # Default
    return "Unknown"

def log_to_cloudwatch(log_group, stream_name, log_data):
    try:
        # Ensure log stream exists
        try:
            logs_client.create_log_stream(
                logGroupName=log_group,
                logStreamName=stream_name
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Add the log to CloudWatch
        logs_client.put_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            logEvents=[{
                'timestamp': int(time.time() * 1000),
                'message': json.dumps(log_data)
            }]
        )
    except Exception as e:
        print(f"Error logging to CloudWatch: {str(e)}")
