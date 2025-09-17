#!/bin/bash

# Deploy Bedrock Usage Monitor Lambda Function
# ==========================================
# This script packages and deploys the bedrock-usage-monitor Lambda function
# with the latest CloudWatch metrics publishing fixes.

set -e  # Exit on any error

echo "=========================================="
echo "DEPLOYING BEDROCK USAGE MONITOR LAMBDA"
echo "=========================================="

# Configuration
FUNCTION_NAME="bedrock-usage-monitor"
REGION="eu-west-1"
LAMBDA_DIR="individual_blocking_system/lambda_functions"
PACKAGE_NAME="bedrock-usage-monitor-lcorp-fix-$(date +%Y%m%d-%H%M%S).zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Preparing deployment package...${NC}"

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy Lambda function files
echo "Copying Lambda function files..."
cp "$LAMBDA_DIR/bedrock_usage_monitor.py" "$TEMP_DIR/"
cp "$LAMBDA_DIR/quota_config.json" "$TEMP_DIR/"

# Verify files are copied
echo "Files in package:"
ls -la "$TEMP_DIR/"

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
    
    # Update function configuration if needed
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --handler "bedrock_usage_monitor.lambda_handler" \
        --timeout 300 \
        --memory-size 256 \
        --region "$REGION" \
        --environment Variables='{"DYNAMODB_TABLE":"bedrock_user_daily_usage","SNS_TOPIC_ARN":"arn:aws:sns:eu-west-1:701055077130:bedrock-usage-alerts","POLICY_MANAGER_FUNCTION":"bedrock-policy-manager","ACCOUNT_ID":"701055077130"}' \
        --description "Bedrock Usage Monitor with CloudWatch metrics fix for lcorp_007 - $(date '+%Y-%m-%d %H:%M:%S')"
    
    echo -e "${GREEN}✓ Function configuration updated${NC}"
    
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

echo -e "${YELLOW}Step 5: Testing function...${NC}"

# Create test event for lcorp_007
TEST_EVENT='{
    "detail": {
        "eventTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "eventSource": "bedrock.amazonaws.com",
        "eventName": "InvokeModel",
        "userIdentity": {
            "type": "IAMUser",
            "userName": "lcorp_007",
            "arn": "arn:aws:iam::701055077130:user/lcorp_007"
        },
        "sourceIPAddress": "192.168.1.100",
        "userAgent": "aws-cli/2.0.0"
    }
}'

echo "Testing with lcorp_007 event..."
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

echo -e "${YELLOW}Step 6: Cleanup...${NC}"

# Keep the package for reference
echo "Deployment package saved as: $PACKAGE_NAME"
echo "You can delete it manually if no longer needed."

echo -e "${GREEN}=========================================="
echo -e "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo -e "==========================================${NC}"

echo ""
echo "Summary:"
echo "- Function: $FUNCTION_NAME"
echo "- Region: $REGION"
echo "- Package: $PACKAGE_NAME"
echo "- Includes: CloudWatch metrics publishing fix for lcorp_007"
echo ""
echo "Next steps:"
echo "1. Monitor CloudWatch logs for the function"
echo "2. Test with actual Bedrock API calls from lcorp_007"
echo "3. Verify dashboard shows updated metrics"
echo "4. Check CloudWatch metrics in UserMetrics namespace"

echo ""
echo -e "${YELLOW}Useful commands for monitoring:${NC}"
echo "# View recent logs:"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
echo ""
echo "# Check CloudWatch metrics:"
echo "aws cloudwatch get-metric-statistics --namespace UserMetrics --metric-name BedrockUsage --dimensions Name=User,Value=lcorp_007 --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 3600 --statistics Sum --region $REGION"
