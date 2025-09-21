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
│  │ • User Mgmt     │    │ • User Creation │    │ • Request Logger        │  │
│  │ • Team Analysis │    │ • Policy Mgmt   │    │ • Usage Monitor         │  │
│  │ • Cost Tracking │    │ • Group Mgmt    │    │ • Daily Reset           │  │
│  │ • Blocking Mgmt │    │ • Provisioning  │    │ • Query Executor        │  │
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
│  │  │ • Users     │  │ • Metrics   │  │ • bedrock-realtime-request-logger   │ │ │
│  │  │ • Groups    │  │ • Logs      │  │ • bedrock-mysql-query-executor      │ │ │
│  │  │ • Roles     │  │ • Alarms    │  │ • bedrock-usage-monitor             │ │ │
│  │  │ • Policies  │  │ • Filters   │  │ • bedrock-daily-reset               │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────────────┘ │ │
│  │                                                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────────┐ │ │
│  │  │ CloudTrail  │  │ EventBridge │  │              RDS MySQL              │ │ │
│  │  │             │  │             │  │                                     │ │ │
│  │  │ • API Calls │  │ • Rules     │  │ • user_limits                       │ │ │
│  │  │ • Audit Log │  │ • Triggers  │  │ • bedrock_requests                  │ │ │
│  │  │ • Events    │  │ • Schedule  │  │ • user_blocking_status              │ │ │
│  │  │             │  │             │  │ • blocking_audit_log                │ │ │
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
│   Email & SNS   │◀───│  Request Logger │◀───│   Lambda        │
│  Notifications  │    │   Updates       │    │  Triggered      │
│                 │    │   RDS MySQL     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Usage Monitor   │
                       │   Evaluates     │
                       │   & Blocks      │
                       │   (if needed)   │
                       └─────────────────┘
```

## 📁 Project Structure

```
AWS_BEDROCK_USAGE_CONTROL/
├── 📄 README.md                                    # Original project documentation
├── 📄 bedrock_usage_dashboard_modular.html         # Main web dashboard
├── 📄 login.html                                   # Dashboard login page
├── 📄 provision_bedrock_user.py                    # Complete user provisioning script
├── 📄 package.json                                 # Node.js dependencies for testing
├── 📄 env_vars.json                                # Environment variables configuration
│
├── 🗂️ Project documents/                           # 📋 THIS DOCUMENTATION FOLDER
│   ├── 📄 README.md                                # Complete project documentation
│   ├── 🗂️ README/                                  # Additional README resources
│   └── 🗂️ Installation Manual/                     # Detailed installation guides
│
├── 🗂️ src/                                         # 🔧 CLI Management System
│   ├── 📄 bedrock_manager.py                       # Main CLI interface
│   ├── 📄 config.json                              # AWS configuration
│   ├── 📄 provision.py                             # Provisioning utilities
│   │
│   ├── 🗂️ user/                                    # User management module
│   │   ├── 📄 __init__.py
│   │   └── 📄 user_manager.py                      # User CRUD operations
│   │
│   ├── 🗂️ group/                                   # Group management module
│   │   ├── 📄 __init__.py
│   │   └── 📄 group_manager.py                     # Team/group operations
│   │
│   ├── 🗂️ policy/                                  # Policy management module
│   │   ├── 📄 __init__.py
│   │   └── 📄 policy_manager.py                    # IAM policy operations
│   │
│   └── 🗂️ utils/                                   # Utility functions
│       ├── 📄 __init__.py
│       └── 📄 aws_utils.py                         # AWS helper functions
│
├── 🗂️ Project documents/Source/Lambda Functions/   # 🛡️ Current Lambda Functions (RDS MySQL)
│   ├── 📄 bedrock_realtime_request_logger.py       # Real-time request logging
│   ├── 📄 bedrock_mysql_query_executor.py          # Database query executor
│   ├── 📄 bedrock_usage_monitor_current.py         # Usage monitoring
│   ├── 📄 bedrock_daily_reset.py                   # Daily reset functionality (RDS MySQL)
│   ├── 📄 bedrock_email_service.py                 # Email notification service
│   ├── 📄 email_credentials.json                   # Email service credentials
│   ├── 📄 quota_config.json                        # User/team quota configuration
│   └── 📄 test_email_service.py                    # Email service testing
│
├── 🗂️ migration/                                   # 🗄️ Database & Deployment Scripts
│   ├── 📄 01_create_rds_instance.sh                # RDS MySQL instance creation
│   ├── 📄 02_create_database_schema_v2.sql         # Enhanced database schema
│   ├── 📄 03_data_migration_lambda.py              # Data migration utilities
│   ├── 📄 05_realtime_request_logger_enhanced_blocking_gmail_fixed.py  # Real-time logger
│   ├── 📄 06_deploy_realtime_logger.sh             # Logger deployment script
│   ├── 📄 07_configure_database_connection.sh      # Database connection setup
│   ├── 📄 08_initialize_database.sql               # Database initialization
│   ├── 📄 09_deploy_complete_realtime_system.sh    # Complete system deployment
│   ├── 📄 13_update_stored_procedures_for_request_limits_pymysql.sql  # Stored procedures
│   ├── 📄 16_cleanup_database_schema_final.sql     # Database cleanup
│   └── 🗂️ lambda_package*/                         # Lambda deployment packages
│
├── 🗂️ css/                                         # 🎨 Dashboard Styling
│   └── 📄 dashboard.css                            # Main dashboard styles
│
├── 🗂️ js/                                          # 💻 Dashboard JavaScript
│   ├── 📄 dashboard.js                             # Main dashboard logic
│   ├── 📄 mysql-data-service.js                    # MySQL data service
│   ├── 📄 blocking.js                              # Blocking management
│   ├── 📄 charts.js                                # Chart visualizations
│   ├── 📄 config.js                                # Frontend configuration
│   ├── 📄 cost-analysis-v2.js                      # Cost analysis features
│   └── 📄 hourly-analytics.js                      # Hourly usage analytics
│
└── 📄 Various Test & Configuration Files:
    ├── 📄 test_bedrock_payload.json                # Test payloads
    ├── 📄 test_blocking_payload.json               # Blocking test data
    ├── 📄 test_enhanced_blocking.py                # Enhanced blocking tests
    ├── 📄 check_blocking_audit_log.py              # Audit log verification
    ├── 📄 execute_blocking_schema_changes.py       # Schema update scripts
    ├── 📄 verify_database_cleanup.py               # Database verification
    └── 📄 Various analysis and summary documents
