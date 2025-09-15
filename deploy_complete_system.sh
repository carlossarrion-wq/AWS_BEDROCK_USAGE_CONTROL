#!/bin/bash

# =============================================================================
# AWS Bedrock Individual Blocking System - Complete Deployment
# =============================================================================
# This script deploys the complete system with administrative protection logic:
# 1. Infrastructure setup (if needed)
# 2. Lambda functions deployment with updated code
# 3. Additional DynamoDB table for blocking history
# 4. Updated IAM permissions for administrative protection
# 5. System verification and testing
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="eu-west-1"
ACCOUNT_ID="701055077130"
TABLE_NAME="bedrock_user_daily_usage"
HISTORY_TABLE_NAME="bedrock_blocking_history"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}AWS Bedrock Individual Blocking System - Complete Deployment${NC}"
echo -e "${BLUE}With Administrative Protection Logic${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    print_error "AWS credentials not configured or invalid."
    exit 1
fi

# Check if we're in the right directory
if [ ! -d "individual_blocking_system" ]; then
    print_error "individual_blocking_system directory not found. Please run from project root."
    exit 1
fi

CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text --region $REGION)
if [ "$CURRENT_ACCOUNT" != "$ACCOUNT_ID" ]; then
    print_warning "Current AWS account ($CURRENT_ACCOUNT) differs from expected ($ACCOUNT_ID)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Prerequisites check completed successfully"
echo ""

# =============================================================================
# STEP 1: Setup Infrastructure (if needed)
# =============================================================================
echo -e "${BLUE}STEP 1: Setting up Infrastructure${NC}"
echo "-----------------------------------"

cd individual_blocking_system

# Check if infrastructure exists
if [ ! -f "blocking_system_config.json" ]; then
    print_status "Infrastructure not found. Running setup_infrastructure.sh..."
    if [ -f "setup_infrastructure.sh" ]; then
        chmod +x setup_infrastructure.sh
        ./setup_infrastructure.sh
    else
        print_error "setup_infrastructure.sh not found!"
        exit 1
    fi
else
    print_status "Infrastructure configuration found. Skipping infrastructure setup."
fi

# =============================================================================
# STEP 2: Create Blocking History Table
# =============================================================================
echo ""
echo -e "${BLUE}STEP 2: Creating Blocking History Table${NC}"
echo "---------------------------------------"

print_status "Creating DynamoDB table for blocking history: $HISTORY_TABLE_NAME"

# Check if history table already exists
if aws dynamodb describe-table --table-name $HISTORY_TABLE_NAME --region $REGION > /dev/null 2>&1; then
    print_warning "Table $HISTORY_TABLE_NAME already exists. Skipping creation."
else
    # Create the history table
    aws dynamodb create-table \
        --table-name $HISTORY_TABLE_NAME \
        --attribute-definitions \
            AttributeName=operation_id,AttributeType=S \
            AttributeName=timestamp,AttributeType=S \
            AttributeName=user_id,AttributeType=S \
            AttributeName=date,AttributeType=S \
        --key-schema \
            AttributeName=operation_id,KeyType=HASH \
            AttributeName=timestamp,KeyType=RANGE \
        --global-secondary-indexes \
            'IndexName=user-date-index,KeySchema=[{AttributeName=user_id,KeyType=HASH},{AttributeName=date,KeyType=RANGE}],Projection={ProjectionType=ALL}' \
        --billing-mode PAY_PER_REQUEST \
        --region $REGION

    print_status "Waiting for history table to become active..."
    aws dynamodb wait table-exists --table-name $HISTORY_TABLE_NAME --region $REGION
    print_status "Table $HISTORY_TABLE_NAME created successfully!"
    
    # Configure TTL for history table (30 days retention)
    print_status "Configuring TTL for history table (30 days retention)..."
    aws dynamodb update-time-to-live \
        --table-name $HISTORY_TABLE_NAME \
        --time-to-live-specification \
            Enabled=true,AttributeName=ttl \
        --region $REGION
    
    print_status "TTL configured for history table!"
fi

# =============================================================================
# STEP 3: Update IAM Roles with Additional Permissions
# =============================================================================
echo ""
echo -e "${BLUE}STEP 3: Updating IAM Roles with Additional Permissions${NC}"
echo "-------------------------------------------------------"

