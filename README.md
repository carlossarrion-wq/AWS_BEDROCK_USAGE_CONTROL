# AWS Bedrock Usage Control System - Complete Documentation

## 📋 Project Overview

The **AWS Bedrock Usage Control System** is a comprehensive enterprise-grade solution for monitoring, controlling, and managing AWS Bedrock usage across organizations. This system provides real-time usage tracking, automatic blocking capabilities, administrative protection mechanisms, and a modern web dashboard for complete visibility and control.

### 🎯 Core Objectives

- **Real-time Usage Monitoring**: Track every Bedrock API call with detailed metrics and cost analysis
- **Intelligent Blocking System**: Automatic user blocking with administrative protection mechanisms
- **Granular Access Control**: User, team, and tool-specific permissions and quotas
- **Cost Management**: Detailed cost tracking and budget enforcement
- **Audit & Compliance**: Complete audit trail of all operations and user activities
- **Modern Dashboard**: Interactive web interface for monitoring and management

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK USAGE CONTROL SYSTEM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   Web Dashboard │    │   CLI Manager   │    │  Lambda Functions       │  │
│  │   (HTML/JS)     │    │   (Python)      │    │  (RDS MySQL)            │  │
│  │                 │    │                 │    │                         │  │
│  │ • User Mgmt     │    │ • User Creation │    │ • Realtime Controller   │  │
│  │ • Team Analysis │    │ • Policy Mgmt   │    │ • Daily Reset           │  │
│  │ • Cost Tracking │    │ • Group Mgmt    │    │ • Email Service         │  │
│  │ • Blocking Mgmt │    │ • Provisioning  │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                           │              │
│           └───────────────────────┼───────────────────────────┘              │
│                                   │                                          │
│  ┌─────────────────────────────────┼─────────────────────────────────────────┐ │
│  │                    AWS CLOUD INFRASTRUCTURE                              │ │
│  │                                 │                                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────────┐ │ │
│  │  │     IAM     │  │ CloudWatch  │  │            Lambda Functions         │ │ │
│  │  │             │  │             │  │                                     │ │ │
│  │  │ • Users     │  │ • Metrics   │  │ • bedrock-realtime-usage-controller │ │ │
│  │  │ • Groups    │  │ • Logs      │  │ • bedrock-daily-reset               │ │ │
│  │  │ • Roles     │  │ • Alarms    │  │ • bedrock-email-service             │ │ │
│  │  │ • Policies  │  │ • Filters   │  │                                     │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────────────┘ │ │
│  │                                                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────────┐ │ │
│  │  │ CloudTrail  │  │ EventBridge │  │              RDS MySQL              │ │ │
│  │  │             │  │             │  │                                     │ │ │
│  │  │ • API Calls │  │ • Rules     │  │ • users                             │ │ │
│  │  │ • Audit Log │  │ • Triggers  │  │ • bedrock_requests                  │ │ │
│  │  │ • Events    │  │ • Schedule  │  │ • blocking_operations               │ │ │
│  │  │             │  │             │  │ • model_pricing                     │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────────────┘ │ │
│  │                                                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────────┐ │ │
│  │  │     SNS     │  │     SES     │  │            Gmail SMTP               │ │ │
│  │  │             │  │             │  │                                     │ │ │
│  │  │ • Alerts    │  │ • Email     │  │ • Email Notifications               │ │ │
│  │  │ • Topics    │  │ • Templates │  │ • Warning Emails                    │ │ │
│  │  │ • Subs      │  │ • Delivery  │  │ • Blocking Emails                   │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┐
```

### Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Makes    │───▶│   CloudTrail    │───▶│   EventBridge   │
│ Bedrock Request │    │   Captures      │    │   Processes     │
│                 │    │     Event       │    │     Event       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Email & SNS   │◀───│ Realtime Usage  │◀───│   Lambda        │
│  Notifications  │    │   Controller    │    │  Triggered      │
│                 │    │ (MERGED FUNC)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Automatic       │
                       │ Blocking &      │
                       │ Policy Mgmt     │
                       │ (if needed)     │
                       └─────────────────┘
```

## 📁 Project Structure

