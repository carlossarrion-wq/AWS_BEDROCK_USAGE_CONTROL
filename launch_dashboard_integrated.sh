#!/bin/bash

# =============================================================================
# Launch AWS Bedrock Usage Dashboard - Integrated Version
# =============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}AWS Bedrock Usage Dashboard - Integrated Launch${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found. Please install Python to run the dashboard.${NC}"
    exit 1
fi

# Check if login.html exists
if [ ! -f "login.html" ]; then
    echo -e "${YELLOW}Warning: login.html not found. Creating a basic login page...${NC}"
    
    cat > login.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Bedrock Dashboard - Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 400px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1e4a72;
            margin-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .form-group input:focus {
            outline: none;
            border-color: #1e4a72;
            box-shadow: 0 0 0 2px rgba(30, 74, 114, 0.25);
        }
        .login-button {
            width: 100%;
            padding: 12px;
            background-color: #1e4a72;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .login-button:hover {
            background-color: #2d5aa0;
        }
        .error-message {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #f56565;
        }
        .info-message {
            background-color: #e6fffa;
            color: #0c5460;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <h1>AWS Bedrock Dashboard</h1>
            <p>Please enter your AWS credentials</p>
        </div>
        
        <div id="error-container"></div>
        
        <form id="login-form">
            <div class="form-group">
                <label for="access-key">AWS Access Key ID:</label>
                <input type="text" id="access-key" name="access-key" required>
            </div>
            
            <div class="form-group">
                <label for="secret-key">AWS Secret Access Key:</label>
                <input type="password" id="secret-key" name="secret-key" required>
            </div>
            
            <button type="submit" class="login-button">Login to Dashboard</button>
        </form>
        
        <div class="info-message" style="margin-top: 20px;">
            <strong>Note:</strong> Your credentials are stored locally in your browser session and are used to assume a dashboard role for secure access to AWS services.
        </div>
    </div>

    <script>
        // Check for error parameter in URL
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        
        if (error) {
            const errorContainer = document.getElementById('error-container');
            let errorMessage = '';
            
            switch(error) {
                case 'no_credentials':
                    errorMessage = 'No credentials found. Please login again.';
                    break;
                case 'invalid_credentials':
                    errorMessage = 'Invalid AWS credentials. Please check your Access Key ID and Secret Access Key.';
                    break;
                default:
                    errorMessage = 'An error occurred. Please try again.';
            }
            
            errorContainer.innerHTML = `
                <div class="error-message">
                    <strong>Error:</strong> ${errorMessage}
                </div>
            `;
        }
        
        // Handle form submission
        document.getElementById('login-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const accessKey = document.getElementById('access-key').value.trim();
            const secretKey = document.getElementById('secret-key').value.trim();
            
            if (!accessKey || !secretKey) {
                document.getElementById('error-container').innerHTML = `
                    <div class="error-message">
                        <strong>Error:</strong> Please enter both Access Key ID and Secret Access Key.
                    </div>
                `;
                return;
            }
            
            // Store credentials in session storage
            sessionStorage.setItem('aws_access_key', accessKey);
            sessionStorage.setItem('aws_secret_key', secretKey);
            
            // Redirect to dashboard
            window.location.href = 'bedrock_usage_dashboard_aws.html';
        });
    </script>
</body>
</html>
EOF
    echo -e "${GREEN}✅ Created basic login page${NC}"
fi

# Start HTTP server
PORT=8080
echo -e "${GREEN}Starting dashboard server on port $PORT...${NC}"
echo -e "${GREEN}Dashboard will be available at: http://localhost:$PORT${NC}"
echo ""
echo -e "${BLUE}Instructions:${NC}"
echo "1. Open your browser and go to http://localhost:$PORT"
echo "2. You will see the login page"
echo "3. Enter your AWS credentials (Access Key ID and Secret Access Key)"
echo "4. The dashboard will load with real AWS data from your environment"
echo ""
echo -e "${YELLOW}Features Available:${NC}"
echo "• Real-time user and team consumption monitoring"
echo "• CloudWatch metrics integration"
echo "• IAM user and group management"
echo "• Usage alerts and notifications"
echo "• Historical usage tracking"
echo "• Blocking management (requires full infrastructure deployment)"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "• Your AWS credentials are stored securely in browser session storage"
echo "• The dashboard assumes a role for secure access to AWS services"
echo "• For full blocking functionality, run the infrastructure setup scripts"
echo "• CloudWatch metrics may take a few minutes to appear for new users"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
$PYTHON_CMD -m http.server $PORT