# Update bedrock-usage-monitor role for history table access
ROLE_NAME_MONITOR="bedrock-usage-monitor-role"
print_status "Updating IAM role: $ROLE_NAME_MONITOR with history table permissions..."

cat > /tmp/monitor-policy-updated.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:$REGION:$ACCOUNT_ID:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem",
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$TABLE_NAME"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$HISTORY_TABLE_NAME/index/user-date-index"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-policy-manager"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:$REGION:$ACCOUNT_ID:bedrock-usage-alerts"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListUserTags",
        "iam:GetUser"
      ],
      "Resource": "arn:aws:iam::$ACCOUNT_ID:user/*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $ROLE_NAME_MONITOR \
    --policy-name "BedrockUsageMonitorPolicy" \
    --policy-document file:///tmp/monitor-policy-updated.json

print_status "Updated permissions for $ROLE_NAME_MONITOR"

# Update bedrock-policy-manager role for history table access
ROLE_NAME_POLICY="bedrock-policy-manager-role"
print_status "Updating IAM role: $ROLE_NAME_POLICY with history table permissions..."

cat > /tmp/policy-manager-policy-updated.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:$REGION:$ACCOUNT_ID:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetUserPolicy",
        "iam:PutUserPolicy",
        "iam:ListUserPolicies"
      ],
      "Resource": "arn:aws:iam::$ACCOUNT_ID:user/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$TABLE_NAME"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-blocking-history"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:$REGION:$ACCOUNT_ID:bedrock-usage-alerts"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $ROLE_NAME_POLICY \
    --policy-name "BedrockPolicyManagerPolicy" \
    --policy-document file:///tmp/policy-manager-policy-updated.json

print_status "Updated permissions for $ROLE_NAME_POLICY"

# Create IAM role for bedrock-blocking-history
ROLE_NAME_HISTORY="bedrock-blocking-history-role"
print_status "Creating IAM role: $ROLE_NAME_HISTORY"

# Trust policy for Lambda
cat > /tmp/lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

if aws iam get-role --role-name $ROLE_NAME_HISTORY > /dev/null 2>&1; then
    print_warning "Role $ROLE_NAME_HISTORY already exists. Skipping creation."
else
    aws iam create-role \
        --role-name $ROLE_NAME_HISTORY \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
        --description "Role for bedrock-blocking-history Lambda function"
    
    print_status "Role $ROLE_NAME_HISTORY created successfully!"
fi

# Policy for bedrock-blocking-history
cat > /tmp/history-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:$REGION:$ACCOUNT_ID:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$HISTORY_TABLE_NAME",
        "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/$HISTORY_TABLE_NAME/index/user-date-index"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $ROLE_NAME_HISTORY \
    --policy-name "BedrockBlockingHistoryPolicy" \
    --policy-document file:///tmp/history-policy.json

print_status "Policy attached to $ROLE_NAME_HISTORY successfully!"

# Clean up temporary files
rm -f /tmp/monitor-policy-updated.json /tmp/policy-manager-policy-updated.json /tmp/history-policy.json /tmp/lambda-trust-policy.json

# =============================================================================
# STEP 4: Deploy Lambda Functions with Updated Code
# =============================================================================
echo ""
echo -e "${BLUE}STEP 4: Deploying Lambda Functions with Updated Code${NC}"
echo "-----------------------------------------------------"

# Create temp directory for packages
mkdir -p temp_packages
cd temp_packages

# Package 1: bedrock-usage-monitor (with administrative protection)
print_status "Creating package for bedrock-usage-monitor (with admin protection)..."
mkdir -p bedrock-usage-monitor
cp ../lambda_functions/bedrock_usage_monitor.py bedrock-usage-monitor/
cd bedrock-usage-monitor
zip -r ../bedrock-usage-monitor.zip . > /dev/null
cd ..
print_status "Package bedrock-usage-monitor.zip created"

# Package 2: bedrock-policy-manager (with administrative protection)
print_status "Creating package for bedrock-policy-manager (with admin protection)..."
mkdir -p bedrock-policy-manager
cp ../lambda_functions/bedrock_policy_manager.py bedrock-policy-manager/
cd bedrock-policy-manager
zip -r ../bedrock-policy-manager.zip . > /dev/null
cd ..
print_status "Package bedrock-policy-manager.zip created"