```
AWS_BEDROCK_USAGE_CONTROL/
├── 📄 README.md                                    # This complete project documentation
├── 📄 bedrock_usage_dashboard_modular.html         # Main web dashboard
├── 📄 login.html                                   # Dashboard login page
├── 📄 provision_bedrock_user.py                    # Complete user provisioning script
├── 📄 package.json                                 # Node.js dependencies for testing
├── 📄 env_vars.json                                # Environment variables configuration
│
├── 🗂️ 01. Project documents/                       # 📋 COMPLETE DOCUMENTATION
│   ├── 📄 00_DOCUMENTATION_SUMMARY.md              # Documentation overview
│   └── 🗂️ Installation Manual/                     # Detailed installation guides
│       ├── 📄 00_Documentation_Overview.md         # Navigation guide
│       ├── 📄 01_Complete_Installation_Guide.md    # Step-by-step installation
│       ├── 📄 02_AWS_Resources_Documentation.md    # AWS resource specifications
│       ├── 📄 03_IAM_Policies_and_Roles.json      # IAM configuration
│       └── 📄 04_Complete_Deployment_Script.sh     # Automated deployment
│
├── 🗂️ 02. Source/                                  # 🔧 COMPLETE SOURCE CODE
│   ├── 📄 README_Source_Code.md                    # Source code documentation
│   │
│   ├── 🗂️ Dashboard/                               # 🌐 Web Dashboard Components
│   │   ├── 📄 bedrock_usage_dashboard_modular.html # Main dashboard interface
│   │   ├── 📄 login.html                           # Authentication page
│   │   ├── 🗂️ css/                                 # Dashboard styling
│   │   │   └── 📄 dashboard.css                    # Main dashboard styles
│   │   └── 🗂️ js/                                  # Dashboard JavaScript
│   │       ├── 📄 dashboard.js                     # Main dashboard logic
│   │       ├── 📄 mysql-data-service.js            # MySQL data service
│   │       ├── 📄 blocking.js                      # Blocking management
│   │       ├── 📄 charts.js                        # Chart visualizations
│   │       ├── 📄 config.js                        # Frontend configuration
│   │       ├── 📄 cost-analysis-v2.js              # Cost analysis features
│   │       └── 📄 hourly-analytics.js              # Hourly usage analytics
│   │
│   ├── 🗂️ Lambda Functions/                        # ⚡ CURRENT LAMBDA FUNCTIONS
│   │   ├── 📄 bedrock-realtime-usage-controller.py # 🔥 MERGED FUNCTION (NEW)
│   │   ├── 📄 bedrock_daily_reset.py               # Daily reset operations
│   │   ├── 📄 bedrock_email_service.py             # Email notification service
│   │   ├── 📄 email_credentials.json               # Email service credentials
│   │   ├── 📄 quota_config.json                    # User/team quota configuration
│   │   └── 📄 test_email_service.py                # Email service testing
│   │
│   ├── 🗂️ Scripts/                                 # 🔧 CLI Management & Deployment
│   │   ├── 📄 bedrock_manager.py                   # Main CLI interface
│   │   ├── 📄 config.json                          # AWS configuration
│   │   ├── 📄 provision.py                         # Provisioning utilities
│   │   ├── 📄 provision_bedrock_user.py            # User provisioning
│   │   ├── 📄 deploy_bedrock_realtime_usage_controller.sh # Deploy merged function
│   │   ├── 📄 update_cloudtrail_for_new_function.sh # Update AWS artifacts
│   │   ├── 📄 disable_old_lambda_functions.sh      # Disable old functions
│   │   ├── 📄 cleanup_old_function_artifacts.sh    # Clean up AWS artifacts
│   │   ├── 🗂️ user/                                # User management module
│   │   ├── 🗂️ group/                               # Group management module
│   │   ├── 🗂️ policy/                              # Policy management module
│   │   └── 🗂️ utils/                               # Utility functions
│   │
│   ├── 🗂️ Database/                                # 🗄️ Database Schema & Scripts
│   │   ├── 📄 README.md                            # Database documentation
│   │   ├── 📄 create_database.sql                  # Simple database creation
│   │   ├── 🗂️ Tables/                              # Table creation scripts
│   │   ├── 🗂️ Views/                               # Database view definitions
│   │   ├── 🗂️ Stored_Procedures/                  # Stored procedure definitions
│   │   ├── 🗂️ Indexes/                             # Additional index scripts
│   │   ├── 🗂️ Functions/                           # Custom function scripts
│   │   └── 🗂️ Triggers/                            # Trigger scripts
│   │
│   └── 🗂️ Configuration/                           # ⚙️ Configuration Files
│       ├── 📄 package.json                         # Node.js dependencies
│       ├── 📄 env_vars.json                        # Environment variables
│       ├── 📄 quota_config.json                    # User/team quotas
│       ├── 📄 email_credentials.json               # Email configuration
│       ├── 📄 test_bedrock_payload.json            # Test payloads
│       └── 📄 test_blocking_payload.json           # Blocking test data
│
├── 🗂️ 03. Build_folder/                            # 🏗️ Build & Deployment Artifacts
│   └── Various build and deployment files
│
└── 🗂️ 04. Testing/                                 # 🧪 Testing & Quality Assurance
    ├── 📄 test_bedrock_realtime_usage_controller_comprehensive.py # Comprehensive tests
    ├── 📄 test_enhanced_blocking.py                # Enhanced blocking tests
    ├── 📄 test_email_service.py                    # Email notification tests
    └── Various test and verification scripts
```

