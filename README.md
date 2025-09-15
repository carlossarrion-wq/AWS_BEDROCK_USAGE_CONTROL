# AWS Bedrock Usage Control

This project provides a comprehensive solution for controlling and monitoring AWS Bedrock usage across teams and users. It allows you to create and manage users, groups, roles, and policies for controlling access to AWS Bedrock services, with a focus on Claude and Nova Pro models.

## Project Overview

The solution includes:

1. **IAM Setup**: Groups, users, roles, and policies for team-based access control
2. **Bedrock Inference Profiles**: System-defined profiles for Claude and Nova models
3. **IAM Policies**: Team-specific and user-specific access policies with appropriate permissions
4. **Monitoring and Alerting**: CloudWatch metrics, AWS Budgets, and SNS notifications
5. **API Key Management**: Tool-specific API keys with appropriate tagging

## Project Structure

```
.
├── src/                      # Source code for the main implementation
│   ├── user/                 # User management module
│   ├── group/                # Group management module
│   ├── policy/               # Policy management module
│   ├── dashboard/            # Dashboard module
│   ├── utils/                # Utility functions
│   ├── config.json           # Configuration file
│   └── bedrock_manager.py    # Main CLI script
├── poc/                      # Proof of Concept implementation
└── README.md                 # This file
```

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- AWS account with access to Bedrock service
- Python 3.9 or later
- Account ID and region configured in `src/config.json`

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/aws_bedrock_usage_control.git
   cd aws_bedrock_usage_control
   ```

2. Install required Python packages:
   ```bash
   pip install boto3
   ```

3. Update the configuration in `src/config.json` with your AWS account ID and region.

## Usage

The project provides a command-line interface for managing AWS Bedrock usage control. The main script is `src/bedrock_manager.py`.

### User Management

Create a new user:
```bash
python src/bedrock_manager.py user create <username> "<person_name>" <team_name>
```

Delete a user:
```bash
python src/bedrock_manager.py user delete <username>
```

Get information about a user:
```bash
python src/bedrock_manager.py user info <username>
```

List all users:
```bash
python src/bedrock_manager.py user list
```

List users in a specific team:
```bash
python src/bedrock_manager.py user list --team <team_name>
```

Create an API key for a user with a tool tag:
```bash
python src/bedrock_manager.py user create-key <username> <tool_name>
```

### Group Management

Create a new group:
```bash
python src/bedrock_manager.py group create <team_name>
```

Delete a group:
```bash
python src/bedrock_manager.py group delete <team_name>
```

Get information about a group:
```bash
python src/bedrock_manager.py group info <team_name>
```

List all groups:
```bash
python src/bedrock_manager.py group list
```

Set up a team with group, role, and policies:
```bash
python src/bedrock_manager.py group setup <team_name>
```

### Policy Management

Create a policy:
```bash
python src/bedrock_manager.py policy create <policy_name> <policy_file>
```

Delete a policy:
```bash
python src/bedrock_manager.py policy delete <policy_name>
```

Get information about a policy:
```bash
python src/bedrock_manager.py policy info <policy_name>
```

Attach a policy to a user:
```bash
python src/bedrock_manager.py policy attach <policy_name> --user <username>
```

Attach a policy to a role:
```bash
python src/bedrock_manager.py policy attach <policy_name> --role <role_name>
```

## Sample Use Case: Provisioning a New User

To provision a new user, follow these steps:

1. Create a new user and assign them to a team:
   ```bash
   python src/bedrock_manager.py user create new_user "John Doe" team_darwin
   ```

   This command will:
   - Create the group if it doesn't exist
   - Create the roles for the group
   - Create the user and assign the user to the group
   - Assign policies at the requested levels: role, group, user

2. Create an API key for the user with a tool tag:
   ```bash
   python src/bedrock_manager.py user create-key new_user Jupyter
   ```

   This command will:
   - Create an API key for the user
   - Tag the API key with the tool name
   - Create and attach a tool-specific policy
   - Save the credentials to a file

## Resource Structure

### For Each Team

- **IAM Group**: team_name_group
- **IAM Role**: team_name_BedrockRole
- **IAM Policies**:
  - team_name_BedrockPolicy
  - team_name_AssumeRolePolicy

### For Each User

- **IAM User**: username
- **IAM Policies**:
  - username_BedrockPolicy
  - username_tool_name_Policy (for each tool)

### Shared Resources

- CloudWatch Log Group: /aws/bedrock/user_usage
- CloudWatch Log Group: /aws/bedrock/team_usage
- CloudWatch Metric Filters
- SNS Topic: bedrock-usage-alerts
- AWS Budgets

## Monitoring and Usage Control

The solution implements several monitoring and control mechanisms:

### 1. CloudWatch Metrics and Logging

- Dedicated CloudWatch log groups
- Metric filters for each team and user that track usage

### 2. AWS Budgets for Usage Tracking

- Budget for each team with a configurable limit
- Team tags used to filter and track usage

### 3. Alerting System

- SNS topic for notifications
- Budget alerts when usage exceeds the warning threshold
- CloudWatch alarms that trigger when a team approaches their usage limit

### 4. Access Control

- Role-based access control with team-specific roles
- Team-specific and user-specific policies that limit access to specific inference profiles
- User tagging for team identification
- Tool tagging for API keys

## Security Considerations

- Temporary passwords with reset required on first login
- Principle of least privilege applied to IAM policies
- Team-based access control with role assumption
- Resource-specific permissions for Bedrock actions
- Tool-specific API keys with appropriate tagging

## Troubleshooting

If you encounter permission errors when using Bedrock services, check:

1. The IAM policy attached to the user or role
2. The permissions for specific Bedrock actions (e.g., `bedrock:InvokeModelWithResponseStream`, `bedrock:CallWithBearerToken`)
3. The resource ARNs in the policy to ensure they match the inference profiles being used

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
