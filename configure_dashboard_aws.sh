#!/bin/bash

# =============================================================================
# AWS Bedrock Usage Dashboard - AWS Integration Configuration
# =============================================================================
# This script configures the dashboard to work with the AWS environment
# and sets up the necessary permissions and CloudWatch metrics
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

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}AWS Bedrock Usage Dashboard - AWS Integration Configuration${NC}"
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
# STEP 1: Create CloudWatch Custom Metrics
# =============================================================================
echo -e "${BLUE}STEP 1: Setting up CloudWatch Custom Metrics${NC}"
echo "----------------------------------------------"

print_status "Creating CloudWatch custom metrics for dashboard..."

# Create a sample metric to ensure the namespace exists
aws cloudwatch put-metric-data \
    --namespace "UserMetrics" \
    --metric-data MetricName=BedrockUsage,Value=0,Unit=Count,Dimensions=[{Name=User,Value=dashboard-init}] \
    --region $REGION

aws cloudwatch put-metric-data \
    --namespace "TeamMetrics" \
    --metric-data MetricName=BedrockUsage,Value=0,Unit=Count,Dimensions=[{Name=Team,Value=dashboard-init}] \
    --region $REGION

print_status "CloudWatch custom metrics namespace initialized"

# =============================================================================
# STEP 2: Create IAM Role for Dashboard Access
# =============================================================================
echo -e "${BLUE}STEP 2: Creating IAM Role for Dashboard Access${NC}"
echo "-----------------------------------------------"

DASHBOARD_ROLE_NAME="bedrock-dashboard-access-role"
print_status "Creating IAM role: $DASHBOARD_ROLE_NAME"

# Trust policy for the dashboard role (allows assumption by users)
cat > /tmp/dashboard-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::$ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "bedrock-dashboard-access"
        }
      }
    }
  ]
}
EOF

# Check if role exists
if aws iam get-role --role-name $DASHBOARD_ROLE_NAME > /dev/null 2>&1; then
    print_warning "Role $DASHBOARD_ROLE_NAME already exists. Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name $DASHBOARD_ROLE_NAME \
        --policy-document file:///tmp/dashboard-trust-policy.json
else
    aws iam create-role \
        --role-name $DASHBOARD_ROLE_NAME \
        --assume-role-policy-document file:///tmp/dashboard-trust-policy.json \
        --description "Role for Bedrock Usage Dashboard access"
    
    print_status "Role $DASHBOARD_ROLE_NAME created successfully!"
fi