## 🔧 Core Components

### 1. Web Dashboard (`02. Source/Dashboard/`)

**Purpose**: Interactive web interface for monitoring and managing Bedrock usage

**Key Features**:
- **Multi-tab Interface**: User Consumption, Team Consumption, Consumption Details, Blocking Management
- **Real-time Data**: Live usage statistics and status updates
- **Blocking Management**: Manual blocking/unblocking with duration options
- **Export Capabilities**: CSV export for all data tables
- **Cost Analysis**: Detailed cost tracking and budget monitoring
- **Responsive Design**: Works on desktop and mobile devices

**Technical Stack**:
- HTML5 with modern CSS3
- Vanilla JavaScript (no external dependencies)
- AWS SDK for JavaScript (browser)
- Chart.js for visualizations
- Bootstrap for responsive design

### 2. CLI Management System (`02. Source/Scripts/`)

**Purpose**: Command-line interface for administrative operations

**Core Modules**:

#### `bedrock_manager.py` - Main CLI Interface
```python
# Key Commands:
python3 bedrock_manager.py user create <username> <person_name> <team>
python3 bedrock_manager.py user create-key <username> <tool_name>
python3 bedrock_manager.py user info <username>
python3 bedrock_manager.py group create <team_name>
python3 bedrock_manager.py policy create <policy_name>
```

#### User, Group, and Policy Management Modules
- **user_manager.py**: User CRUD operations, API key generation
- **group_manager.py**: Team/group creation and management
- **policy_manager.py**: IAM policy operations and management

### 3. Lambda Functions System (Updated September 2025)

**Purpose**: Real-time monitoring and blocking system using RDS MySQL

#### 🔥 **NEW: `bedrock-realtime-usage-controller.py` - MERGED FUNCTION**
**Major Architecture Change**: This function combines the functionality of multiple previous functions into a single, more efficient Lambda function.

**Merged Functionality**:
- **Real-time Request Logging** (previously `bedrock-realtime-logger-fixed`)
- **Policy Management & Blocking** (previously `bedrock-policy-manager-enhanced`)
- **Usage Monitoring & Quota Checking**
- **Email Notification Integration**

**Key Features**:
- **Real-time CloudTrail Event Processing**: Processes Bedrock API calls in real-time with CET timezone handling
- **Direct RDS MySQL Integration**: Uses PyMySQL for direct database operations
- **Auto-provisioning**: Automatically provisions new users in the database
- **Usage Limit Checking**: Uses stored procedures for efficient limit evaluation
- **Automatic Blocking**: Implements IAM policy-based blocking when limits are exceeded
- **Email Notifications**: Integrates with bedrock-email-service for user notifications
- **Comprehensive Audit Logging**: All operations logged for compliance and debugging
- **CET Timezone Support**: All timestamps handled in Central European Time

**Performance Benefits**:
- **Reduced Latency**: Single function eliminates inter-function communication delays
- **Lower Costs**: Fewer Lambda invocations and reduced complexity
- **Simplified Architecture**: Easier to maintain and debug
- **Better Resource Utilization**: Optimized memory and execution time

#### `bedrock_daily_reset.py` - Daily Reset
**Functionality**:
- Automatic daily reset at 00:00 CET
- Unblock automatically blocked users
- Generate daily summary statistics
- Send comprehensive email notifications
- Complete audit trail maintenance

#### `bedrock_email_service.py` - Email Service
**Features**:
- Gmail SMTP integration
- Professional HTML email templates
- Multi-language support (Spanish/English)
- Comprehensive notification types
- Error handling and logging

### 4. Database System (RDS MySQL)

**Purpose**: Unified persistent storage for all usage tracking and audit data

#### Core Tables:

**`users`** - User Configuration
```sql
- user_id (PRIMARY KEY)
- team, person_tag
- daily_limit, monthly_limit
- is_blocked, blocked_reason, blocked_until
- admin_protection_by
- created_at, updated_at
```

**`bedrock_requests`** - Individual Request Records
```sql
- id (AUTO_INCREMENT PRIMARY KEY)
- user_id, team, request_timestamp
- model_id, model_name, request_type
- input_tokens, output_tokens, total_tokens
- cost_usd, region, source_ip, user_agent
- created_at
```

