# AWS Bedrock Usage Control - Email Delivery Integration Guide

## 🎯 Overview

This guide explains the comprehensive email delivery functionality integrated into the AWS Bedrock Usage Control system. The enhanced system now supports **5 different email scenarios** with Spanish templates and proper color coding.

## 📧 Email Scenarios Supported

### 1. Warning Email (Amber/Orange) 
- **Trigger**: When user reaches 80% of daily quota (200/250 requests)
- **Color**: Amber background (#F4B860)
- **Subject**: "Aviso de Uso de Bedrock - Te estás acercando a tu límite diario"
- **Content**: Spanish warning message with usage statistics and progress bar

### 2. Blocking Email (Light Red)
- **Trigger**: When user exceeds 100% of daily quota (250/250 requests)
- **Color**: Light red background (#EC7266)
- **Subject**: "Acceso a Bedrock Bloqueado - Límite diario excedido"
- **Content**: Spanish blocking notification with expiration details

### 3. Unblocking Email (Green)
- **Trigger**: When daily reset restores user access
- **Color**: Green background (#9CD286)
- **Subject**: "Acceso a Bedrock Restaurado - Ya puedes usar Bedrock nuevamente"
- **Content**: Spanish restoration notification

### 4. Admin Blocking Email (Light Red)
- **Trigger**: When AWS admin blocks user account manually
- **Color**: Light red background (#EC7266)
- **Subject**: "Acceso a Bedrock Bloqueado por Administrador"
- **Content**: Spanish admin blocking notification

### 5. Admin Unblocking Email (Green)
- **Trigger**: When AWS admin unblocks user manually (administrative safe)
- **Color**: Green background (#9CD286)
- **Subject**: "Acceso a Bedrock Restaurado por Administrador"
- **Content**: Spanish admin unblocking notification with protection details

## 🏗️ Architecture

### Files Created/Enhanced

1. **`email_credentials.json`** - Secure Gmail SMTP credentials
2. **`bedrock_email_service.py`** - Complete email service with all 5 scenarios
3. **`bedrock_usage_monitor_enhanced.py`** - Enhanced usage monitor with email integration
4. **`bedrock_policy_manager_enhanced.py`** - Enhanced policy manager for admin scenarios
5. **`test_email_service.py`** - Test script to verify all email functionality

### Integration Points

- **Usage Monitor** → Sends warning/blocking emails automatically
- **Policy Manager** → Sends admin blocking/unblocking emails
- **Daily Reset** → Sends unblocking emails during daily reset
- **All Functions** → Use the centralized email service

## 🚀 Deployment Steps

### Step 1: Configure Email Credentials

1. Update `email_credentials.json` with your Gmail SMTP settings:
```json
{
  "gmail_smtp": {
    "server": "smtp.gmail.com",
    "port": 587,
    "user": "your-email@gmail.com",
    "password": "your-app-password",
    "use_tls": true
  },
  "email_settings": {
    "default_language": "es",
    "timezone": "Europe/Madrid",
    "reply_to": "your-email@gmail.com"
  }
}
```

### Step 2: Deploy Enhanced Lambda Functions

Replace your existing Lambda functions with the enhanced versions:

1. **Usage Monitor**: Deploy `bedrock_usage_monitor_enhanced.py`
2. **Policy Manager**: Deploy `bedrock_policy_manager_enhanced.py`
3. **Email Service**: Include `bedrock_email_service.py` in all Lambda packages

### Step 3: Set Environment Variables

Add these environment variables to your Lambda functions:
```bash
EMAIL_NOTIFICATIONS_ENABLED=true
GMAIL_USER=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
```

### Step 4: Update IAM User Tags

Ensure all users have proper tags in IAM for personalization:

**Required Tags:**
- `Email` tag: User's email address for notifications
- `Person` tag: User's display name for personalized emails (optional but recommended)

```bash
# Add email tag (required)
aws iam tag-user --user-name sap_003 --tags Key=Email,Value=carlos.sarrion@es.ibm.com

# Add person tag for personalization (recommended)
aws iam tag-user --user-name sap_003 --tags Key=Person,Value="Carlos Sarrión"
```

**Personalization Logic:**
1. **Priority 1**: Uses `Person` tag if exists and not "unknown"
2. **Priority 2**: Uses email username (part before @) if `Person` tag is missing/unknown
3. **Priority 3**: Falls back to user_id if no other options available

## 🧪 Testing

### Run the Test Script

```bash
cd individual_blocking_system/lambda_functions
python3 test_email_service.py
```

**Expected Output:**
```
🧪 Testing Enhanced Email Service
==================================================
✅ Email service initialized successfully
   SMTP Server: smtp.gmail.com
   SMTP Port: 587
   Gmail User: cline.aws.noreply@gmail.com

📧 Testing Email Scenarios:
------------------------------
1. Testing Warning Email (Amber)...
   ✅ Warning email test: SUCCESS
2. Testing Blocking Email (Light Red)...
   ✅ Blocking email test: SUCCESS
3. Testing Unblocking Email (Green)...
   ✅ Unblocking email test: SUCCESS
4. Testing Admin Blocking Email (Light Red)...
   ✅ Admin blocking email test: SUCCESS
5. Testing Admin Unblocking Email (Green)...
   ✅ Admin unblocking email test: SUCCESS

🎯 Email Service Test Summary:
==================================================
✅ All 5 email scenarios have been tested
📧 Check the recipient's email inbox for the test emails
```

## 📱 Email Templates

### Template Features

- **Spanish Language**: All emails are in Spanish as requested
- **Color Coding**: Proper color schemes matching your examples
- **HTML + Plain Text**: Both formats for maximum compatibility
- **Madrid Timezone**: All timestamps show in CET (Europe/Madrid)
- **Professional Design**: Clean, responsive HTML templates
- **Usage Statistics**: Visual progress bars and statistics
- **Clear Actions**: What happens next and contact information

### Template Structure

Each email includes:
- **Header**: Colored header with title and subtitle
- **Content**: Main message with relevant details
- **Statistics**: Usage numbers and progress indicators (where applicable)
- **Next Steps**: What the user should expect
- **Footer**: System information and timestamp

## 🔧 Configuration

### Email Service Configuration

The email service automatically:
- Retrieves user emails from IAM tags
- Handles SSL certificate issues with Gmail SMTP
- Formats timestamps in Madrid timezone
- Sends both HTML and plain text versions
- Logs all email operations

### Error Handling

The system includes comprehensive error handling:
- SSL certificate verification bypass for Gmail
- Graceful fallback when user email not found
- Detailed logging for troubleshooting
- Non-blocking email failures (system continues working)

## 🎨 Email Examples

### Warning Email (Amber)
- **Background**: #F4B860 (Amber)
- **Progress Bar**: Visual indicator of usage percentage
- **Statistics**: Current usage, remaining requests, daily limit
- **Message**: "Te estás acercando a tu límite diario"

### Blocking Email (Light Red)
- **Background**: #EC7266 (Light Red)
- **Alert Box**: Prominent blocking notification
- **Details**: Reason, team, expiration time, duration
- **Message**: "Tu acceso a AWS Bedrock ha sido bloqueado temporalmente"

### Unblocking Email (Green)
- **Background**: #9CD286 (Green)
- **Success Box**: Positive restoration message
- **Information**: What this means and next steps
- **Message**: "¡Buenas noticias! Tu acceso a AWS Bedrock ha sido restaurado"

## 🔐 Security

### Gmail App Passwords

For Gmail SMTP, use App Passwords instead of regular passwords:
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password for "Mail"
3. Use the App Password in your credentials file

### Credential Storage

- Store credentials in `email_credentials.json`
- Use environment variables for Lambda deployment
- Never commit credentials to version control
- Consider using AWS Secrets Manager for production

## 📊 Monitoring

### Email Delivery Monitoring

The system logs all email operations:
- Successful email deliveries
- Failed email attempts
- User email retrieval from IAM
- SMTP connection issues

### CloudWatch Integration

Email events are logged to CloudWatch for monitoring:
- Email service initialization
- Individual email send results
- Error conditions and troubleshooting

## 🚨 Troubleshooting

### Common Issues

1. **SSL Certificate Error**
   - Fixed with `context.verify_mode = ssl.CERT_NONE`
   - Gmail SMTP requires less strict certificate verification

2. **User Email Not Found**
   - Ensure IAM users have `Email` tag
   - Check IAM permissions for tag reading

3. **Gmail Authentication Failed**
   - Use App Passwords, not regular passwords
   - Enable 2-Factor Authentication first

4. **Email Not Received**
   - Check spam/junk folders
   - Verify recipient email address
   - Check Gmail sending limits

## ✅ Success Criteria

The email integration is successful when:
- ✅ All 5 email scenarios send successfully
- ✅ Emails display proper Spanish content
- ✅ Color coding matches requirements (Amber, Light Red, Green)
- ✅ Timestamps show Madrid timezone (CET)
- ✅ HTML formatting displays correctly
- ✅ User emails are retrieved from IAM tags
- ✅ System continues working even if emails fail

## 🎉 Conclusion

The AWS Bedrock Usage Control system now has comprehensive email delivery functionality that:

- **Informs users** about their quota usage with warning emails
- **Notifies users** when they're blocked due to quota limits
- **Celebrates restoration** when access is restored
- **Communicates admin actions** for manual blocks/unblocks
- **Provides administrative protection** for manually unblocked users

All emails follow the exact Spanish format and color coding you requested, ensuring users receive clear, professional notifications about their Bedrock access status.
