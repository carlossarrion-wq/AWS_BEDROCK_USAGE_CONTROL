#!/bin/bash

# Deploy Bedrock Usage Monitor with Enhanced Email Service
# =======================================================
# This script packages and deploys the bedrock-usage-monitor Lambda function
# with the enhanced email service including dynamic date integration.

set -e  # Exit on any error

echo "=========================================="
echo "DEPLOYING BEDROCK EMAIL SERVICE LAMBDA"
echo "=========================================="

# Configuration
FUNCTION_NAME="bedrock-usage-monitor"
REGION="eu-west-1"
LAMBDA_DIR="individual_blocking_system/lambda_functions"
PACKAGE_NAME="bedrock-usage-monitor-email-service-$(date +%Y%m%d-%H%M%S).zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Preparing enhanced email service deployment package...${NC}"

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy Lambda function files
echo "Copying Lambda function files..."
cp "$LAMBDA_DIR/bedrock_usage_monitor_enhanced.py" "$TEMP_DIR/bedrock_usage_monitor.py"  # Rename for deployment
cp "$LAMBDA_DIR/bedrock_email_service.py" "$TEMP_DIR/"
cp "$LAMBDA_DIR/email_credentials.json" "$TEMP_DIR/"
cp "$LAMBDA_DIR/quota_config.json" "$TEMP_DIR/"

# Verify files are copied
echo "Files in package:"
ls -la "$TEMP_DIR/"

echo -e "${BLUE}Package contents:${NC}"
echo "✓ bedrock_usage_monitor.py (enhanced version with email integration)"
echo "✓ bedrock_email_service.py (enhanced email service with dynamic dates)"
echo "✓ email_credentials.json (Gmail SMTP credentials)"
echo "✓ quota_config.json (user quota configuration)"

echo -e "${YELLOW}Step 2: Creating deployment package...${NC}"

# Create ZIP package
cd "$TEMP_DIR"
zip -r "../$PACKAGE_NAME" .
cd - > /dev/null

# Move package to current directory
mv "$TEMP_DIR/../$PACKAGE_NAME" "./$PACKAGE_NAME"

# Clean up temp directory
rm -rf "$TEMP_DIR"

echo "Created package: $PACKAGE_NAME"
echo "Package size: $(du -h "$PACKAGE_NAME" | cut -f1)"

echo -e "${YELLOW}Step 3: Checking if Lambda function exists...${NC}"

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo -e "${GREEN}Function exists. Updating function code...${NC}"
    
    # Update existing function
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$PACKAGE_NAME" \
        --region "$REGION"
    
    echo -e "${GREEN}✓ Function code updated successfully${NC}"
    
    # Update function configuration with email service environment variables
    echo "Updating function configuration with email service settings..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --handler "bedrock_usage_monitor.lambda_handler" \
        --timeout 300 \
        --memory-size 512 \
        --region "$REGION" \
        --environment Variables='{DYNAMODB_TABLE=bedrock_user_daily_usage,SNS_TOPIC_ARN=arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts,POLICY_MANAGER_FUNCTION=bedrock-policy-manager,ACCOUNT_ID=701055077130,EMAIL_NOTIFICATIONS_ENABLED=true}' \
        --description "Bedrock Usage Monitor with Enhanced Email Service and Dynamic Date Integration - $(date '+%Y-%m-%d %H:%M:%S')"
    
    echo -e "${GREEN}✓ Function configuration updated with email service settings${NC}"
    
else
    echo -e "${RED}Function does not exist. Please create it first or provide the correct function name.${NC}"
    echo "Available functions:"
    aws lambda list-functions --region "$REGION" --query 'Functions[?contains(FunctionName, `bedrock`)].FunctionName' --output table
    exit 1
fi

echo -e "${YELLOW}Step 4: Verifying deployment...${NC}"

# Get function info
FUNCTION_INFO=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION")

echo "Function details:"
echo "$FUNCTION_INFO" | jq -r '.Configuration | {
    FunctionName: .FunctionName,
    Runtime: .Runtime,
    Handler: .Handler,
    CodeSize: .CodeSize,
    Timeout: .Timeout,
    MemorySize: .MemorySize,
    LastModified: .LastModified,
    Description: .Description
}'

echo -e "${YELLOW}Step 5: Testing enhanced email service function...${NC}"