```

## 🔧 Core Components

### 1. Web Dashboard (`bedrock_usage_dashboard_modular.html`)

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

### 2. CLI Management System (`src/`)

**Purpose**: Command-line interface for administrative operations

**Core Modules**:

#### `bedrock_manager.py` - Main CLI Interface
```python
# Key Commands:
python3 src/bedrock_manager.py user create <username> <person_name> <team>
python3 src/bedrock_manager.py user create-key <username> <tool_name>
python3 src/bedrock_manager.py user info <username>
python3 src/bedrock_manager.py group create <team_name>
python3 src/bedrock_manager.py policy create <policy_name>
```

#### `user_manager.py` - User Operations
- User creation and deletion
- API key generation with tool-specific tagging
- User information retrieval
- Team assignment and management

#### `group_manager.py` - Team Management
- Team/group creation
- Role creation for teams
- Policy attachment to groups
- Team-based resource management

#### `policy_manager.py` - IAM Policy Management
- Bedrock-specific policy creation
- Tool-specific policy generation
- Policy attachment and detachment
- Permission management

### 3. Lambda Functions System (RDS MySQL-based)

**Purpose**: Real-time monitoring and blocking system using RDS MySQL

#### `bedrock_realtime_request_logger.py` - Real-time Request Logger
**Functionality**:
- Real-time CloudTrail event processing
- CET timezone handling for European operations
- Direct RDS MySQL logging with PyMySQL
- User team and person tag extraction from IAM
- Comprehensive error handling and logging

**Key Features**:
- **RDS MySQL Integration**: Uses PyMySQL for database connections
- **Connection Pooling**: Optimized database connection management
- **CET Timezone Support**: Proper timezone conversion for European operations
- **User Auto-provisioning**: Automatically creates user limits based on quota config
- **Comprehensive Logging**: Detailed logs for all operations

#### `bedrock_mysql_query_executor.py` - Database Query Executor
**Operations**:
- Execute MySQL queries for dashboard integration
- JSON serialization for datetime and decimal objects
- Parameterized query support for security
- Connection management with proper cleanup

#### `bedrock_usage_monitor_current.py` - Usage Monitor
**Functionality**:
- Monitor usage patterns and limits
- Database connectivity testing
- Query execution with proper error handling
- Support for complex database operations

#### `bedrock_daily_reset.py` - Daily Reset (RDS MySQL Version)
**Functionality**:
- Automatic daily reset at 00:00 CET
- Unblock automatically blocked users
- Generate daily summary statistics
- Send comprehensive email notifications
- Complete audit trail maintenance

**Key Features**:
- **RDS MySQL Integration**: Re-engineered from DynamoDB to RDS MySQL
- **CET Timezone Support**: All operations in Central European Time
- **Comprehensive Unblocking**: Complete workflow with IAM policy management
- **Daily Summaries**: Detailed usage and blocking statistics
- **Email Notifications**: Gmail SMTP integration for notifications

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

**`user_limits`** - User Configuration
```sql
- user_id (PRIMARY KEY)
- team, person
- daily_request_limit, monthly_request_limit
- administrative_safe
- created_at, updated_at
```

**`bedrock_requests`** - Individual Request Records
```sql
- id (AUTO_INCREMENT PRIMARY KEY)
- user_id, team, person, request_timestamp
- model_id, request_id, source_ip, user_agent
- aws_region, response_status, error_message
- processing_time_ms, created_at
```

**`user_blocking_status`** - Current Blocking Status
```sql
- user_id (PRIMARY KEY)
- is_blocked, blocked_reason, blocked_at, blocked_until
- requests_at_blocking, last_request_at
- last_reset_at, created_at, updated_at
```

**`blocking_audit_log`** - Complete Audit Trail
```sql
- id (AUTO_INCREMENT PRIMARY KEY)
- user_id, operation_type, operation_reason
- performed_by, operation_timestamp
- daily_requests_at_operation, daily_limit_at_operation
- usage_percentage, iam_policy_updated, email_sent
- created_at
```

## 🔄 System Workflows

### User Request Processing Flow

```
1. User makes Bedrock API call
   ↓
