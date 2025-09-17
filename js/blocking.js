// Blocking Management Functions for AWS Bedrock Usage Dashboard

// Blocking management functions - Real Lambda integration
async function loadBlockingData() {
    if (!isConnectedToAWS) {
        showBlockingError('Not connected to AWS. Please refresh the page and login again.');
        return;
    }
    
    try {
        console.log('Loading blocking management data...');
        showBlockingLoadingIndicators();
        
        // Load real blocking data from Lambda functions
        await loadUserBlockingStatus();
        await loadBlockingOperationsHistory();
        
        console.log('Blocking data loaded successfully');
        
    } catch (error) {
        console.error('Error loading blocking data:', error);
        showBlockingError('Failed to load blocking management data: ' + error.message);
    }
}

async function loadUserBlockingStatus() {
    const statusTableBody = document.querySelector('#user-blocking-status-table tbody');
    statusTableBody.innerHTML = '';
    
    // Populate user select dropdown
    const userSelect = document.getElementById('user-select');
    userSelect.innerHTML = '<option value="">Select User...</option>';
    
    // Use real user data from IAM
    const sortedUsers = [...allUsers].sort();
    
    for (const username of sortedUsers) {
        const personTag = getUserPersonTag(username) || "Unknown";
        
        let userTeam = "Unknown";
        for (const team in usersByTeam) {
            if (usersByTeam[team].includes(username)) {
                userTeam = team;
                break;
            }
        }
        
        // Add to select dropdown
        userSelect.innerHTML += `<option value="${username}">${username} - ${personTag}</option>`;
        
        // Get blocking status from Lambda function
        let isBlocked = false;
        let blockType = 'None';
        let blockedSince = '-';
        let expires = '-';
        let hasAdminProtection = false;
        
        try {
            // Invoke policy manager to get user status
            const lambda = new AWS.Lambda();
            const params = {
                FunctionName: 'bedrock-policy-manager',
                Payload: JSON.stringify({
                    action: 'check_status',
                    user_id: username
                })
            };
            
            const result = await lambda.invoke(params).promise();
            const response = JSON.parse(result.Payload);
            
            if (response.statusCode === 200) {
                const data = JSON.parse(response.body);
                isBlocked = data.is_blocked || false;
                blockType = data.block_type || 'None';
                
                // Format blocked_since date with seconds
                if (data.blocked_since) {
                    blockedSince = formatDateTime(data.blocked_since, true);
                } else {
                    blockedSince = '-';
                }
                
                // Format expires_at date with seconds (same format as blocked_since)
                if (data.expires_at && data.expires_at !== 'Indefinite') {
                    expires = formatDateTime(data.expires_at, true);
                } else {
                    expires = 'Indefinite';
                }
            }
        } catch (error) {
            console.error(`Error getting status for user ${username}:`, error);
            // Continue with default values
        }
        
        // Check for administrative protection by querying DynamoDB directly
        try {
            const dynamodb = new AWS.DynamoDB.DocumentClient();
            const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
            
            const params = {
                TableName: 'bedrock_user_daily_usage',
                Key: {
                    'user_id': username,
                    'date': today
                }
            };
            
            const result = await dynamodb.get(params).promise();
            if (result.Item && result.Item.admin_protection === true) {
                hasAdminProtection = true;
                console.log(`User ${username} has administrative protection`);
            }
        } catch (error) {
            console.error(`Error checking admin protection for user ${username}:`, error);
            // Continue without admin protection info
        }
        
        // Store blocking status for dynamic button
        userBlockingStatus[username] = isBlocked;
        
        const userQuota = quotaConfig?.users?.[username] || {
            daily_limit: 150,
            warning_threshold: 60, 
            critical_threshold: 85 
        };
        
        const dailyUsage = userMetrics[username]?.daily?.[8] || 0;
        const dailyLimit = userQuota.daily_limit;
        const dailyPercentage = Math.round((dailyUsage / dailyLimit) * 100);
        
        let dailyColorClass = '';
        if (dailyPercentage > userQuota.critical_threshold) {
            dailyColorClass = 'critical';
        } else if (dailyPercentage > userQuota.warning_threshold) {
            dailyColorClass = 'warning';
        }
        
        let statusBadge = `<span class="status-badge active">Active</span>`;
        let rowClass = '';
        
        if (isBlocked) {
            // Determine if it's an admin block by checking the reason or performed_by
            let isAdminBlock = false;
            try {
                // Check DynamoDB for additional context about the block
                const dynamodb = new AWS.DynamoDB.DocumentClient();
                const today = new Date().toISOString().split('T')[0];
                
                const dbParams = {
                    TableName: 'bedrock_user_daily_usage',
                    Key: {
                        'user_id': username,
                        'date': today
                    }
                };
                
                const dbResult = await dynamodb.get(dbParams).promise();
                if (dbResult.Item) {
                    const adminProtectionBy = dbResult.Item.admin_protection_by;
                    
                    // Check if it's an admin block: admin_protection_by exists and is not 'system'
                    isAdminBlock = adminProtectionBy && adminProtectionBy !== 'system';
                }
            } catch (error) {
                console.error(`Error checking admin block status for ${username}:`, error);
                // Fallback: assume regular block if we can't determine
                isAdminBlock = false;
            }
            
            if (isAdminBlock) {
                statusBadge = `<span class="status-badge blocked">Blocked Admin</span>`;
            } else {
                statusBadge = `<span class="status-badge blocked">Blocked</span>`;
            }
            rowClass = 'blocked-user';
        } else if (hasAdminProtection) {
            statusBadge = `<span class="status-badge active-admin">Active Admin</span>`;
            rowClass = '';
        }
        
        statusTableBody.innerHTML += `
            <tr class="${rowClass}">
                <td>${username}</td>
                <td>${personTag}</td>
                <td>${userTeam}</td>
                <td>${statusBadge}</td>
                <td>${dailyUsage}</td>
                <td>${dailyLimit}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-bar-fill ${dailyColorClass}" style="width: ${dailyPercentage}%"></div>
                    </div>
                    ${dailyPercentage}%
                </td>
                <td>${blockType}</td>
                <td>${blockedSince}</td>
                <td>${expires}</td>
            </tr>
        `;
    }
    
    if (allUsers.length === 0) {
        statusTableBody.innerHTML = `
            <tr>
                <td colspan="10">No users found</td>
            </tr>
        `;
    }
}

