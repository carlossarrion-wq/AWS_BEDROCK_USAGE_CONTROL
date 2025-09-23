#!/bin/bash

# Manual Deployment Script for Bedrock Realtime Usage Controller
# This script deploys the fixed Lambda function with manual blocking capabilities

set -e  # Exit on any error

echo "🚀 Manual Deployment: Bedrock Realtime Usage Controller"
echo "======================================================"

# Configuration
FUNCTION_NAME="bedrock-realtime-usage-controller"
REGION="eu-west-1"
ACCOUNT_ID="701055077130"
ROLE_NAME="bedrock-realtime-usage-controller-role"

# File paths
LAMBDA_FILE="02. Source/Lambda Functions/bedrock-realtime-usage-controller.py"
PYMYSQL_DIR="02. Source/Lambda Functions/pymysql"
PYTZ_DIR="02. Source/Lambda Functions/pytz"
EMAIL_CREDS="02. Source/Configuration/email_credentials.json"

# Environment variables for the Lambda function
RDS_ENDPOINT="bedrock-usage-mysql.czuimyk2qu10.eu-west-1.rds.amazonaws.com"
RDS_USERNAME="admin"
RDS_DATABASE="bedrock_usage"
EMAIL_SERVICE_LAMBDA_NAME="bedrock-email-service"
SNS_TOPIC_ARN="arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts"
EMAIL_NOTIFICATIONS_ENABLED="true"

echo "📋 Configuration:"
echo "  Function Name: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  Account ID: $ACCOUNT_ID"
echo "  RDS Endpoint: $RDS_ENDPOINT"
echo ""

# Step 1: Verify files exist
echo "🔍 Step 1: Verifying required files..."
if [ ! -f "$LAMBDA_FILE" ]; then
    echo "❌ Error: Lambda function file not found: $LAMBDA_FILE"
    exit 1
fi

if [ ! -d "$PYMYSQL_DIR" ]; then
    echo "❌ Error: PyMySQL directory not found: $PYMYSQL_DIR"
    exit 1
fi

if [ ! -d "$PYTZ_DIR" ]; then
    echo "❌ Error: pytz directory not found: $PYTZ_DIR"
    exit 1
fi

if [ ! -f "$EMAIL_CREDS" ]; then
    echo "❌ Error: Email credentials file not found: $EMAIL_CREDS"
    exit 1
fi

echo "✅ All required files found"

# Step 2: Create deployment package
echo ""
echo "📦 Step 2: Creating deployment package..."
TEMP_DIR="lambda_deployment_temp"
ZIP_FILE="bedrock-realtime-usage-controller-fixed.zip"

# Clean up any existing temp directory
rm -rf "$TEMP_DIR"
mkdir "$TEMP_DIR"

# Copy Lambda function as lambda_function.py
cp "$LAMBDA_FILE" "$TEMP_DIR/lambda_function.py"
echo "✅ Copied Lambda function"

# Copy dependencies
cp -r "$PYMYSQL_DIR" "$TEMP_DIR/"
cp -r "$PYTZ_DIR" "$TEMP_DIR/"
echo "✅ Copied Python dependencies (pymysql, pytz)"

# Copy configuration files
cp "$EMAIL_CREDS" "$TEMP_DIR/"
echo "✅ Copied email credentials"

# Create ZIP package
cd "$TEMP_DIR"
zip -r "../$ZIP_FILE" . -q
cd ..

echo "✅ Created deployment package: $ZIP_FILE"

# Step 3: Check/Create IAM Role
echo ""
echo "🔐 Step 3: Setting up IAM Role..."
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    echo "✅ IAM role already exists: $ROLE_NAME"
else
    echo "🆕 Creating IAM role: $ROLE_NAME"
    
    # Create trust policy
    cat > trust-policy.json << EOF
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
    
    # Create the role
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://trust-policy.json
    
    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Create comprehensive policy for the function
    cat > lambda-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ListUserTags",
                "iam:GetUser",
                "iam:GetGroupsForUser",
                "iam:GetUserPolicy",
                "iam:PutUserPolicy",
                "iam:DeleteUserPolicy",
                "iam:ListAttachedUserPolicies"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-email-service"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": "$SNS_TOPIC_ARN"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
EOF
    
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "BedrockRealtimeUsageControllerPolicy" \
        --policy-document file://lambda-policy.json
    
    # Clean up policy files
    rm -f trust-policy.json lambda-policy.json
    
    echo "✅ Created IAM role with necessary permissions"
    echo "⏳ Waiting for role to propagate..."
    sleep 15