2. CloudTrail captures the event
   ↓
3. EventBridge triggers Lambda (bedrock-realtime-request-logger)
   ↓
4. Lambda processes event:
   - Extracts user information from IAM tags
   - Logs request to RDS MySQL
   - Checks user limits via stored procedures
   - Evaluates blocking conditions
   ↓
5. If limits exceeded:
   - Check for administrative protection
   - If no protection: trigger blocking workflow
   - Send notifications (email + SNS)
   ↓
6. IAM policies modified for blocking
   ↓
7. User is blocked/warned as appropriate
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
   - Update user_blocking_status table
   - Log to blocking_audit_log
   - Remove IAM deny policies
   - Send unblocking email notifications
   ↓
5. Send comprehensive daily summary notifications
```

## 🛡️ Security & Permissions

### IAM Roles and Policies

#### Dashboard Access Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "rds:DescribeDBInstances",
        "rds-db:connect"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Lambda Execution Roles
- **bedrock-realtime-request-logger-role**: RDS, SNS, IAM, SES permissions
- **bedrock-mysql-query-executor-role**: RDS connection permissions
- **bedrock-daily-reset-role**: RDS, IAM, SNS, SES permissions

#### User Bedrock Policies
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.anthropic.claude-*",
        "arn:aws:bedrock:eu-west-1:701055077130:inference-profile/eu.amazon.nova-*"
      ]
    }
  ]
}
```

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

### Email Notifications

**Gmail SMTP Integration** (`bedrock_email_service.py`):
- **Warning Emails**: Professional HTML templates
- **Blocking Notifications**: Detailed reason and duration
- **Unblocking Confirmations**: Admin action confirmations
- **Daily Summaries**: Usage and cost reports
- **Error Notifications**: System issue alerts

## 💰 Cost Management

### Cost Tracking Features

1. **Real-time Cost Calculation**: Based on token usage and model pricing
2. **Daily/Monthly Budgets**: Configurable per user and team
3. **Cost Alerts**: Automatic notifications when budgets exceeded
4. **Historical Analysis**: Cost trends and projections
5. **Model Comparison**: Cost efficiency analysis across models

### Pricing Configuration