# Package 3: bedrock-daily-reset (with admin protection cleanup)
print_status "Creating package for bedrock-daily-reset (with admin protection cleanup)..."
mkdir -p bedrock-daily-reset
cp ../lambda_functions/bedrock_daily_reset.py bedrock-daily-reset/
cd bedrock-daily-reset
zip -r ../bedrock-daily-reset.zip . > /dev/null
cd ..
print_status "Package bedrock-daily-reset.zip created"

# Package 4: bedrock-blocking-history
print_status "Creating package for bedrock-blocking-history..."
mkdir -p bedrock-blocking-history
cp ../lambda_functions/bedrock_blocking_history.py bedrock-blocking-history/
cd bedrock-blocking-history
zip -r ../bedrock-blocking-history.zip . > /dev/null
cd ..
print_status "Package bedrock-blocking-history.zip created"

cd ..

# Deploy all functions
FUNCTIONS=(
    "bedrock-usage-monitor:bedrock-usage-monitor-role:bedrock_usage_monitor.lambda_handler:256:60"
    "bedrock-policy-manager:bedrock-policy-manager-role:bedrock_policy_manager.lambda_handler:256:60"
    "bedrock-daily-reset:bedrock-daily-reset-role:bedrock_daily_reset.lambda_handler:512:300"
    "bedrock-blocking-history:bedrock-blocking-history-role:bedrock_blocking_history.lambda_handler:256:60"
)

for FUNCTION_INFO in "${FUNCTIONS[@]}"; do
    IFS=':' read -r FUNCTION_NAME ROLE_NAME HANDLER MEMORY TIMEOUT <<< "$FUNCTION_INFO"
    ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
    
    print_status "Deploying $FUNCTION_NAME..."
    
    # Check if function exists
    if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
        print_warning "Function $FUNCTION_NAME already exists. Updating code..."
        
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://temp_packages/$FUNCTION_NAME.zip \
            --region $REGION > /dev/null
        
        # Update configuration
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --runtime python3.9 \
            --handler $HANDLER \
            --timeout $TIMEOUT \
            --memory-size $MEMORY \
            --environment Variables="{
                ACCOUNT_ID=$ACCOUNT_ID,
                DYNAMODB_TABLE=$TABLE_NAME,
                HISTORY_TABLE=$HISTORY_TABLE_NAME,
                SNS_TOPIC_ARN=arn:aws:sns:$REGION:$ACCOUNT_ID:bedrock-usage-alerts,
                POLICY_MANAGER_FUNCTION=bedrock-policy-manager
            }" \
            --region $REGION > /dev/null
        
        print_status "Function $FUNCTION_NAME updated successfully"
    else
        print_status "Creating new function $FUNCTION_NAME..."
        
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --runtime python3.9 \
            --role $ROLE_ARN \
            --handler $HANDLER \
            --zip-file fileb://temp_packages/$FUNCTION_NAME.zip \
            --timeout $TIMEOUT \
            --memory-size $MEMORY \
            --environment Variables="{
                ACCOUNT_ID=$ACCOUNT_ID,
                DYNAMODB_TABLE=$TABLE_NAME,
                HISTORY_TABLE=$HISTORY_TABLE_NAME,
                SNS_TOPIC_ARN=arn:aws:sns:$REGION:$ACCOUNT_ID:bedrock-usage-alerts,
                POLICY_MANAGER_FUNCTION=bedrock-policy-manager
            }" \
            --region $REGION > /dev/null
        
        print_status "Function $FUNCTION_NAME created successfully"
    fi
done

# =============================================================================
# STEP 5: Configure Event Triggers
# =============================================================================
echo ""
echo -e "${BLUE}STEP 5: Configuring Event Triggers${NC}"
echo "------------------------------------"

# Configure trigger for bedrock-usage-monitor
RULE_NAME_MONITOR="bedrock-individual-blocking-monitor"
print_status "Configuring trigger for bedrock-usage-monitor..."

# Add permission for EventBridge to invoke the function
aws lambda add-permission \
    --function-name bedrock-usage-monitor \
    --statement-id allow-eventbridge-monitor \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/$RULE_NAME_MONITOR \
    --region $REGION > /dev/null 2>&1 || print_warning "Permission already exists for bedrock-usage-monitor"