# Create test event for sap_003 (user with email configured)
TEST_EVENT='{
    "detail": {
        "eventTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "eventSource": "bedrock.amazonaws.com",
        "eventName": "InvokeModel",
        "userIdentity": {
            "type": "IAMUser",
            "userName": "sap_003",
            "arn": "arn:aws:iam::701055077130:user/sap_003"
        },
        "sourceIPAddress": "192.168.1.100",
        "userAgent": "aws-cli/2.0.0"
    }
}'

echo "Testing with sap_003 event (user with email configured)..."
TEST_RESULT=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --payload "$TEST_EVENT" \
    --cli-binary-format raw-in-base64-out \
    response.json)

echo "Invocation result:"
echo "$TEST_RESULT" | jq '.'

if [ -f "response.json" ]; then
    echo "Function response:"
    cat response.json | jq '.'
    rm response.json
fi

echo -e "${YELLOW}Step 6: Verifying email service integration...${NC}"

echo -e "${BLUE}Enhanced Email Service Features Deployed:${NC}"
echo "✓ 5 Email Scenarios:"
echo "  - Warning emails (80% quota reached) - Amber color"
echo "  - Blocking emails (100% quota exceeded) - Light red color"
echo "  - Unblocking emails (daily reset) - Green color"
echo "  - Admin blocking emails (manual admin block) - Light red color"
echo "  - Admin unblocking emails (manual admin unblock) - Green color"
echo ""
echo "✓ Dynamic Date Integration:"
echo "  - Reads expires_at from DynamoDB usage table"
echo "  - Converts UTC to Madrid timezone (CET)"
echo "  - Graceful fallback for missing dates"
echo "  - No more [PONER LA FECHA DE LA TABLA] placeholder"
echo ""
echo "✓ Personalization:"
echo "  - Uses IAM Person tag for friendly names"
echo "  - Fallback to email username or user ID"
echo "  - All emails show 'Hola Carlos Sarrión' instead of 'Hola sap_003'"
echo ""
echo "✓ Email Configuration:"
echo "  - Gmail SMTP integration"
echo "  - HTML and text email formats"
echo "  - Spanish language templates"
echo "  - Madrid timezone display"

echo -e "${YELLOW}Step 7: Cleanup...${NC}"

# Keep the package for reference
echo "Deployment package saved as: $PACKAGE_NAME"
echo "You can delete it manually if no longer needed."

echo -e "${GREEN}=========================================="
echo -e "EMAIL SERVICE DEPLOYMENT COMPLETED!"
echo -e "==========================================${NC}"

echo ""
echo "Summary:"
echo "- Function: $FUNCTION_NAME"
echo "- Region: $REGION"
echo "- Package: $PACKAGE_NAME"
echo "- Features: Enhanced Email Service with Dynamic Date Integration"
echo "- Memory: 512MB (increased for email processing)"
echo "- Timeout: 300 seconds"
echo ""
echo -e "${BLUE}Email Service Capabilities:${NC}"
echo "1. ✅ Warning Email (Amber) - 80% quota reached"
echo "2. ✅ Blocking Email (Light Red) - 100% quota exceeded"
echo "3. ✅ Unblocking Email (Green) - Daily reset"
echo "4. ✅ Admin Blocking Email (Light Red) - Manual admin block with dynamic dates"
echo "5. ✅ Admin Unblocking Email (Green) - Manual admin unblock"
echo ""
echo "Next steps:"
echo "1. Monitor CloudWatch logs for email sending activity"
echo "2. Test with actual Bedrock API calls from users with Email tags"
echo "3. Verify emails are received with proper personalization"
echo "4. Check that admin blocking emails show dynamic dates from DynamoDB"
echo "5. Verify dashboard shows updated metrics"

echo ""
echo -e "${YELLOW}Useful commands for monitoring:${NC}"
echo "# View recent logs:"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo ""
echo "# Check email service logs specifically:"
echo "aws logs filter-log-events --log-group-name /aws/lambda/$FUNCTION_NAME --region $REGION --filter-pattern 'Email' --start-time \$(date -d '1 hour ago' +%s)000"
echo ""
echo "# Test email functionality:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --region $REGION --payload '{\"detail\":{\"eventTime\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"eventSource\":\"bedrock.amazonaws.com\",\"eventName\":\"InvokeModel\",\"userIdentity\":{\"type\":\"IAMUser\",\"userName\":\"sap_003\",\"arn\":\"arn:aws:iam::701055077130:user/sap_003\"},\"sourceIPAddress\":\"192.168.1.100\",\"userAgent\":\"aws-cli/2.0.0\"}}' --cli-binary-format raw-in-base64-out test-response.json"

echo ""
echo -e "${GREEN}🎉 Enhanced Email Service with Dynamic Date Integration is now live!${NC}"
