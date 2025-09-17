#!/usr/bin/env python3
"""
Test script to diagnose lcorp_001 dashboard visibility issue
"""

import boto3
import json
from datetime import datetime, date

def test_lcorp_001_data():
    """Test if lcorp_001 data exists in DynamoDB and CloudWatch"""
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    iam = boto3.client('iam', region_name='eu-west-1')
    
    user_id = 'lcorp_001'
    today = date.today().isoformat()
    
    print(f"Testing lcorp_001 data visibility for date: {today}")
    print("=" * 60)
    
    # 1. Check DynamoDB data
    print("1. Checking DynamoDB data...")
    try:
        table = dynamodb.Table('bedrock_user_daily_usage')
        response = table.get_item(
            Key={'user_id': user_id, 'date': today}
        )
        
        if 'Item' in response:
            item = response['Item']
            print(f"✅ Found DynamoDB record for {user_id}:")
            print(f"   - Request count: {item.get('request_count', 0)}")
            print(f"   - Daily limit: {item.get('daily_limit', 'N/A')}")
            print(f"   - Status: {item.get('status', 'N/A')}")
            print(f"   - Team: {item.get('team', 'N/A')}")
            print(f"   - Last request: {item.get('last_request_time', 'N/A')}")
        else:
            print(f"❌ No DynamoDB record found for {user_id} on {today}")
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {str(e)}")
    
    # 2. Check CloudWatch metrics
    print("\n2. Checking CloudWatch metrics...")
    try:
        end_time = datetime.utcnow()
        start_time = datetime(end_time.year, end_time.month, 1)  # First day of month
        
        response = cloudwatch.get_metric_statistics(
            Namespace='UserMetrics',
            MetricName='BedrockUsage',
            Dimensions=[
                {
                    'Name': 'User',
                    'Value': user_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            total = sum(dp['Sum'] for dp in response['Datapoints'])
            print(f"✅ Found CloudWatch metrics for {user_id}:")
            print(f"   - Total requests this month: {total}")
            print(f"   - Number of data points: {len(response['Datapoints'])}")
            
            # Show recent datapoints
            sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
            for i, dp in enumerate(sorted_datapoints[:5]):  # Show last 5 days
                print(f"   - {dp['Timestamp'].strftime('%Y-%m-%d')}: {dp['Sum']} requests")
        else:
            print(f"❌ No CloudWatch metrics found for {user_id}")
    except Exception as e:
        print(f"❌ Error checking CloudWatch: {str(e)}")
    
    # 3. Check IAM group membership
    print("\n3. Checking IAM group membership...")
    try:
        # Check if user exists
        try:
            iam.get_user(UserName=user_id)
            print(f"✅ User {user_id} exists in IAM")
        except iam.exceptions.NoSuchEntityException:
            print(f"❌ User {user_id} does not exist in IAM")
            return
        
        # Check group memberships
        response = iam.list_groups_for_user(UserName=user_id)
        groups = [group['GroupName'] for group in response['Groups']]
        
        if groups:
            print(f"✅ User {user_id} is member of groups: {', '.join(groups)}")
            
            # Check if in team_lcorp_group specifically
            if 'team_lcorp_group' in groups:
                print(f"✅ User {user_id} is correctly in team_lcorp_group")
            else:
                print(f"⚠️  User {user_id} is NOT in team_lcorp_group")
        else:
            print(f"❌ User {user_id} is not member of any groups")
            
    except Exception as e:
        print(f"❌ Error checking IAM groups: {str(e)}")
    
    # 4. Check IAM tags
    print("\n4. Checking IAM user tags...")
    try:
        response = iam.list_user_tags(UserName=user_id)
        tags = {tag['Key']: tag['Value'] for tag in response['Tags']}
        
        if tags:
            print(f"✅ User {user_id} has tags:")
            for key, value in tags.items():
                print(f"   - {key}: {value}")
                
            # Check for Person and Team tags specifically
            if 'Person' in tags:
                print(f"✅ Person tag found: {tags['Person']}")
            else:
                print(f"⚠️  No Person tag found")
                
            if 'Team' in tags:
                print(f"✅ Team tag found: {tags['Team']}")
            else:
                print(f"⚠️  No Team tag found")
        else:
            print(f"❌ User {user_id} has no tags")
            
    except Exception as e:
        print(f"❌ Error checking IAM tags: {str(e)}")
    
    # 5. Test dashboard data fetching logic
    print("\n5. Testing dashboard data fetching logic...")
    try:
        # Simulate the dashboard's fetchRealUsersFromIAM function
        all_teams = [
            'team_darwin_group',
            'team_sap_group', 
            'team_mulesoft_group',
            'team_yo_leo_gas_group',
            'team_lcorp_group'
        ]
        
        found_in_teams = []
        for team in all_teams:
            try:
                group_response = iam.get_group(GroupName=team)
                users_in_group = [user['UserName'] for user in group_response['Users']]
                
                if user_id in users_in_group:
                    found_in_teams.append(team)
                    print(f"✅ Found {user_id} in team {team}")
                else:
                    print(f"❌ {user_id} NOT found in team {team}")
                    
            except Exception as e:
                print(f"❌ Error checking team {team}: {str(e)}")
        
        if found_in_teams:
            print(f"✅ Dashboard should find {user_id} in teams: {', '.join(found_in_teams)}")
        else:
            print(f"❌ Dashboard will NOT find {user_id} in any team - THIS IS THE ISSUE!")
            
    except Exception as e:
        print(f"❌ Error testing dashboard logic: {str(e)}")

if __name__ == "__main__":
    test_lcorp_001_data()