# Add target to EventBridge rule
aws events put-targets \
    --rule $RULE_NAME_MONITOR \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-usage-monitor" \
    --region $REGION > /dev/null

print_status "Trigger configured for bedrock-usage-monitor"

# Configure trigger for bedrock-daily-reset
RULE_NAME_RESET="bedrock-individual-daily-reset"
print_status "Configuring trigger for bedrock-daily-reset..."

# Add permission for EventBridge to invoke the function
aws lambda add-permission \
    --function-name bedrock-daily-reset \
    --statement-id allow-eventbridge-reset \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/$RULE_NAME_RESET \
    --region $REGION > /dev/null 2>&1 || print_warning "Permission already exists for bedrock-daily-reset"

# Add target to EventBridge rule
aws events put-targets \
    --rule $RULE_NAME_RESET \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-daily-reset" \
    --region $REGION > /dev/null

print_status "Trigger configured for bedrock-daily-reset"

# =============================================================================
# STEP 6: Cleanup and Verification
# =============================================================================
echo ""
echo -e "${BLUE}STEP 6: Cleanup and Verification${NC}"
echo "----------------------------------"

# Cleanup temporary files
print_status "Cleaning up temporary files..."
rm -rf temp_packages
print_status "Temporary files cleaned up"

# Verify deployments
print_status "Verifying Lambda function deployments..."

# Check each function
FUNCTIONS_TO_CHECK=("bedrock-usage-monitor" "bedrock-policy-manager" "bedrock-daily-reset" "bedrock-blocking-history")
for FUNCTION in "${FUNCTIONS_TO_CHECK[@]}"; do
    if aws lambda get-function --function-name $FUNCTION --region $REGION > /dev/null 2>&1; then
        STATE=$(aws lambda get-function --function-name $FUNCTION --region $REGION --query 'Configuration.State' --output text)
        if [ "$STATE" = "Active" ]; then
            print_status "✅ $FUNCTION is Active"
        else
            print_warning "⚠️  $FUNCTION state: $STATE"
        fi
    else
        print_error "❌ $FUNCTION not found"
    fi
done

# Verify DynamoDB tables
print_status "Verifying DynamoDB tables..."
for TABLE in $TABLE_NAME $HISTORY_TABLE_NAME; do
    if aws dynamodb describe-table --table-name $TABLE --region $REGION > /dev/null 2>&1; then
        STATUS=$(aws dynamodb describe-table --table-name $TABLE --region $REGION --query 'Table.TableStatus' --output text)
        print_status "✅ $TABLE is $STATUS"
    else
        print_error "❌ $TABLE not found"
    fi
done

cd ..

echo ""

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}COMPLETE SYSTEM DEPLOYMENT FINISHED SUCCESSFULLY!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "${GREEN}✅ Deployed Components:${NC}"
echo "   • Infrastructure: DynamoDB tables, IAM roles, CloudWatch Events"
echo "   • Lambda Functions: 4 functions with administrative protection logic"
echo "   • Event Triggers: Configured for monitoring and daily reset"
echo "   • Blocking History: Complete audit trail system"
echo ""
echo -e "${GREEN}✅ New Features Included:${NC}"
echo "   • 🛡️  Administrative Protection: Manual unblocks prevent auto-blocking"
echo "   • 📊 Blocking History: Complete audit trail of all operations"
echo "   • 🔄 Daily Protection Reset: Admin protections cleared each day"
echo "   • 📧 Enhanced Notifications: Admin protection alerts"
echo ""
echo -e "${BLUE}🎯 System Behavior:${NC}"
echo "   • Users exceeding limits are blocked automatically"
echo "   • Admin manual unblocks provide protection until next day"
echo "   • Daily reset at 00:00 UTC clears all protections"
echo "   • Complete history tracking for compliance"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "   1. Test the system: ./test_admin_protection.sh"
echo "   2. Configure dashboard: ../configure_dashboard_aws.sh"
echo "   3. Set up monitoring alerts"
echo "   4. Train administrators on the new protection feature"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "   • System is ACTIVE and will block users exceeding daily limits"
echo "   • Administrative protection prevents re-blocking until next day"
echo "   • Monitor CloudWatch logs for system health"
echo "   • Review blocking history regularly for compliance"
echo ""
echo -e "${GREEN}Deployment completed at: $(date)${NC}"