**`blocking_operations`** - Complete Audit Trail
```sql
- id (AUTO_INCREMENT PRIMARY KEY)
- user_id, operation, reason
- performed_by, expires_at
- created_at
```

**`model_pricing`** - Cost Calculation
```sql
- model_id (PRIMARY KEY)
- model_name, input_token_price, output_token_price
- region, effective_date
```

## 🔄 System Workflows

### User Request Processing Flow (Updated Architecture)

```
1. User makes Bedrock API call
   ↓
2. CloudTrail captures the event
   ↓
3. EventBridge triggers Lambda (bedrock-realtime-usage-controller)
   ↓
4. MERGED Lambda function processes event:
   - Extracts user information from IAM tags
   - Logs request to RDS MySQL
   - Checks user limits via stored procedures
   - Evaluates blocking conditions
   - Executes blocking if needed (IAM policy updates)
   - Sends notifications (email + SNS)
   ↓
5. All operations completed in single function execution
   ↓
6. User is blocked/warned as appropriate
```

### Daily Reset Workflow

```
Every day at 00:00 CET:
1. Daily Reset Lambda triggered by EventBridge
   ↓
2. Generate daily summary from RDS MySQL data
   ↓
3. Query all currently blocked users
   ↓
4. Execute complete unblocking workflow:
   - Update blocking_operations table
   - Remove IAM deny policies
   - Send unblocking email notifications
   ↓
5. Send comprehensive daily summary notifications
```

## 🛡️ Security & Permissions

### IAM Roles and Policies

#### New Merged Function Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "iam:GetUser",
        "iam:GetUserPolicy",
        "iam:PutUserPolicy",
        "iam:DeleteUserPolicy",
        "lambda:InvokeFunction",
        "sns:Publish"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Lambda Execution Roles
- **bedrock-realtime-usage-controller-role**: RDS, SNS, IAM, Lambda invoke permissions
- **bedrock-daily-reset-role**: RDS, IAM, SNS, SES permissions
- **bedrock-email-service-role**: SES and basic execution permissions

### Data Protection

- **Encryption at Rest**: RDS instances encrypted with AWS KMS
- **Encryption in Transit**: All API calls use HTTPS/TLS
- **Access Logging**: Complete audit trail of all operations
- **Data Retention**: Configurable retention policies
- **Principle of Least Privilege**: Minimal required permissions for all components

## 📊 Monitoring & Alerting

### CloudWatch Metrics

**Custom Metrics**:
- `UserMetrics/BedrockUsage` - Per-user usage tracking
- `TeamMetrics/BedrockUsage` - Team-level aggregations
- `BlockingMetrics/Operations` - Blocking operation counts
- `CostMetrics/DailyCost` - Daily cost tracking

**System Metrics**:
- Lambda function duration and errors
- RDS connection and query performance
- Email delivery success rates

### SNS Notifications

**Alert Types**:
1. **Warning Alerts**: User approaching daily limit
2. **Blocking Alerts**: User automatically blocked
3. **Admin Alerts**: Manual blocking/unblocking operations
4. **System Alerts**: Lambda errors, database issues
5. **Daily Summaries**: Usage and cost reports

## 💰 Cost Management

### Cost Tracking Features

1. **Real-time Cost Calculation**: Based on token usage and model pricing
2. **Daily/Monthly Budgets**: Configurable per user and team
3. **Cost Alerts**: Automatic notifications when budgets exceeded
4. **Historical Analysis**: Cost trends and projections
5. **Model Comparison**: Cost efficiency analysis across models

## 🔧 Configuration Management

### Main Configuration Files

#### `02. Source/Scripts/config.json` - AWS Configuration
```json
{
  "account_id": "701055077130",
  "region": "eu-west-1",
  "inference_profiles": {
    "claude": "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.anthropic.claude-sonnet-4-20250514-v1:0",
    "nova_pro": "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.amazon.nova-pro-v1:0"
  },
  "default_quotas": {
    "user": {
      "monthly_limit": 5000,
      "daily_limit": 350,
      "warning_threshold": 150
    }
  }
}
```

#### `02. Source/Configuration/quota_config.json` - User/Team Quotas
```json
{
  "users": {
    "darwin_001": {
      "daily_limit": 350,
      "monthly_limit": 5000,
      "team": "team_darwin_group"
    }
  },
  "teams": {
    "team_darwin_group": {
      "monthly_limit": 25000
    }
  }
}
```

## 🚀 Quick Start Guide

### Option 1: Automated Deployment (Recommended)
```bash
cd "01. Project documents/Installation Manual"
./04_Complete_Deployment_Script.sh
```