Model pricing stored in RDS MySQL:
```sql
-- Example pricing data
INSERT INTO model_pricing VALUES
('anthropic.claude-3-opus-20240229-v1:0', 'Claude 3 Opus', 0.015000, 0.075000),
('anthropic.claude-3-sonnet-20240229-v1:0', 'Claude 3 Sonnet', 0.003000, 0.015000),
('anthropic.claude-3-haiku-20240307-v1:0', 'Claude 3 Haiku', 0.000250, 0.001250);
```

## 🔧 Configuration Management

### Main Configuration Files

#### `src/config.json` - AWS Configuration
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

#### `quota_config.json` - User/Team Quotas
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

### Environment Variables

**Lambda Environment Variables**:
- `AWS_REGION`: AWS region (eu-west-1)
- `ACCOUNT_ID`: AWS account ID (701055077130)
- `RDS_ENDPOINT`: MySQL RDS endpoint
- `RDS_USERNAME`: Database username
- `RDS_PASSWORD`: Database password
- `RDS_DATABASE`: Database name
- `SNS_TOPIC_ARN`: SNS topic for notifications

## 🧪 Testing & Quality Assurance

### Test Suite

**Automated Tests**:
- Unit tests for all Lambda functions
- Integration tests for dashboard functionality
- End-to-end blocking workflow tests
- Database connection and query tests

**Test Files**:
- `test_enhanced_blocking.py` - Blocking system tests
- `test_email_service.py` - Email notification tests
- Various payload test files for Lambda functions

### Quality Checks

**Code Quality**:
- Python code formatting and linting
- JavaScript code quality checks
- Security scanning for vulnerabilities
- Database query optimization

## 📈 Performance & Scalability

### Performance Optimizations

1. **Database Optimizations**:
   - Optimized indexes for common queries
   - Connection pooling in Lambda functions
   - Efficient query patterns

2. **Lambda Optimizations**:
   - Connection pooling for database connections
   - Proper error handling and retry logic
   - Efficient event processing

3. **Caching Strategy**:
   - Lambda function warm-up
   - Database connection reuse
   - Browser caching for dashboard assets

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

### Backup & Recovery

**Data Backup**:
- RDS automated backups with 7-day retention
- Lambda function code versioning
- Configuration file version control

**Disaster Recovery**:
- Multi-AZ RDS deployment
- Infrastructure as Code for rapid rebuilding
- Documented recovery procedures

## 🚀 Future Enhancements

### Planned Features

**Short Term (1-3 months)**:
- [ ] Mobile-responsive dashboard improvements
- [ ] Advanced cost analytics and forecasting
- [ ] Integration with AWS Cost Explorer
- [ ] Slack/Teams notification integration

**Medium Term (3-6 months)**:
- [ ] Machine learning for usage prediction
- [ ] Advanced user behavior analytics
- [ ] Multi-region deployment support
- [ ] API Gateway for external integrations

**Long Term (6+ months)**:
- [ ] AI-powered anomaly detection
- [ ] Advanced reporting and business intelligence
- [ ] Integration with enterprise identity providers
- [ ] Custom model fine-tuning cost tracking

### Technical Improvements

- Enhanced dashboard with real-time updates
- Advanced analytics and reporting features
- Improved email templates and notification system
- Enhanced security and compliance features

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

- Check the Installation Manual for detailed setup instructions
- Review CloudWatch logs for error messages
- Use the test scripts to verify system functionality
- Contact the development team for complex issues

---

**Last Updated**: September 2025  
**Version**: 3.0.0 (RDS MySQL Architecture)  
**Maintainer**: AWS Bedrock Usage Control System Team

## 📝 Recent Changes

### Version 3.0.0 - RDS MySQL Migration
- **Complete Architecture Migration**: Migrated from DynamoDB to RDS MySQL for unified data storage
- **Updated Lambda Functions**: All Lambda functions now use RDS MySQL with PyMySQL
- **Enhanced Daily Reset**: Re-engineered daily reset functionality for RDS MySQL
- **Improved Email Service**: Gmail SMTP integration with professional templates
- **CET Timezone Support**: All operations properly handle Central European Time
- **Comprehensive Audit Trail**: Complete blocking and unblocking audit in RDS MySQL
- **Removed Obsolete Functions**: Cleaned up outdated DynamoDB-based Lambda functions
- **Updated Documentation**: Complete documentation refresh to reflect current architecture
