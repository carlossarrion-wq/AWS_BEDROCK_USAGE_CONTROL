#!/usr/bin/env python3
"""
Compare lcorp_001 vs sap_003 to identify why one works and the other doesn't
"""

import boto3
import json
from datetime import datetime, date

def compare_users():
    """Compare lcorp_001 vs sap_003 data"""
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='eu-west-1')
    iam = boto3.client('iam', region_name='eu-west-1')
    
    users_to_compare = ['lcorp_001', 'sap_003']
    today = date.today().isoformat()
    
    print("COMPARING USERS: lcorp_001 vs sap_003")
    print("=" * 60)
    
    for user_id in users_to_compare:
        print(f"\n🔍 ANALYZING USER: {user_id}")
        print("-" * 40)
        
        # 1. Check DynamoDB data
        print("1. DynamoDB Data:")
        try:
            table = dynamodb.Table('bedrock_user_daily_usage')
            response = table.get_item(
                Key={'user_id': user_id, 'date': today}
            )
            
            if 'Item' in response:
                item = response['Item']
                print(f"   ✅ Request count: {item.get('request_count', 0)}")
                print(f"   ✅ Daily limit: {item.get('daily_limit', 'N/A')}")
                print(f"   ✅ Status: {item.get('status', 'N/A')}")
                print(f"   ✅ Team: {item.get('team', 'N/A')}")
                print(f"   ✅ Last request: {item.get('last_request_time', 'N/A')}")
            else:
                print(f"   ❌ No DynamoDB record found")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # 2. Check CloudWatch metrics
        print("2. CloudWatch Metrics:")
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
                print(f"   ✅ Total requests this month: {total}")
                print(f"   ✅ Number of data points: {len(response['Datapoints'])}")
                
                # Show recent datapoints
                sorted_datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
                for i, dp in enumerate(sorted_datapoints[:3]):  # Show last 3 days
                    print(f"   ✅ {dp['Timestamp'].strftime('%Y-%m-%d')}: {dp['Sum']} requests")
            else:
                print(f"   ❌ No CloudWatch metrics found")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # 3. Check IAM group membership
        print("3. IAM Group Membership:")
        try:
            # Check if user exists
            try:
                iam.get_user(UserName=user_id)
                print(f"   ✅ User exists in IAM")
            except iam.exceptions.NoSuchEntityException:
                print(f"   ❌ User does not exist in IAM")
                continue
            
            # Check group memberships
            response = iam.list_groups_for_user(UserName=user_id)
            groups = [group['GroupName'] for group in response['Groups']]
            
            if groups:
                print(f"   ✅ Member of groups: {', '.join(groups)}")
            else:
                print(f"   ❌ Not member of any groups")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # 4. Check IAM tags
        print("4. IAM User Tags:")
        try:
            response = iam.list_user_tags(UserName=user_id)
            tags = {tag['Key']: tag['Value'] for tag in response['Tags']}
            
            if tags:
                for key, value in tags.items():
                    print(f"   ✅ {key}: {value}")
            else:
                print(f"   ❌ No tags found")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # 5. Test dashboard team discovery
        print("5. Dashboard Team Discovery:")
        try:
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
                        print(f"   ✅ Found in team: {team}")
                        
                except Exception as e:
                    print(f"   ❌ Error checking team {team}: {str(e)}")
            
            if not found_in_teams:
                print(f"   ❌ NOT found in any team - DASHBOARD ISSUE!")
            else:
                print(f"   ✅ Dashboard should find user in: {', '.join(found_in_teams)}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # 6. Compare CloudWatch vs DynamoDB data discrepancy
    print(f"\n🔍 DATA DISCREPANCY ANALYSIS")
    print("-" * 40)
    
    for user_id in users_to_compare:
        try:
            # Get DynamoDB data
            table = dynamodb.Table('bedrock_user_daily_usage')
            dynamo_response = table.get_item(
                Key={'user_id': user_id, 'date': today}
            )
            dynamo_count = 0
            if 'Item' in dynamo_response:
                dynamo_count = dynamo_response['Item'].get('request_count', 0)
            
            # Get CloudWatch data
            end_time = datetime.utcnow()
            start_time = datetime(end_time.year, end_time.month, 1)
            
            cw_response = cloudwatch.get_metric_statistics(
                Namespace='UserMetrics',
                MetricName='BedrockUsage',
                Dimensions=[{'Name': 'User', 'Value': user_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            cw_total = 0
            if cw_response['Datapoints']:
                cw_total = sum(dp['Sum'] for dp in cw_response['Datapoints'])
            
            print(f"{user_id}:")
            print(f"   DynamoDB (today): {dynamo_count}")
            print(f"   CloudWatch (month): {cw_total}")
            
            if dynamo_count > 0 and cw_total == 0:
                print(f"   ⚠️  ISSUE: DynamoDB has data but CloudWatch doesn't!")
            elif dynamo_count > cw_total * 10:  # Significant discrepancy
                print(f"   ⚠️  ISSUE: Major discrepancy between DynamoDB and CloudWatch")
            else:
                print(f"   ✅ Data looks consistent")
                
        except Exception as e:
            print(f"   ❌ Error comparing {user_id}: {str(e)}")

if __name__ == "__main__":
    compare_users()
