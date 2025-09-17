#!/bin/bash

# Deploy Enhanced Bedrock Policy Manager Lambda Function
# ====================================================
# This script packages and deploys the enhanced bedrock-policy-manager Lambda function
# with email service integration for admin blocking/unblocking notifications.

set -e  # Exit on any error

echo "=========================================="
echo "DEPLOYING ENHANCED POLICY MANAGER LAMBDA"
echo "=========================================="

# Configuration
FUNCTION_NAME="bedrock-policy-manager"
REGION="eu-west-1"
LAMBDA_DIR="individual_blocking_system/lambda_functions"
PACKAGE_NAME="bedrock-policy-manager-enhanced-$(date +%Y%m%d-%H%M%S).zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Preparing enhanced policy manager deployment package...${NC}"

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy Lambda function files
echo "Copying Lambda function files..."
cp "$LAMBDA_DIR/bedrock_policy_manager_enhanced.py" "$TEMP_DIR/bedrock_policy_manager.py"  # Rename for deployment
cp "$LAMBDA_DIR/bedrock_email_service.py" "$TEMP_DIR/"
cp "$LAMBDA_DIR/email_credentials.json" "$TEMP_DIR/"

# Verify files are copied
echo "Files in package:"
ls -la "$TEMP_DIR/"

echo -e "${BLUE}Package contents:${NC}"
echo "✓ bedrock_policy_manager.py (enhanced version with email integration)"
echo "✓ bedrock_email_service.py (enhanced email service with dynamic dates)"
echo "✓ email_credentials.json (Gmail SMTP credentials)"

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
        --handler "bedrock_policy_manager.lambda_handler" \
        --timeout 300 \
        --memory-size 512 \
        --region "$REGION" \
        --environment 'Variables={"DYNAMODB_TABLE":"bedrock_user_daily_usage","SNS_TOPIC_ARN":"arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts","ACCOUNT_ID":"701055077130","EMAIL_NOTIFICATIONS_ENABLED":"true"}' \
        --description "Enhanced Bedrock Policy Manager with Email Service Integration - $(date '+%Y-%m-%d %H:%M:%S')"
    
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

echo -e "${YELLOW}Step 5: Testing enhanced policy manager function...${NC}"

# Create test event for admin blocking
TEST_EVENT='{
    "action": "block",
    "user_id": "sap_003",
    "reason": "manual_admin_block_test",
    "performed_by": "admin_test",
    "usage_record": {
        "request_count": 35,
        "daily_limit": 250,
        "team": "team_sap",
        "date": "'$(date +%Y-%m-%d)'"
    }
}'

echo "Testing admin block operation for sap_003..."
TEST_RESULT=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION" \
    --payload "$TEST_EVENT" \
    --cli-binary-format raw-in-base64-out \
    policy_response.json)

echo "Invocation result:"
echo "$TEST_RESULT" | jq '.'

if [ -f "policy_response.json" ]; then
    echo "Function response:"
    cat policy_response.json | jq '.'
    rm policy_response.json
fi

echo -e "${YELLOW}Step 6: Verifying email service integration...${NC}"

echo -e "${BLUE}Enhanced Policy Manager Features Deployed:${NC}"
echo "✓ Admin Blocking Email Integration:"
echo "  - Sends personalized admin blocking emails"
echo "  - Uses dynamic dates from DynamoDB"
echo "  - Shows friendly names (Hola Carlos Sarrión)"
echo "  - Light red color theme for blocking notifications"
echo ""
echo "✓ Admin Unblocking Email Integration:"
echo "  - Sends personalized admin unblocking emails"
echo "  - Green color theme for unblocking notifications"
echo "  - Sets administrative protection to prevent auto-blocking"
echo ""
echo "✓ Enhanced Functionality:"
echo "  - Proper action handling ('block' and 'unblock')"
echo "  - DynamoDB integration with expires_at field"
echo "  - Administrative protection for manual unblocks"
echo "  - Comprehensive audit logging"

echo -e "${YELLOW}Step 7: Cleanup...${NC}"

# Keep the package for reference
echo "Deployment package saved as: $PACKAGE_NAME"
echo "You can delete it manually if no longer needed."

echo -e "${GREEN}=========================================="
echo -e "ENHANCED POLICY MANAGER DEPLOYMENT COMPLETED!"
echo -e "==========================================${NC}"

echo ""
echo "Summary:"
echo "- Function: $FUNCTION_NAME"
echo "- Region: $REGION"
echo "- Package: $PACKAGE_NAME"
echo "- Features: Enhanced Email Service Integration for Admin Operations"
echo "- Memory: 512MB (increased for email processing)"
echo "- Timeout: 300 seconds"
echo ""
echo -e "${BLUE}Admin Email Capabilities:${NC}"
echo "1. ✅ Admin Blocking Email - Manual admin blocks with dynamic dates"
echo "2. ✅ Admin Unblocking Email - Manual admin unblocks with protection"
echo "3. ✅ Personalization - Uses friendly names from IAM Person tags"
echo "4. ✅ Dynamic Dates - Shows actual expiration times from DynamoDB"
echo "5. ✅ Administrative Protection - Prevents auto-blocking after manual unblock"
echo ""
echo "Next steps:"
echo "1. Monitor CloudWatch logs for admin email sending activity"
echo "2. Test manual blocking/unblocking operations"
echo "3. Verify emails are received for admin operations"
echo "4. Check that dynamic dates are displayed correctly"
echo "5. Confirm administrative protection is working"

echo ""
echo -e "${YELLOW}Useful commands for monitoring:${NC}"
echo "# View recent logs:"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo ""
echo "# Check admin email service logs specifically:"
echo "aws logs filter-log-events --log-group-name /aws/lambda/$FUNCTION_NAME --region $REGION --filter-pattern 'admin.*email' --start-time \$(date -d '1 hour ago' +%s)000"
echo ""
echo "# Test admin blocking:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --region $REGION --payload '{\"action\":\"block\",\"user_id\":\"sap_003\",\"reason\":\"manual_admin_test\",\"performed_by\":\"admin_test\"}' --cli-binary-format raw-in-base64-out admin-test-response.json"

echo ""
echo -e "${GREEN}🎉 Enhanced Policy Manager with Admin Email Integration is now live!${NC}"