fi

# Step 4: Deploy Lambda Function
echo ""
echo "☁️ Step 4: Deploying Lambda Function..."

# Prompt for RDS password
echo "🔐 Please enter the RDS password for user '$RDS_USERNAME':"
read -s RDS_PASSWORD

if [ -z "$RDS_PASSWORD" ]; then
    echo "❌ Error: RDS password cannot be empty"
    exit 1
fi

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "🔄 Updating existing Lambda function..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION"
    
    echo "✅ Updated function code"
    
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout 60 \
        --memory-size 512 \
        --runtime python3.9 \
        --environment Variables="{\"RDS_ENDPOINT\":\"$RDS_ENDPOINT\",\"RDS_USERNAME\":\"$RDS_USERNAME\",\"RDS_PASSWORD\":\"$RDS_PASSWORD\",\"RDS_DATABASE\":\"$RDS_DATABASE\",\"EMAIL_SERVICE_LAMBDA_NAME\":\"$EMAIL_SERVICE_LAMBDA_NAME\",\"SNS_TOPIC_ARN\":\"$SNS_TOPIC_ARN\",\"EMAIL_NOTIFICATIONS_ENABLED\":\"$EMAIL_NOTIFICATIONS_ENABLED\"}" \
        --region "$REGION"
    
    echo "✅ Updated function configuration"
    
else
    echo "🆕 Creating new Lambda function..."
    
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler lambda_function.lambda_handler \
        --zip-file "fileb://$ZIP_FILE" \
        --timeout 60 \
        --memory-size 512 \
        --environment Variables="{\"RDS_ENDPOINT\":\"$RDS_ENDPOINT\",\"RDS_USERNAME\":\"$RDS_USERNAME\",\"RDS_PASSWORD\":\"$RDS_PASSWORD\",\"RDS_DATABASE\":\"$RDS_DATABASE\",\"EMAIL_SERVICE_LAMBDA_NAME\":\"$EMAIL_SERVICE_LAMBDA_NAME\",\"SNS_TOPIC_ARN\":\"$SNS_TOPIC_ARN\",\"EMAIL_NOTIFICATIONS_ENABLED\":\"$EMAIL_NOTIFICATIONS_ENABLED\"}" \
        --region "$REGION"
    
    echo "✅ Created new Lambda function"
fi

# Step 5: Test the deployment
echo ""
echo "🧪 Step 5: Testing the deployment..."

# Test with a simple status check
TEST_PAYLOAD='{"action": "check_status", "user_id": "sap_003"}'

echo "📤 Testing with payload: $TEST_PAYLOAD"

RESPONSE=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "$TEST_PAYLOAD" \
    --region "$REGION" \
    response.json)

if [ $? -eq 0 ]; then
    echo "✅ Lambda function invoked successfully"
    echo "📥 Response:"
    cat response.json | python3 -m json.tool
    rm -f response.json
else
    echo "❌ Lambda function invocation failed"
fi

# Step 6: Clean up
echo ""
echo "🧹 Step 6: Cleaning up temporary files..."
rm -rf "$TEMP_DIR"
rm -f "$ZIP_FILE"
echo "✅ Cleanup completed"

# Step 7: Summary
echo ""
echo "🎉 Deployment Summary"
echo "===================="
echo "✅ Function Name: $FUNCTION_NAME"
echo "✅ Region: $REGION"
echo "✅ Runtime: python3.9"
echo "✅ Memory: 512 MB"
echo "✅ Timeout: 60 seconds"
echo "✅ IAM Role: $ROLE_ARN"
echo ""
echo "🔧 Key Features Deployed:"
echo "  ✅ Fixed IAM policy blocking logic"
echo "  ✅ Manual blocking/unblocking via API events"
echo "  ✅ CloudTrail event processing for automatic blocking"
echo "  ✅ Enhanced logging and debugging"
echo "  ✅ Database schema compatibility fixes"
echo "  ✅ CET timezone support"
echo ""
echo "📋 Next Steps:"
echo "1. Test manual blocking from the dashboard"
echo "2. Verify CloudTrail integration is working"
echo "3. Check CloudWatch logs for any issues"
echo "4. Update any CloudWatch Events/EventBridge rules if needed"
echo ""
echo "🔍 Function ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
echo ""
echo "✅ Manual deployment completed successfully!"