# Policy for dashboard access
cat > /tmp/dashboard-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListUsers",
        "iam:GetUser",
        "iam:ListUserTags",
        "iam:GetGroup",
        "iam:ListGroupsForUser"
      ],
      "Resource": [
        "arn:aws:iam::$ACCOUNT_ID:user/*",
        "arn:aws:iam::$ACCOUNT_ID:group/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-policy-manager",
        "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:bedrock-blocking-history"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/bedrock_user_daily_usage"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $DASHBOARD_ROLE_NAME \
    --policy-name "BedrockDashboardAccessPolicy" \
    --policy-document file:///tmp/dashboard-policy.json

print_status "Policy attached to $DASHBOARD_ROLE_NAME successfully!"

# Clean up temporary files
rm -f /tmp/dashboard-trust-policy.json /tmp/dashboard-policy.json

# =============================================================================
# STEP 3: Create Dashboard Configuration File
# =============================================================================
echo -e "${BLUE}STEP 3: Creating Dashboard Configuration${NC}"
echo "----------------------------------------"

print_status "Creating dashboard configuration file..."

cat > dashboard_config.json << EOF
{
  "aws": {
    "region": "$REGION",
    "account_id": "$ACCOUNT_ID",
    "dashboard_role_arn": "arn:aws:iam::$ACCOUNT_ID:role/$DASHBOARD_ROLE_NAME",
    "external_id": "bedrock-dashboard-access"
  },
  "cloudwatch": {
    "user_metrics_namespace": "UserMetrics",
    "team_metrics_namespace": "TeamMetrics",
    "metric_name": "BedrockUsage"
  },
  "lambda_functions": {
    "policy_manager": "bedrock-policy-manager",
    "blocking_history": "bedrock-blocking-history"
  },
  "teams": [
    "team_darwin_group",
    "team_sap_group", 
    "team_mulesoft_group",
    "team_yo_leo_gas_group",
    "team_lcorp_group"
  ],
  "quotas": {
    "users": {
      "team_darwin_usr_001": {
        "monthly_limit": 3500,
        "daily_limit": 150,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "yo_leo_gas_001": {
        "monthly_limit": 3500,
        "daily_limit": 150,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_sap_usr_001": {
        "monthly_limit": 3000,
        "daily_limit": 120,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_sap_usr_002": {
        "monthly_limit": 3000,
        "daily_limit": 120,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_mulesoft_usr_001": {
        "monthly_limit": 2500,
        "daily_limit": 100,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_mulesoft_usr_002": {
        "monthly_limit": 2500,
        "daily_limit": 100,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_yp_leo_gas_usr_001": {
        "monthly_limit": 4000,
        "daily_limit": 160,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_yp_leo_gas_usr_002": {
        "monthly_limit": 4000,
        "daily_limit": 160,
        "warning_threshold": 60,
        "critical_threshold": 85
      }
    },
    "teams": {
      "team_darwin_group": {
        "monthly_limit": 25000,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_sap_group": {
        "monthly_limit": 20000,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_mulesoft_group": {
        "monthly_limit": 15000,
        "warning_threshold": 60,
        "critical_threshold": 85
      },
      "team_yo_leo_gas_group": {
        "monthly_limit": 30000,
        "warning_threshold": 60,
        "critical_threshold": 85
      }
    }
  }
}
EOF

print_status "Dashboard configuration created: dashboard_config.json"

# =============================================================================
# STEP 4: Create Lambda Function for Dashboard Backend
# =============================================================================
echo -e "${BLUE}STEP 4: Creating Dashboard Backend Lambda${NC}"
echo "--------------------------------------------"

print_status "Creating bedrock-blocking-history Lambda function..."

# Check if the function already exists
FUNCTION_NAME="bedrock-blocking-history"
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
    print_warning "Function $FUNCTION_NAME already exists. Updating..."
    
    # Create deployment package
    cd individual_blocking_system/lambda_functions
    zip -r ../../bedrock-blocking-history.zip bedrock_blocking_history.py > /dev/null
    cd ../..
    
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://bedrock-blocking-history.zip \
        --region $REGION > /dev/null
    
    rm bedrock-blocking-history.zip
    print_status "Function $FUNCTION_NAME updated successfully"
else
    print_status "Creating new function $FUNCTION_NAME..."
    
    # Create IAM role for the function
    HISTORY_ROLE_NAME="bedrock-blocking-history-role"
    
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

    if ! aws iam get-role --role-name $HISTORY_ROLE_NAME > /dev/null 2>&1; then
        aws iam create-role \
            --role-name $HISTORY_ROLE_NAME \
            --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
            --description "Role for bedrock-blocking-history Lambda function"
    fi

    # Policy for the function
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
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/bedrock_user_daily_usage"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $HISTORY_ROLE_NAME \
        --policy-name "BedrockBlockingHistoryPolicy" \
        --policy-document file:///tmp/history-policy.json

    # Create deployment package
    cd individual_blocking_system/lambda_functions
    zip -r ../../bedrock-blocking-history.zip bedrock_blocking_history.py > /dev/null
    cd ../..
    
    # Wait for role to be ready
    sleep 10
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role "arn:aws:iam::$ACCOUNT_ID:role/$HISTORY_ROLE_NAME" \
        --handler bedrock_blocking_history.lambda_handler \
        --zip-file fileb://bedrock-blocking-history.zip \
        --timeout 60 \
        --memory-size 256 \
        --environment Variables="{
            ACCOUNT_ID=$ACCOUNT_ID,
            DYNAMODB_TABLE=bedrock_user_daily_usage
        }" \
        --region $REGION > /dev/null
    
    rm bedrock-blocking-history.zip
    rm -f /tmp/lambda-trust-policy.json /tmp/history-policy.json
    print_status "Function $FUNCTION_NAME created successfully"
fi

# =============================================================================
# STEP 5: Update Dashboard HTML with AWS Configuration
# =============================================================================
echo -e "${BLUE}STEP 5: Updating Dashboard Configuration${NC}"
echo "----------------------------------------"

print_status "Creating updated dashboard with AWS integration..."

# Create a backup of the original dashboard
cp bedrock_usage_dashboard.html bedrock_usage_dashboard_backup.html

# Create the updated dashboard configuration script
cat > dashboard_aws_config.js << 'EOF'
// AWS Configuration for Bedrock Usage Dashboard
const AWS_CONFIG = {
    region: 'eu-west-1',
    account_id: '701055077130',
    dashboard_role_arn: 'arn:aws:iam::701055077130:role/bedrock-dashboard-access-role',
    external_id: 'bedrock-dashboard-access'
};

// Configure AWS SDK with STS for role assumption
function configureAWSWithRole(accessKey, secretKey) {
    // First configure with user credentials
    AWS.config.update({
        region: AWS_CONFIG.region,
        credentials: new AWS.Credentials({
            accessKeyId: accessKey,
            secretAccessKey: secretKey
        })
    });
    
    // Then assume the dashboard role
    const sts = new AWS.STS();
    const params = {
        RoleArn: AWS_CONFIG.dashboard_role_arn,
        RoleSessionName: 'bedrock-dashboard-session',
        ExternalId: AWS_CONFIG.external_id,
        DurationSeconds: 3600 // 1 hour
    };
    
    return sts.assumeRole(params).promise().then(data => {
        // Update AWS config with assumed role credentials
        AWS.config.update({
            credentials: new AWS.Credentials({
                accessKeyId: data.Credentials.AccessKeyId,
                secretAccessKey: data.Credentials.SecretAccessKey,
                sessionToken: data.Credentials.SessionToken
            })
        });
        
        console.log('Successfully assumed dashboard role');
        return true;
    }).catch(error => {
        console.error('Error assuming dashboard role:', error);
        throw error;
    });
}

// Enhanced CloudWatch metrics fetching
async function fetchRealCloudWatchMetrics(metricName, dimension, startTime, endTime, namespace = 'UserMetrics', dimensionName = 'User') {
    const cloudwatch = new AWS.CloudWatch();
    
    const params = {
        MetricName: metricName,
        Namespace: namespace,
        Dimensions: [
            {
                Name: dimensionName,
                Value: dimension
            }
        ],
        StartTime: startTime,
        EndTime: endTime,
        Period: 86400, // 1 day
        Statistics: ['Sum']
    };
    
    try {
        const data = await cloudwatch.getMetricStatistics(params).promise();
        
        let total = 0;
        if (data.Datapoints && data.Datapoints.length > 0) {
            data.Datapoints.forEach(datapoint => {
                total += datapoint.Sum || 0;
            });
        }
        
        return { total, datapoints: data.Datapoints || [] };
    } catch (error) {
        console.error(`Error fetching metrics for ${dimension}:`, error);
        return { total: 0, datapoints: [] };
    }
}

// Enhanced user fetching from IAM
async function fetchRealUsersFromIAM() {
    const iam = new AWS.IAM();
    
    try {
        const teams = [
            'team_darwin_group',
            'team_sap_group',
            'team_mulesoft_group',
            'team_yo_leo_gas_group',
            'team_lcorp_group'
        ];
        
        const allUsers = [];
        const usersByTeam = {};
        const userTags = {};
        
        // Initialize teams
        teams.forEach(team => {
            usersByTeam[team] = [];
        });
        
        // Fetch users for each team
        for (const team of teams) {
            try {
                const groupResponse = await iam.getGroup({ GroupName: team }).promise();
                
                for (const user of groupResponse.Users) {
                    const username = user.UserName;
                    
                    // Add user to team
                    usersByTeam[team].push(username);
                    
                    // Add to overall list if not already there
                    if (!allUsers.includes(username)) {
                        allUsers.push(username);
                    }
                    
                    // Fetch user tags
                    try {
                        const tagsResponse = await iam.listUserTags({ UserName: username }).promise();
                        const tags = {};
                        
                        tagsResponse.Tags.forEach(tag => {
                            tags[tag.Key] = tag.Value;
                        });
                        
                        userTags[username] = tags;
                    } catch (tagError) {
                        console.error(`Error fetching tags for user ${username}:`, tagError);
                        userTags[username] = {};
                    }
                }
            } catch (groupError) {
                console.error(`Error fetching users for team ${team}:`, groupError);
            }
        }
        
        return { allUsers, usersByTeam, userTags };
    } catch (error) {
        console.error('Error fetching users from IAM:', error);
        throw error;
    }
}
EOF

print_status "Dashboard AWS configuration created: dashboard_aws_config.js"

# =============================================================================
# STEP 6: Create Launch Script
# =============================================================================
echo -e "${BLUE}STEP 6: Creating Dashboard Launch Script${NC}"
echo "----------------------------------------"

cat > launch_dashboard_aws.sh << 'EOF'
#!/bin/bash

# =============================================================================
# Launch Bedrock Usage Dashboard with AWS Integration
# =============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}Launching AWS Bedrock Usage Dashboard${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Please install Python to run the dashboard."
    exit 1
fi

# Start HTTP server
PORT=8080
echo -e "${GREEN}Starting dashboard server on port $PORT...${NC}"
echo -e "${GREEN}Dashboard will be available at: http://localhost:$PORT${NC}"
echo ""
echo -e "${BLUE}Instructions:${NC}"
echo "1. Open your browser and go to http://localhost:$PORT"
echo "2. You will be redirected to the login page"
echo "3. Enter your AWS credentials (Access Key ID and Secret Access Key)"
echo "4. The dashboard will load with real AWS data"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
$PYTHON_CMD -m http.server $PORT
EOF

chmod +x launch_dashboard_aws.sh

print_status "Dashboard launch script created: launch_dashboard_aws.sh"

echo ""

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}DASHBOARD AWS INTEGRATION COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "${GREEN}✅ Created Resources:${NC}"
echo "   • IAM Role: $DASHBOARD_ROLE_NAME"
echo "   • Lambda Function: bedrock-blocking-history (updated/created)"
echo "   • CloudWatch Custom Metrics: UserMetrics, TeamMetrics"
echo "   • Dashboard Configuration: dashboard_config.json"
echo "   • AWS Integration Script: dashboard_aws_config.js"
echo "   • Launch Script: launch_dashboard_aws.sh"
echo ""
echo -e "${BLUE}🚀 How to Launch the Dashboard:${NC}"
echo "   1. Run: ./launch_dashboard_aws.sh"
echo "   2. Open browser: http://localhost:8080"
echo "   3. Login with your AWS credentials"
echo "   4. Dashboard will load real AWS data"
echo ""
echo -e "${BLUE}📋 Dashboard Features:${NC}"
echo "   • Real-time user and team consumption data"
echo "   • CloudWatch metrics integration"
echo "   • User blocking management"
echo "   • Historical usage tracking"
echo "   • Automated alerts and notifications"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "   • Users need IAM permissions to assume the dashboard role"
echo "   • The dashboard uses STS to assume roles for secure access"
echo "   • All data is fetched in real-time from AWS services"
echo "   • CloudWatch metrics may take a few minutes to appear"
echo ""
echo -e "${GREEN}Configuration completed at: $(date)${NC}"