### Option 2: Manual Step-by-Step
1. Read this README for system understanding
2. Follow `01. Project documents/Installation Manual/01_Complete_Installation_Guide.md`
3. Use source code from `02. Source/` folder as needed

### Option 3: Source Code Development
1. Review `02. Source/README_Source_Code.md` for code organization
2. Modify source files in appropriate folders
3. Deploy using installation guides

## 🧪 Testing & Quality Assurance

### Test Suite

**Automated Tests**:
- `04. Testing/test_bedrock_realtime_usage_controller_comprehensive.py` - Comprehensive tests for merged function
- Unit tests for all Lambda functions
- Integration tests for dashboard functionality
- End-to-end blocking workflow tests
- Database connection and query tests

### Quality Checks

**Code Quality**:
- Python code formatting and linting
- JavaScript code quality checks
- Security scanning for vulnerabilities
- Database query optimization

## 📈 Performance & Scalability

### Performance Optimizations

1. **Lambda Function Consolidation**: Merged multiple functions into single efficient function
2. **Database Optimizations**: Optimized indexes and connection pooling
3. **Caching Strategy**: Lambda function warm-up and connection reuse

### Scalability Considerations

- **Auto-scaling**: RDS auto-scaling enabled
- **Lambda Concurrency**: Reserved concurrency for critical functions
- **Regional Deployment**: EU-West-1 optimized for European operations
- **Data Archiving**: Automated cleanup of old usage data

## 🔄 Maintenance & Operations

### Regular Maintenance Tasks

**Daily**:
- Monitor Lambda function errors
- Check RDS performance metrics
- Review blocking operations and user feedback

**Weekly**:
- Analyze usage patterns and trends
- Review and update user quotas as needed
- Check system capacity and scaling needs

**Monthly**:
- Update model pricing information
- Review and optimize database performance
- Update documentation and runbooks

## 📞 Support & Troubleshooting

### Common Issues

1. **Dashboard not loading data**: Check AWS credentials and Lambda function permissions
2. **Users not being blocked**: Verify Lambda function permissions and EventBridge rules
3. **Email notifications not working**: Check Gmail SMTP configuration and credentials
4. **Database connection issues**: Verify RDS endpoint and security group settings

### Logging & Debugging

**Log Locations**:
- Lambda logs: CloudWatch Logs `/aws/lambda/function-name`
- Application logs: Custom log groups for detailed debugging
- Database logs: RDS slow query logs and error logs
- System metrics: CloudWatch custom metrics

### Getting Help

- Check the `01. Project documents/Installation Manual/` for detailed setup instructions
- Review CloudWatch logs for error messages
- Use the test scripts in `04. Testing/` to verify system functionality
- Contact the development team for complex issues

---

**Last Updated**: September 2025  
**Version**: 4.0.0 (Lambda Function Consolidation)  
**Maintainer**: AWS Bedrock Usage Control System Team

## 📝 Recent Changes

### Version 4.0.0 - Lambda Function Consolidation (September 2025)
- **🔥 MAJOR ARCHITECTURE CHANGE**: Merged multiple Lambda functions into single efficient function
- **New Merged Function**: `bedrock-realtime-usage-controller` combines real-time logging, quota checking, blocking, and notifications
- **Functions Consolidated**: 
  - `bedrock-realtime-logger-fixed` (merged into new controller)
  - `bedrock-policy-manager-enhanced` (merged into new controller)
- **Performance Improvements**: Reduced latency, lower costs, simplified architecture
- **Complete AWS Cleanup**: Removed all artifacts from old functions
- **Updated Documentation**: Complete documentation refresh to reflect new architecture
- **Comprehensive Testing**: Full regression testing confirms all functionality preserved
- **Dashboard Integration**: Updated dashboard to use new merged function seamlessly

### Previous Versions
- **Version 3.0.0**: RDS MySQL Migration from DynamoDB
- **Version 2.0.0**: Enhanced blocking system with administrative protection
- **Version 1.0.0**: Initial release with DynamoDB backend

## 🎯 Architecture Benefits

### Lambda Function Consolidation Benefits
- **⚡ Improved Performance**: Single function eliminates inter-function communication delays
- **💰 Cost Reduction**: Fewer Lambda invocations and reduced complexity
- **🔧 Simplified Maintenance**: Single codebase easier to maintain and debug
- **🚀 Better Resource Utilization**: Optimized memory and execution time
- **🛡️ Enhanced Security**: Reduced attack surface with fewer functions
- **📊 Cleaner Architecture**: More logical and easier to understand system design