async function loadBlockingOperationsHistory() {
    try {
        // Get all operations history from Lambda function (first time only)
        if (allOperations.length === 0) {
            const lambda = new AWS.Lambda();
            const params = {
                FunctionName: 'bedrock-blocking-history',
                Payload: JSON.stringify({
                    action: 'get_history',
                    limit: 100  // Get more operations for pagination
                })
            };
            
            const result = await lambda.invoke(params).promise();
            const response = JSON.parse(result.Payload);
            
            if (response.statusCode === 200) {
                const data = JSON.parse(response.body);
                const operations = data.operations || [];
                
                // Sort operations by timestamp descending (most recent first)
                allOperations = operations.sort((a, b) => {
                    return new Date(b.timestamp) - new Date(a.timestamp);
                });
                
                operationsTotalCount = allOperations.length;
            } else {
                throw new Error('Failed to load operations history');
            }
        }
        
        // Display current page
        displayOperationsPage();
        
    } catch (error) {
        console.error('Error loading operations history:', error);
        const operationsTableBody = document.querySelector('#blocking-operations-table tbody');
        operationsTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="error-message">
                    Error loading operations history: ${error.message}
                </td>
            </tr>
        `;
        updateOperationsPaginationInfo();
    }
}

// Display current page of operations
function displayOperationsPage() {
    const operationsTableBody = document.querySelector('#blocking-operations-table tbody');
    operationsTableBody.innerHTML = '';
    
    if (allOperations.length === 0) {
        operationsTableBody.innerHTML = `
            <tr>
                <td colspan="6">No operations history found</td>
            </tr>
        `;
        updateOperationsPaginationInfo();
        return;
    }
    
    // Calculate pagination
    const startIndex = (operationsCurrentPage - 1) * PAGINATION_CONFIG.operationsPageSize;
    const endIndex = Math.min(startIndex + PAGINATION_CONFIG.operationsPageSize, allOperations.length);
    const pageOperations = allOperations.slice(startIndex, endIndex);
    
    // Display operations for current page
    pageOperations.forEach(op => {
        const timestamp = formatDateTime(op.timestamp, true);
        const statusBadge = op.status === 'SUCCESS' ? 
            '<span class="status-badge active">Success</span>' : 
            '<span class="status-badge blocked">Failed</span>';
        
        // Get person tag for the user
        const personTag = getUserPersonTag(op.user_id) || 'Unknown';
        
        operationsTableBody.innerHTML += `
            <tr>
                <td>${timestamp}</td>
                <td>${op.user_id || 'Unknown'}</td>
                <td>${personTag}</td>
                <td>${op.operation || 'Unknown'}</td>
                <td>${op.reason || 'No reason provided'}</td>
                <td>${op.performed_by || 'System'}</td>
            </tr>
        `;
    });
    
    // Update pagination info and buttons
    updateOperationsPaginationInfo();
}

// Update pagination information and button states
function updateOperationsPaginationInfo() {
    const totalPages = Math.ceil(operationsTotalCount / PAGINATION_CONFIG.operationsPageSize);
    const startIndex = (operationsCurrentPage - 1) * PAGINATION_CONFIG.operationsPageSize + 1;
    const endIndex = Math.min(operationsCurrentPage * PAGINATION_CONFIG.operationsPageSize, operationsTotalCount);
    
    // Update info text
    document.getElementById('operations-info').textContent = 
        `Showing ${startIndex}-${endIndex} of ${operationsTotalCount} operations`;
    
    // Update page info
    document.getElementById('operations-page-info').textContent = 
        `Page ${operationsCurrentPage} of ${totalPages}`;
    
    // Update button states
    const prevBtn = document.getElementById('prev-operations-btn');
    const nextBtn = document.getElementById('next-operations-btn');
    
    prevBtn.disabled = operationsCurrentPage <= 1;
    nextBtn.disabled = operationsCurrentPage >= totalPages;
    
    // Update button styles
    if (prevBtn.disabled) {
        prevBtn.style.opacity = '0.5';
        prevBtn.style.cursor = 'not-allowed';
    } else {
        prevBtn.style.opacity = '1';
        prevBtn.style.cursor = 'pointer';
    }
    
    if (nextBtn.disabled) {
        nextBtn.style.opacity = '0.5';
        nextBtn.style.cursor = 'not-allowed';
    } else {
        nextBtn.style.opacity = '1';
        nextBtn.style.cursor = 'pointer';
    }
}

// Load previous page of operations
function loadPreviousOperations() {
    if (operationsCurrentPage > 1) {
        operationsCurrentPage--;
        displayOperationsPage();
    }
}

// Load next page of operations
function loadNextOperations() {
    const totalPages = Math.ceil(operationsTotalCount / PAGINATION_CONFIG.operationsPageSize);
    if (operationsCurrentPage < totalPages) {
        operationsCurrentPage++;
        displayOperationsPage();
    }
}

function showBlockingLoadingIndicators() {
    document.querySelector('#user-blocking-status-table tbody').innerHTML = 
        '<tr><td colspan="10"><div class="loading-spinner"></div>Loading user status from Lambda...</td></tr>';
    document.querySelector('#blocking-operations-table tbody').innerHTML = 
        '<tr><td colspan="6"><div class="loading-spinner"></div>Loading operations history from Lambda...</td></tr>';
}

function showBlockingError(message) {
    const statusTable = document.querySelector('#user-blocking-status-table tbody');
    const historyTable = document.querySelector('#blocking-operations-table tbody');
    
    statusTable.innerHTML = `<tr><td colspan="10" class="error-message">${message}</td></tr>`;
    historyTable.innerHTML = `<tr><td colspan="6" class="error-message">${message}</td></tr>`;
}

// Real blocking functions using Lambda
async function performManualBlock() {
    const userSelect = document.getElementById('user-select');
    const blockDuration = document.getElementById('block-duration');
    const blockReason = document.getElementById('block-reason');
    
    const username = userSelect.value;
    const duration = blockDuration.value;
    const reason = blockReason.value;
    
    if (!username) {
        updateConnectionStatus('error', 'Please select a user to block');
        return;
    }
    
    if (!reason) {
        updateConnectionStatus('error', 'Please provide a reason for blocking');
        return;
    }
    
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'block',
                user_id: username,
                reason: reason,
                duration: duration,
                performed_by: currentUserAccessKey
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            updateConnectionStatus('success', `User ${username} has been blocked successfully`);
            // Clear form
            userSelect.value = '';
            blockReason.value = '';
            // Force complete refresh of blocking data
            await loadBlockingData();
        } else {
            const error = JSON.parse(response.body);
            updateConnectionStatus('error', `Failed to block user: ${error.error}`);
        }
    } catch (error) {
        console.error('Error blocking user:', error);
        updateConnectionStatus('error', `Error blocking user: ${error.message}`);
    }
}

async function blockUser(username) {
    const reason = prompt(`Enter reason for blocking ${username}:`);
    if (!reason) return;
    
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'block',
                user_id: username,
                reason: reason,
                duration: '1day',
                performed_by: currentUserAccessKey
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            alert(`User ${username} has been blocked successfully`);
            // Force complete refresh of blocking data
            await loadBlockingData();
        } else {
            const error = JSON.parse(response.body);
            alert(`Failed to block user: ${error.error}`);
        }
    } catch (error) {
        console.error('Error blocking user:', error);
        alert(`Error blocking user: ${error.message}`);
    }
}

async function unblockUser(username) {
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'unblock',
                user_id: username,
                performed_by: currentUserAccessKey
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            alert(`User ${username} has been unblocked successfully`);
            // Force complete refresh of blocking data
            await loadBlockingData();
        } else {
            const error = JSON.parse(response.body);
            alert(`Failed to unblock user: ${error.error}`);
        }
    } catch (error) {
        console.error('Error unblocking user:', error);
        alert(`Error unblocking user: ${error.message}`);
    }
}

async function getUserStatus(username) {
    try {
        const lambda = new AWS.Lambda();
        const params = {
            FunctionName: 'bedrock-policy-manager',
            Payload: JSON.stringify({
                action: 'check_status',
                user_id: username
            })
        };
        
        const result = await lambda.invoke(params).promise();
        const response = JSON.parse(result.Payload);
        
        if (response.statusCode === 200) {
            const data = JSON.parse(response.body);
            const status = data.is_blocked ? 'BLOCKED' : 'ACTIVE';
            const message = `User: ${username}\nStatus: ${status}\nDaily Usage: ${data.daily_usage || 0}\nDaily Limit: ${data.daily_limit || 0}`;
            alert(message);
        } else {
            const error = JSON.parse(response.body);
            alert(`Failed to get user status: ${error.error}`);
        }
    } catch (error) {
        console.error('Error getting user status:', error);
        alert(`Error getting user status: ${error.message}`);
    }
}

// Update user blocking status for all users
async function updateUserBlockingStatus() {
    if (!isConnectedToAWS) {
        console.log('Not connected to AWS, skipping blocking status update');
        return;
    }
    
    try {
        console.log('Updating blocking status and admin protection for all users...');
        
        // Clear existing status
        userBlockingStatus = {};
        userAdminProtection = {};
        
        // Get blocking status and admin protection for each user
        for (const username of allUsers) {
            try {
                // Get blocking status from Lambda
                const lambda = new AWS.Lambda();
                const params = {
                    FunctionName: 'bedrock-policy-manager',
                    Payload: JSON.stringify({
                        action: 'check_status',
                        user_id: username
                    })
                };
                
                const result = await lambda.invoke(params).promise();
                const response = JSON.parse(result.Payload);
                
                if (response.statusCode === 200) {
                    const data = JSON.parse(response.body);
                    userBlockingStatus[username] = data.is_blocked || false;
                } else {
                    // Default to not blocked if we can't get status
                    userBlockingStatus[username] = false;
                }
                
                // Check for administrative protection by querying DynamoDB directly
                try {
                    const dynamodb = new AWS.DynamoDB.DocumentClient();
                    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
                    
                    const dbParams = {
                        TableName: 'bedrock_user_daily_usage',
                        Key: {
                            'user_id': username,
                            'date': today
                        }
                    };
                    
                    const dbResult = await dynamodb.get(dbParams).promise();
                    if (dbResult.Item && dbResult.Item.admin_protection === true) {
                        userAdminProtection[username] = true;
                        console.log(`User ${username} has administrative protection`);
                    } else {
                        userAdminProtection[username] = false;
                    }
                } catch (error) {
                    console.error(`Error checking admin protection for user ${username}:`, error);
                    userAdminProtection[username] = false;
                }
                
            } catch (error) {
                console.error(`Error getting blocking status for user ${username}:`, error);
                // Default to not blocked if there's an error
                userBlockingStatus[username] = false;
                userAdminProtection[username] = false;
            }
        }
        
        console.log('Updated blocking status:', userBlockingStatus);
        console.log('Updated admin protection:', userAdminProtection);
        
    } catch (error) {
        console.error('Error updating user blocking status:', error);
    }
}

// Format datetime in CET timezone
function formatDateTime(isoString, includeSeconds = false) {
    if (!isoString || isoString === 'Indefinite' || isoString === null) {
        return 'Indefinite';
    }
    
    try {
        // Create date from ISO string (this will be in UTC)
        const utcDate = new Date(isoString);
        
        // Check if date is valid
        if (isNaN(utcDate.getTime())) {
            return 'Indefinite';
        }
        
        // Use Intl.DateTimeFormat with formatToParts for proper timezone conversion
        const formatter = new Intl.DateTimeFormat('en-GB', {
            timeZone: 'Europe/Madrid',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const parts = formatter.formatToParts(utcDate);
        const partsObj = {};
        parts.forEach(part => {
            partsObj[part.type] = part.value;
        });
        
        const day = partsObj.day;
        const month = partsObj.month;
        const fullYear = partsObj.year;
        const year = includeSeconds ? fullYear : fullYear.slice(-2);
        const hours = partsObj.hour;
        const minutes = partsObj.minute;
        const seconds = partsObj.second;
        
        if (includeSeconds) {
            return `${day}/${month}/${year}, ${hours}:${minutes}:${seconds}`;
        } else {
            return `${day}/${month}/${year} - ${hours}:${minutes}`;
        }
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Indefinite';
    }
}

// Handle duration change for custom datetime
function handleDurationChange() {
    const durationSelect = document.getElementById('block-duration');
    const customDatetime = document.getElementById('custom-datetime');
    
    if (durationSelect.value === 'custom') {
        customDatetime.style.display = 'block';
        // Set minimum datetime to current time
        const now = new Date();
        const localISOTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        customDatetime.min = localISOTime;
        customDatetime.value = localISOTime;
        
        // Update the option text to show selected datetime
        customDatetime.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const formattedDate = formatDateTime(selectedDate.toISOString());
            durationSelect.options[durationSelect.selectedIndex].text = formattedDate;
        });
    } else {
        customDatetime.style.display = 'none';
        // Reset custom option text
        const customOption = durationSelect.querySelector('option[value="custom"]');
        if (customOption) {
            customOption.text = 'Custom';
        }
    }
}

// Calculate expiration date based on duration
function calculateExpirationDate(duration) {
    const now = new Date();
    
    switch (duration) {
        case '1day':
            return new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString();
        case '30days':
            return new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString();
        case '90days':
            return new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000).toISOString();
        case 'custom':
            const customDatetime = document.getElementById('custom-datetime');
            if (!customDatetime.value) {
                return null;
            }
            return new Date(customDatetime.value).toISOString();
        case 'indefinite':
        default:
            return 'Indefinite';
    }
}

// Dynamic action function
async function performDynamicAction() {
    const userSelect = document.getElementById('user-select');
    const blockDuration = document.getElementById('block-duration');
    const blockReason = document.getElementById('block-reason');
    const dynamicBtn = document.getElementById('dynamic-action-btn');
    
    const username = userSelect.value;
    const duration = blockDuration.value;
    const reason = blockReason.value;
    
    if (!username) {
        alert('Please select a user');
        return;
    }
    
    const isBlocked = userBlockingStatus[username] || false;
    
    if (isBlocked) {
        // Unblock user
        try {
            const lambda = new AWS.Lambda();
            const params = {
                FunctionName: 'bedrock-policy-manager',
                Payload: JSON.stringify({
                    action: 'unblock',
                    user_id: username,
                    reason: reason || 'Manual unblock',
                    performed_by: currentUserAccessKey
                })
            };
            
            const result = await lambda.invoke(params).promise();
            const response = JSON.parse(result.Payload);
            
            if (response.statusCode === 200) {
                alert(`User ${username} has been unblocked successfully`);
                // Clear form
                userSelect.value = '';
                blockReason.value = '';
                // Update button state
                updateDynamicButton();
                // Force complete refresh of blocking data
                await loadBlockingData();
            } else {
                const error = JSON.parse(response.body);
                alert(`Failed to unblock user: ${error.error}`);
            }
        } catch (error) {
            console.error('Error unblocking user:', error);
            alert(`Error unblocking user: ${error.message}`);
        }
    } else {
        // Block user
        if (!reason) {
            alert('Please provide a reason for blocking');
            return;
        }
        
        // Calculate expiration date
        const expiresAt = calculateExpirationDate(duration);
        if (duration === 'custom' && !expiresAt) {
            alert('Please select a custom date and time');
            return;
        }
        
        try {
            const lambda = new AWS.Lambda();
            const params = {
                FunctionName: 'bedrock-policy-manager',
                Payload: JSON.stringify({
                    action: 'block',
                    user_id: username,
                    reason: reason,
                    expires_at: expiresAt,
                    performed_by: currentUserAccessKey
                })
            };
            
            const result = await lambda.invoke(params).promise();
            const response = JSON.parse(result.Payload);
            
            if (response.statusCode === 200) {
                alert(`User ${username} has been blocked successfully`);
                // Clear form
                userSelect.value = '';
                blockReason.value = '';
                blockDuration.value = '1day';
                document.getElementById('custom-datetime').style.display = 'none';
                // Reset custom option text
                const customOption = blockDuration.querySelector('option[value="custom"]');
                if (customOption) {
                    customOption.text = 'Custom';
                }
                // Update button state
                updateDynamicButton();
                // Force complete refresh of blocking data
                await loadBlockingData();
            } else {
                const error = JSON.parse(response.body);
                alert(`Failed to block user: ${error.error}`);
            }
        } catch (error) {
            console.error('Error blocking user:', error);
            alert(`Error blocking user: ${error.message}`);
        }
    }
}

// Update dynamic button and duration control based on selected user
function updateDynamicButton() {
    const userSelect = document.getElementById('user-select');
    const dynamicBtn = document.getElementById('dynamic-action-btn');
    const blockDuration = document.getElementById('block-duration');
    const customDatetime = document.getElementById('custom-datetime');
    const selectedUser = userSelect.value;
    
    if (!selectedUser) {
        // No user selected - gray state
        dynamicBtn.className = 'btn btn-select-user';
        dynamicBtn.textContent = 'Select user';
        dynamicBtn.disabled = true;
        // Disable duration control when no user selected
        blockDuration.disabled = true;
        customDatetime.style.display = 'none';
    } else {
        const isBlocked = userBlockingStatus[selectedUser] || false;
        
        if (isBlocked) {
            // User is blocked - green unblock button
            dynamicBtn.className = 'btn btn-unblock-user';
            dynamicBtn.textContent = 'Unblock User';
            dynamicBtn.disabled = false;
            // Disable duration control for blocked users
            blockDuration.disabled = true;
            customDatetime.style.display = 'none';
        } else {
            // User is active - pink block button
            dynamicBtn.className = 'btn btn-block-user';
            dynamicBtn.textContent = 'Block User';
            dynamicBtn.disabled = false;
            // Enable duration control for active users
            blockDuration.disabled = false;
            // Show custom datetime if custom is selected
            if (blockDuration.value === 'custom') {
                customDatetime.style.display = 'block';
            }
        }
    }
}

// Initialize controls on page load
function initializeBlockingControls() {
    const blockDuration = document.getElementById('block-duration');
    const customDatetime = document.getElementById('custom-datetime');
    
    // Set default value to "1day" and disable control
    blockDuration.value = '1day';
    blockDuration.disabled = true;
    customDatetime.style.display = 'none';
}
