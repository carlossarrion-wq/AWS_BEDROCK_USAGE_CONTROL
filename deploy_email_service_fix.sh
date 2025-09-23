#!/bin/bash

# Deploy Email Service Fix Script
# This script updates the bedrock-email-service Lambda function with the correct handler

echo "🚀 Starting bedrock-email-service deployment fix..."

# Create temporary deployment directory
TEMP_DIR="email_service_deployment_temp"
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

echo "📁 Created temporary deployment directory: $TEMP_DIR"

# Copy the required files
echo "📋 Copying files to deployment directory..."
cp "02. Source/Lambda Functions/bedrock_email_service.py" $TEMP_DIR/bedrock_email_service.py
cp lambda_handler.py $TEMP_DIR/lambda_handler.py

# Check if email_credentials.json exists and copy it
if [ -f "02. Source/Configuration/email_credentials.json" ]; then
    echo "📧 Copying email credentials..."
    cp "02. Source/Configuration/email_credentials.json" $TEMP_DIR/email_credentials.json
else
    echo "⚠️  Warning: email_credentials.json not found, creating placeholder..."
    cat > $TEMP_DIR/email_credentials.json << 'EOF'
{
  "gmail_smtp": {
    "server": "smtp.gmail.com",
    "port": 587,
    "user": "cline.aws.noreply@gmail.com",
    "password": "lozs wwqa vfpn nlup",
    "use_tls": true
  },
  "email_settings": {
    "default_language": "es",
    "timezone": "Europe/Madrid",
    "reply_to": "cline.aws.noreply@gmail.com"
  }
}
EOF
fi

# Create the deployment package
echo "📦 Creating deployment package..."
cd $TEMP_DIR
zip -r ../bedrock-email-service-fixed.zip . -x "*.pyc" "__pycache__/*"
cd ..

echo "✅ Created deployment package: bedrock-email-service-fixed.zip"

# Update the Lambda function
echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
    --function-name bedrock-email-service \
    --zip-file fileb://bedrock-email-service-fixed.zip

if [ $? -eq 0 ]; then
    echo "✅ Successfully updated bedrock-email-service Lambda function"
    
    # Wait for update to complete
    echo "⏳ Waiting for function update to complete..."
    aws lambda wait function-updated --function-name bedrock-email-service
    
    echo "✅ Function update completed"
    
    # Clean up
    echo "🧹 Cleaning up temporary files..."
    rm -rf $TEMP_DIR
    rm bedrock-email-service-fixed.zip
    
    echo "🎉 Email service fix deployment completed successfully!"
    echo ""
    echo "📧 The bedrock-email-service function now has:"
    echo "   - Correct lambda_handler.py entry point"
    echo "   - Enhanced email formatting with CSS styles"
    echo "   - Support for all email types (warning, blocking, unblocking, admin)"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Test the email service with a sample payload"
    echo "   2. Verify that bedrock-realtime-usage-controller now uses the enhanced emails"
    
else
    echo "❌ Failed to update Lambda function"
    echo "🧹 Cleaning up temporary files..."
    rm -rf $TEMP_DIR
    rm -f bedrock-email-service-fixed.zip
    exit 1
fi
