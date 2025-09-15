#!/bin/bash

# Launch the AWS Bedrock Usage Dashboard
echo "Launching AWS Bedrock Usage Dashboard..."

# Determine the OS and open the login page in the default browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open login.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open login.html
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    start login.html
else
    echo "Unsupported operating system. Please open login.html manually in your browser."
    exit 1
fi

echo "Dashboard login page opened in your default browser."
echo "Please enter your AWS credentials to access the dashboard."
