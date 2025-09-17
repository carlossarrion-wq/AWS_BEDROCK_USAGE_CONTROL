// AWS Bedrock Usage Dashboard JavaScript

// Global variables
let allUsers = [];
let usersByTeam = {};
let userTags = {};
let userMetrics = {};
let teamMetrics = {};
let quotaConfig = null;
let isConnectedToAWS = false;
let currentUserAccessKey = '';

// Chart instances
let userMonthlyChart;
let userDailyChart;
let accessMethodChart;
let teamMonthlyChart;
let teamDailyChart;
let modelDistributionChart;
let consumptionDetailsChart;
let costTrendChart;
let serviceCostChart;
let costPerRequestChart;
let costRequestsCorrelationChart;

// Cost Analysis data
let costData = {};

// Blocking management variables
let userBlockingStatus = {};
let userAdminProtection = {};
let operationsCurrentPage = 1;
let operationsTotalCount = 0;
let allOperations = [];

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeBlockingControls();
    checkCredentials();
    
    // Add event listener for user selection change
    document.getElementById('user-select').addEventListener('change', updateDynamicButton);
});

// Connection status management
function updateConnectionStatus(status, message) {
    const indicator = document.getElementById('connection-status');
    indicator.className = `connection-status ${status}`;
    indicator.style.opacity = '1';
    
    // Clear any existing timeout
    if (window.statusTimeout) {
        clearTimeout(window.statusTimeout);
    }
    
    switch(status) {
        case 'connected':
            indicator.innerHTML = '🟢 ' + (message || 'Connected to AWS');
            window.statusTimeout = setTimeout(() => {
                indicator.style.opacity = '0';
            }, 5000);
            break;
        case 'connecting':
            indicator.innerHTML = '🟡 ' + (message || 'Connecting to AWS...');
            break;
        case 'success':
            indicator.innerHTML = '✅ ' + (message || 'Operation successful');
            window.statusTimeout = setTimeout(() => {
                indicator.style.opacity = '0';
            }, 4000);
            break;
        case 'error':
            indicator.innerHTML = '❌ ' + (message || 'Operation failed');
            window.statusTimeout = setTimeout(() => {
                indicator.style.opacity = '0';
            }, 6000);
            break;
        case 'disconnected':
        default:
            indicator.innerHTML = '🔴 ' + (message || 'Disconnected from AWS');
            break;
    }
}

// Tab management
function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabId).classList.add('active');
    
    // Activate selected button
    document.querySelector(`.tab-button[onclick="showTab('${tabId}')"]`).classList.add('active');
    
    // Auto-load data when switching tabs
    if (tabId === 'blocking-management-tab' && isConnectedToAWS) {
        console.log('Switching to blocking tab, loading data...');
        loadBlockingData();
    }
    
    if (tabId === 'cost-analysis-tab') {
        console.log('Switching to cost analysis tab, loading data...');
        loadCostAnalysisData();
    }
}

// AWS Configuration and Authentication
async function configureAWSWithRole(accessKey, secretKey) {
    try {
        updateConnectionStatus('connecting', 'Configuring AWS credentials...');
        
        // First configure with user credentials
        AWS.config.update({
            region: AWS_CONFIG.region,
            credentials: new AWS.Credentials({
                accessKeyId: accessKey,
                secretAccessKey: secretKey
            })
        });
        
        updateConnectionStatus('connecting', 'Assuming dashboard role...');
        
        // Then assume the dashboard role
        const sts = new AWS.STS();
        const params = {
            RoleArn: AWS_CONFIG.dashboard_role_arn,
            RoleSessionName: 'bedrock-dashboard-session',
            ExternalId: AWS_CONFIG.external_id,
            DurationSeconds: 3600 // 1 hour
        };
        
        const data = await sts.assumeRole(params).promise();
        
        // Update AWS config with assumed role credentials
        AWS.config.update({
            credentials: new AWS.Credentials({
                accessKeyId: data.Credentials.AccessKeyId,
                secretAccessKey: data.Credentials.SecretAccessKey,
                sessionToken: data.Credentials.SessionToken
            })
        });
        
        console.log('Successfully assumed dashboard role');
        updateConnectionStatus('connected', 'Connected to AWS');
        isConnectedToAWS = true;
        return true;
    } catch (error) {
        console.error('Error assuming dashboard role:', error);
        updateConnectionStatus('disconnected', 'Failed to connect to AWS');
        isConnectedToAWS = false;
        throw error;
    }
}

async function checkCredentials() {
    const accessKey = sessionStorage.getItem('aws_access_key');
    const secretKey = sessionStorage.getItem('aws_secret_key');
    
    if (!accessKey || !secretKey) {
        window.location.href = 'login.html?error=no_credentials';
        return;
    }
    
    currentUserAccessKey = accessKey;
    
    try {
        await configureAWSWithRole(accessKey, secretKey);
        await loadQuotaConfig();
        await loadDashboardData();
    } catch (error) {
        console.error('Error configuring AWS:', error);
        showErrorMessage('Failed to connect to AWS. Please check your credentials and try again.');
        updateConnectionStatus('disconnected', 'Connection failed');
    }
}

function logout() {
    sessionStorage.removeItem('aws_access_key');
    sessionStorage.removeItem('aws_secret_key');
    updateConnectionStatus('disconnected', 'Logged out');
    isConnectedToAWS = false;
    window.location.href = 'login.html';
}

// Quota Configuration Management
async function loadQuotaConfig() {
    try {
        const cacheBuster = new Date().getTime();
        let response;
        let config;
        
        // First try: Lambda function directory
        try {
            response = await fetch(`individual_blocking_system/lambda_functions/quota_config.json?v=${cacheBuster}`);
            if (response.ok) {
                config = await response.json();
                console.log('Loaded quota configuration from Lambda directory:', config);
                quotaConfig = config;
                return config;
            }
        } catch (lambdaError) {
            console.log('Lambda directory quota_config.json not accessible, trying root directory...');
        }
        
        // Second try: Root directory (fallback)
        try {
            response = await fetch(`quota_config.json?v=${cacheBuster}`);
            if (response.ok) {
                config = await response.json();
                console.log('Loaded quota configuration from root directory:', config);
                quotaConfig = config;
                return config;
            }
        } catch (rootError) {
            console.log('Root directory quota_config.json not accessible either');
        }
        
        throw new Error('quota_config.json not found in Lambda directory or root directory');
        
    } catch (error) {
        console.error('Error loading quota configuration from file, using fallback:', error);
        console.log('Using fallback quota configuration:', DEFAULT_QUOTA_CONFIG);
        quotaConfig = DEFAULT_QUOTA_CONFIG;
        return DEFAULT_QUOTA_CONFIG;
    }
}

// CloudWatch Metrics Functions
async function fetchRealCloudWatchMetrics(metricName, dimension, startTime, endTime, namespace = 'UserMetrics', dimensionName = 'User') {
    if (!isConnectedToAWS) {
        throw new Error('Not connected to AWS');
    }
    
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

async function fetchRealUsersFromIAM() {
    if (!isConnectedToAWS) {
        throw new Error('Not connected to AWS');
    }
    
    const iam = new AWS.IAM();
    
    try {
        const allUsers = [];
        const usersByTeam = {};
        const userTags = {};
        
        // Initialize teams
        ALL_TEAMS.forEach(team => {
            usersByTeam[team] = [];
        });
        
        // Fetch users for each team
        for (const team of ALL_TEAMS) {
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

// Dashboard Data Loading
async function loadDashboardData() {
    if (!isConnectedToAWS) {
        showErrorMessage('Not connected to AWS. Please refresh the page and login again.');
        return;
    }
    
    try {
        updateConnectionStatus('connecting', 'Loading dashboard data...');
        showLoadingIndicators();
        
        // Fetch users from IAM
        const userData = await fetchRealUsersFromIAM();
        allUsers = userData.allUsers;
        usersByTeam = userData.usersByTeam;
        userTags = userData.userTags;
        
        // Get current date and time
        const now = new Date();
        const startTime = getFirstDayOfMonth();
        
        // Fetch metrics for all users and teams
        await fetchAllMetrics(startTime, now);
        
        // Load all dashboard sections
        loadUserMonthlyData();
        loadUserDailyData();
        loadUserUsageDetails();
        loadAccessMethodData();
        loadTeamMonthlyData();
        loadTeamDailyData();
        loadTeamUsageDetails();
        loadTeamUsersData();
        loadModelDistributionData();
        loadConsumptionDetailsData();
        loadModelUsageData();
        
        updateConnectionStatus('connected', 'Data loaded successfully');
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showErrorMessage('Failed to load dashboard data: ' + error.message);
        updateConnectionStatus('disconnected', 'Failed to load data');
    }
}

function showLoadingIndicators() {
    document.getElementById('user-alerts-container').innerHTML = `
        <div class="alert info">
            <div class="loading-spinner"></div>
            <strong>Loading:</strong> Fetching user data from AWS...
        </div>
    `;
    
    document.getElementById('team-alerts-container').innerHTML = `
        <div class="alert info">
            <div class="loading-spinner"></div>
            <strong>Loading:</strong> Fetching team data from AWS...
        </div>
    `;
}

function showErrorMessage(message) {
    const alertsContainer = document.getElementById('user-alerts-container');
    alertsContainer.innerHTML = `
        <div class="alert critical">
            <strong>Error:</strong> ${message}
        </div>
    `;
}

function getFirstDayOfMonth() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
}

async function fetchAllMetrics(startTime, endTime) {
    // Fetch metrics for each user
    for (const username of allUsers) {
        try {
            const monthlyResult = await fetchRealCloudWatchMetrics('BedrockUsage', username, startTime, endTime, 'UserMetrics');
            const dailyResult = await getDailyMetricData(username, startTime, endTime);
            
            userMetrics[username] = {
                monthly: monthlyResult.total || 0,
                daily: dailyResult.dailyData || Array(10).fill(0)
            };
        } catch (error) {
            console.error(`Error fetching metrics for user ${username}:`, error);
            userMetrics[username] = {
                monthly: 0,
                daily: Array(10).fill(0)
            };
        }
    }
    
    // Calculate team metrics by aggregating user metrics
    for (const team of ALL_TEAMS) {
        const teamUsers = usersByTeam[team] || [];
        
        teamMetrics[team] = {
            monthly: 0,
            daily: Array(10).fill(0)
        };
        
        for (const username of teamUsers) {
            if (userMetrics[username]) {
                teamMetrics[team].monthly += userMetrics[username].monthly;
                
                for (let i = 0; i < 10; i++) {
                    teamMetrics[team].daily[i] += userMetrics[username].daily[i] || 0;
                }
            }
        }
    }
}

async function getDailyMetricData(username, startTime, endTime) {
    try {
        const extendedEndTime = new Date(endTime);
        extendedEndTime.setDate(extendedEndTime.getDate() + 1);
        
        const result = await fetchRealCloudWatchMetrics('BedrockUsage', username, startTime, extendedEndTime, 'UserMetrics');
        
        const dailyData = Array(10).fill(0);
        
        if (result.datapoints && result.datapoints.length > 0) {
            const sortedDatapoints = [...result.datapoints].sort((a, b) => 
                new Date(a.Timestamp) - new Date(b.Timestamp)
            );
            
            sortedDatapoints.forEach(datapoint => {
                const date = new Date(datapoint.Timestamp);
                const endTimeLocal = new Date(endTime.getFullYear(), endTime.getMonth(), endTime.getDate());
                const dateLocal = new Date(date.getFullYear(), date.getMonth(), date.getDate());
                const daysAgo = Math.floor((endTimeLocal - dateLocal) / (1000 * 60 * 60 * 24));
                
                if (daysAgo >= -1 && daysAgo < 9) {
                    let index;
                    if (daysAgo === 0) {
                        index = 8; // Today
                    } else if (daysAgo === -1) {
                        index = 9; // Tomorrow
                    } else {
                        index = 8 - daysAgo; // Past days
                    }
                    dailyData[index] = datapoint.Sum || 0;
                }
            });
        }
        
        return { dailyData };
    } catch (error) {
        console.error(`Error fetching daily metrics for ${username}:`, error);
        return { dailyData: Array(10).fill(0) };
    }
}

function getUserPersonTag(username) {
    if (!userTags[username]) return null;
    
    for (const key in userTags[username]) {
        if (key.toLowerCase() === 'person') {
            return userTags[username][key];
        }
    }
    return null;
}

// User Data Loading Functions
function loadUserMonthlyData() {
    const labels = [];
    const data = [];
    const colors = CHART_COLORS.primary;
    
    const sortedUsers = [...allUsers].sort();
    
    sortedUsers.forEach((username, index) => {
        const personTag = getUserPersonTag(username) || "Unknown";
        const userLabel = `${username} - ${personTag}`;
        
        labels.push(userLabel);
        data.push(userMetrics[username]?.monthly || 0);
    });
    
    const chartData = {
        labels: labels,
        datasets: [{
            label: 'Monthly Requests',
            data: data,
            backgroundColor: colors,
            borderWidth: 1
        }]
    };
    
    updateUserMonthlyChart(chartData);
}

function loadUserDailyData() {
    const dateLabels = [];
    for (let i = 8; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        if (i === 0) {
            dateLabels.push('Today');
        } else {
            dateLabels.push(moment(date).format('D MMM'));
        }
    }
    
    const datasets = [];
    
    allUsers.forEach((username, index) => {
        const personTag = getUserPersonTag(username) || "Unknown";
        const userLabel = `${username} - ${personTag}`;
        
        datasets.push({
            label: userLabel,
            data: userMetrics[username]?.daily || Array(10).fill(0),
            borderColor: CHART_COLORS.primary[index % CHART_COLORS.primary.length],
            backgroundColor: CHART_COLORS.primary[index % CHART_COLORS.primary.length] + '33',
            tension: 0.4,
            fill: true
        });
    });
    
    const data = {
        labels: dateLabels,
        datasets: datasets
    };
    
    updateUserDailyChart(data);
}

async function loadUserUsageDetails() {
    const tableBody = document.querySelector('#user-usage-table tbody');
    tableBody.innerHTML = '';
    
    const sortedUsers = [...allUsers].sort((a, b) => a.localeCompare(b));
    
    await updateUserBlockingStatus();
    
    for (const username of sortedUsers) {
        const personTag = getUserPersonTag(username) || "Unknown";
        
        let userTeam = "Unknown";
        for (const team in usersByTeam) {
            if (usersByTeam[team].includes(username)) {
                userTeam = team;
                break;
            }
        }
        
        const userQuota = quotaConfig?.users?.[username] || { 
            monthly_limit: 5000, 
            daily_limit: 250,
            warning_threshold: 60, 
            critical_threshold: 85 
        };
        
        const monthlyTotal = userMetrics[username]?.monthly || 0;
        const monthlyLimit = userQuota.monthly_limit;
        const monthlyPercentage = Math.round((monthlyTotal / monthlyLimit) * 100);
        
        let monthlyColorClass = '';
        if (monthlyPercentage > userQuota.critical_threshold) {
            monthlyColorClass = 'critical';
        } else if (monthlyPercentage > userQuota.warning_threshold) {
            monthlyColorClass = 'warning';
        }
        
        const dailyTotal = userMetrics[username]?.daily?.[8] || 0;
        const dailyLimit = userQuota.daily_limit;
        const dailyPercentage = Math.round((dailyTotal / dailyLimit) * 100);
        
        let dailyColorClass = '';
        if (dailyPercentage > userQuota.critical_threshold) {
            dailyColorClass = 'critical';
        } else if (dailyPercentage > userQuota.warning_threshold) {
            dailyColorClass = 'warning';
        }
        
        let statusBadge = `<span class="status-badge active" style="cursor: pointer;" onclick="navigateToBlockingTab()">Active</span>`;
        
        if (userBlockingStatus && userBlockingStatus[username]) {
            let isAdminBlock = false;
            try {
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
                    isAdminBlock = adminProtectionBy && adminProtectionBy !== 'system';
                }
            } catch (error) {
                console.error(`Error checking admin block status for ${username}:`, error);
                isAdminBlock = false;
            }
            
            if (isAdminBlock) {
                statusBadge = `<span class="status-badge blocked" style="cursor: pointer;" onclick="navigateToBlockingTab()">Blocked Admin</span>`;
            } else {
                statusBadge = `<span class="status-badge blocked" style="cursor: pointer;" onclick="navigateToBlockingTab()">Blocked</span>`;
            }
        } else if (userAdminProtection && userAdminProtection[username]) {
            statusBadge = `<span class="status-badge active-admin" style="cursor: pointer;" onclick="navigateToBlockingTab()">Active Admin</span>`;
        }
        
        tableBody.innerHTML += `
            <tr>
                <td>${username}</td>
                <td>${personTag}</td>
                <td>${userTeam}</td>
                <td>${statusBadge}</td>
                <td>${dailyTotal}</td>
                <td>${dailyLimit}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-bar-fill ${dailyColorClass}" style="width: ${dailyPercentage}%"></div>
                    </div>
                    ${dailyPercentage}%
                </td>
                <td>${monthlyTotal}</td>
                <td>${monthlyLimit}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-bar-fill ${monthlyColorClass}" style="width: ${monthlyPercentage}%"></div>
                    </div>
                    ${monthlyPercentage}%
                </td>
            </tr>
        `;
    }
    
    updateUserAlerts();
}

function updateUserAlerts() {
    const alertsContainer = document.getElementById('user-alerts-container');
    alertsContainer.innerHTML = '';
    
    alertsContainer.innerHTML += `
        <div class="alert info">
            <strong>All Users:</strong> Monitoring ${allUsers.length} users across ${ALL_TEAMS.length} teams
        </div>
    `;
    
    const userDailyPercentages = [];
    
    allUsers.forEach(username => {
        const userQuota = quotaConfig?.users?.[username] || { 
            monthly_limit: 5000, 
            daily_limit: 250,
            warning_threshold: 60, 
            critical_threshold: 85 
        };
        
        const dailyTotal = userMetrics[username]?.daily?.[8] || 0;
        const dailyLimit = userQuota.daily_limit;
        const dailyPercentage = Math.round((dailyTotal / dailyLimit) * 100);
        const personTag = getUserPersonTag(username) || "Unknown";
        
        userDailyPercentages.push({
            username,
            personTag,
            dailyTotal,
            dailyLimit,
            dailyPercentage,
            critical_threshold: userQuota.critical_threshold,
            warning_threshold: userQuota.warning_threshold
        });
    });
    
    const highUsageUsers = userDailyPercentages.filter(user => user.dailyPercentage >= 80);
    highUsageUsers.sort((a, b) => b.dailyPercentage - a.dailyPercentage);
    
    if (highUsageUsers.length > 0) {
        highUsageUsers.forEach(user => {
            let alertClass = 'info';
            let alertPrefix = 'Info';
            
            if (user.dailyPercentage > user.critical_threshold) {
                alertClass = 'critical';
                alertPrefix = 'Critical';
            } else if (user.dailyPercentage > user.warning_threshold) {
                alertClass = '';
                alertPrefix = 'Warning';
            }
            
            alertsContainer.innerHTML += `
                <div class="alert ${alertClass}">
                    <strong>${alertPrefix}:</strong> ${user.username} (${user.personTag}) is at ${user.dailyPercentage}% of daily limit (${user.dailyTotal}/${user.dailyLimit})
                </div>
            `;
        });
    } else {
        alertsContainer.innerHTML += `
            <div class="alert info">
                <strong>Info:</strong> No users have surpassed 80% of their daily usage limit.
            </div>
        `;
    }
}

function loadAccessMethodData() {
    const data = {
        labels: ['API Key', 'Console', 'Assumed Role'],
        datasets: [{
            label: 'Access Method',
            data: [75, 20, 5],
            backgroundColor: ['#1e4a72', '#27ae60', '#e67e22'],
            borderWidth: 1
        }]
    };
    
    updateAccessMethodChart(data);
}

// Team Data Loading Functions
function loadTeamMonthlyData() {
    const labels = [];
    const data = [];
    
    const sortedTeams = [...ALL_TEAMS].sort();
    
    sortedTeams.forEach((team, index) => {
        labels.push(team);
        data.push(teamMetrics[team]?.monthly || 0);
    });
    
    const chartData = {
        labels: labels,
        datasets: [{
            label: 'Monthly Requests',
            data: data,
            backgroundColor: CHART_COLORS.teams.slice(0, labels.length),
            borderWidth: 1
        }]
    };
    
    updateTeamMonthlyChart(chartData);
}

function loadTeamDailyData() {
    const dateLabels = [];
    for (let i = 8; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        if (i === 0) {
            dateLabels.push('Today');
        } else {
            dateLabels.push(moment(date).format('D MMM'));
        }
    }
    
    const datasets = [];
    
    ALL_TEAMS.forEach((team, index) => {
        const dailyData = teamMetrics[team]?.daily ? teamMetrics[team].daily.slice(0, 9) : Array(9).fill(0);
        
        datasets.push({
            label: team,
            data: dailyData,
            borderColor: CHART_COLORS.teams[index % CHART_COLORS.teams.length],
            backgroundColor: CHART_COLORS.teams[index % CHART_COLORS.teams.length] + '33',
            tension: 0.4,
            fill: true
        });
    });
    
    const data = {
        labels: dateLabels,
        datasets: datasets
    };
    
    updateTeamDailyChart(data);
}

function loadTeamUsageDetails() {
    const tableBody = document.querySelector('#team-usage-table tbody');
    tableBody.innerHTML = '';
    
    const sortedTeams = [...ALL_TEAMS].sort();
    
    sortedTeams.forEach(team => {
        const teamQuota = quotaConfig?.teams?.[team] || { 
            monthly_limit: 25000, 
            warning_threshold: 60, 
            critical_threshold: 85 
        };
        
        const monthlyTotal = teamMetrics[team]?.monthly || 0;
        const monthlyLimit = teamQuota.monthly_limit;
        const monthlyPercentage = Math.round((monthlyTotal / monthlyLimit) * 100);
        
        let monthlyColorClass = '';
        if (monthlyPercentage > teamQuota.critical_threshold) {
            monthlyColorClass = 'critical';
        } else if (monthlyPercentage > teamQuota.warning_threshold) {
            monthlyColorClass = 'warning';
        }
        
        const dailyTotal = teamMetrics[team]?.daily?.[8] || 0;
        const dailyPercentage = Math.round((dailyTotal / (monthlyLimit / 30)) * 100);
        
        let dailyColorClass = '';
        if (dailyPercentage > teamQuota.critical_threshold) {
            dailyColorClass = 'critical';
        } else if (dailyPercentage > teamQuota.warning_threshold) {
            dailyColorClass = 'warning';
        }
        
        tableBody.innerHTML += `
            <tr>
                <td>${team}</td>
                <td>${dailyTotal}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-bar-fill ${dailyColorClass}" style="width: ${dailyPercentage}%"></div>
                    </div>
                    ${dailyPercentage}%
                </td>
                <td>${monthlyTotal}</td>
                <td>${monthlyLimit}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-bar-fill ${monthlyColorClass}" style="width: ${monthlyPercentage}%"></div>
                    </div>
                    ${monthlyPercentage}%
                </td>
            </tr>
        `;
    });
    
    updateTeamAlerts();
}

function updateTeamAlerts() {
    const alertsContainer = document.getElementById('team-alerts-container');
    alertsContainer.innerHTML = '';
    
    alertsContainer.innerHTML += `
        <div class="alert info">
            <strong>All Teams:</strong> Monitoring ${ALL_TEAMS.length} teams (${ALL_TEAMS.join(', ')})
        </div>
    `;
    
    const highUsageTeams = [];
    
    ALL_TEAMS.forEach(team => {
        const teamQuota = quotaConfig?.teams?.[team] || { 
            monthly_limit: 25000, 
            warning_threshold: 60, 
            critical_threshold: 85 
        };
        
        const monthlyTotal = teamMetrics[team]?.monthly || 0;
        const monthlyLimit = teamQuota.monthly_limit;
        const monthlyPercentage = Math.round((monthlyTotal / monthlyLimit) * 100);
        
        if (monthlyPercentage >= 80) {
            highUsageTeams.push({
                team,
                monthlyTotal,
                monthlyLimit,
                monthlyPercentage,
                critical_threshold: teamQuota.critical_threshold,
                warning_threshold: teamQuota.warning_threshold
            });
        }
    });
    
    highUsageTeams.sort((a, b) => b.monthlyPercentage - a.monthlyPercentage);
    
    if (highUsageTeams.length > 0) {
        highUsageTeams.forEach(teamData => {
            let alertClass = 'info';
            let alertPrefix = 'Info';
            
            if (teamData.monthlyPercentage > teamData.critical_threshold) {
                alertClass = 'critical';
                alertPrefix = 'Critical';
            } else if (teamData.monthlyPercentage > teamData.warning_threshold) {
                alertClass = '';
                alertPrefix = 'Warning';
            }
            
            alertsContainer.innerHTML += `
                <div class="alert ${alertClass}">
                    <strong>${alertPrefix}:</strong> ${teamData.team} has reached ${teamData.monthlyPercentage}% of monthly limit (${teamData.monthlyTotal}/${teamData.monthlyLimit}).
                </div>
            `;
        });
    } else {
        alertsContainer.innerHTML += `
            <div class="alert info">
                <strong>Info:</strong> No teams have surpassed 80% of their monthly usage limit.
            </div>
        `;
    }
}

function loadTeamUsersData() {
    const tableBody = document.querySelector('#team-users-table tbody');
    tableBody.innerHTML = '';
    
    let allTeamUsers = [];
    
    ALL_TEAMS.forEach(team => {
        const teamUsersList = usersByTeam[team] || [];
        const teamTotal = teamMetrics[team]?.monthly || 0;
        
        teamUsersList.forEach(username => {
            const userRequests = userMetrics[username]?.monthly || 0;
            const percentage = teamTotal > 0 ? Math.round((userRequests / teamTotal) * 100) : 0;
            
            allTeamUsers.push({
                username,
                personTag: getUserPersonTag(username) || "Unknown",
                team,
                userRequests,
                percentage
            });
        });
    });
    
    allTeamUsers.sort((a, b) => b.userRequests - a.userRequests);
    
    allTeamUsers.forEach(user => {
        tableBody.innerHTML += `
            <tr>
                <td>${user.username}</td>
                <td>${user.personTag}</td>
                <td>${user.team}</td>
                <td>${user.userRequests}</td>
                <td>${user.percentage}%</td>
            </tr>
        `;
    });
    
    if (allUsers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5">No users found in any team</td>
            </tr>
        `;
    }
}

function loadModelDistributionData() {
    const selectedTeam = ALL_TEAMS[0];
    const modelLabels = ['Claude 3 Opus', 'Claude 3 Sonnet', 'Claude 3 Haiku', 'Claude 3.7 Sonnet', 'Amazon Titan'];
    
    const teamHash = selectedTeam.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    
    let distribution = [
        20 + (teamHash % 30),
        15 + ((teamHash * 2) % 25),
        10 + ((teamHash * 3) % 20),
        5 + ((teamHash * 4) % 15),
        5 + ((teamHash * 5) % 10)
    ];
    
    const sum = distribution.reduce((acc, val) => acc + val, 0);
    distribution = distribution.map(val => Math.round((val / sum) * 100));
    
    const currentSum = distribution.reduce((acc, val) => acc + val, 0);
    distribution[distribution.length - 1] += (100 - currentSum);
    
    const data = {
        labels: modelLabels,
        datasets: [{
            label: 'Model Usage',
            data: distribution,
            backgroundColor: ['#1e4a72', '#27ae60', '#e67e22', '#3498db', '#2d5aa0'],
            borderWidth: 1
        }]
    };
    
    updateModelDistributionChart(data);
}

function loadConsumptionDetailsData() {
    const tableBody = document.querySelector('#consumption-details-table tbody');
    tableBody.innerHTML = '';
    
    updateConsumptionDetailsHeaders();
    
    const sortedUsers = [...allUsers].sort();
    
    // Array to store daily totals
    const dailyTotals = Array(10).fill(0);
    
    sortedUsers.forEach(username => {
        const personTag = getUserPersonTag(username) || "Unknown";
        
        let userTeam = "Unknown";
        for (const team in usersByTeam) {
            if (usersByTeam[team].includes(username)) {
                userTeam = team;
                break;
            }
        }
        
        const dailyData = userMetrics[username]?.daily || Array(10).fill(0);
        
        let rowHtml = `
            <tr>
                <td>${username}</td>
                <td>${personTag}</td>
                <td>${userTeam}</td>
        `;
        
        for (let i = 0; i < 10; i++) {
            let dataIndex;
            if (i === 0) {
                dataIndex = 9;
            } else {
                dataIndex = i - 1;
            }
            
            const consumption = dailyData[dataIndex] || 0;
            rowHtml += `<td>${consumption}</td>`;
            
            // Add to daily totals
            dailyTotals[i] += consumption;
        }
        
        rowHtml += '</tr>';
        tableBody.innerHTML += rowHtml;
    });
    
    // Add totals row
    if (allUsers.length > 0) {
        let totalsRowHtml = `
            <tr style="border-top: 2px solid #1e4a72; background-color: #f8f9fa;">
                <td style="font-weight: bold;">TOTAL</td>
                <td style="font-weight: bold;">-</td>
                <td style="font-weight: bold;">-</td>
        `;
        
        for (let i = 0; i < 10; i++) {
            totalsRowHtml += `<td style="font-weight: bold;">${dailyTotals[i]}</td>`;
        }
        
        totalsRowHtml += '</tr>';
        tableBody.innerHTML += totalsRowHtml;
    }
    
    if (allUsers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="13">No users found</td>
            </tr>
        `;
    }
    
    // Update the consumption details chart
    updateConsumptionDetailsChart(dailyTotals);
}

function updateConsumptionDetailsChart(dailyTotals) {
    // Create labels for the last 10 days
    const dateLabels = [];
    for (let i = 9; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        if (i === 0) {
            dateLabels.push('Today');
        } else {
            dateLabels.push(moment(date).format('D MMM'));
        }
    }
    
    const chartData = {
        labels: dateLabels,
        datasets: [{
            label: 'Total Daily Requests',
            data: dailyTotals,
            backgroundColor: '#1e4a72',
            borderColor: '#1e4a72',
            borderWidth: 1
        }]
    };
    
    if (consumptionDetailsChart) {
        consumptionDetailsChart.data = chartData;
        consumptionDetailsChart.update();
    } else {
        consumptionDetailsChart = new Chart(
            document.getElementById('consumption-details-chart'),
            {
                type: 'bar',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Total Daily Usage - Last 10 Days'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Total Requests'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        }
                    }
                }
            }
        );
    }
}

function updateConsumptionDetailsHeaders() {
    for (let i = 0; i < 10; i++) {
        const date = new Date();
        const daysBack = 9 - i;
        date.setDate(date.getDate() - daysBack);
        
        const headerElement = document.getElementById(`day-${daysBack}`);
        if (headerElement) {
            const dayOfWeek = date.getDay();
            const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
            
            if (daysBack === 0) {
                headerElement.textContent = 'Today';
            } else {
                headerElement.textContent = moment(date).format('D MMM');
            }
            
            if (isWeekend) {
                headerElement.classList.add('weekend');
            } else {
                headerElement.classList.remove('weekend');
            }
        }
    }
}

function loadModelUsageData() {
    const tableBody = document.querySelector('#model-usage-table tbody');
    tableBody.innerHTML = '';
    
    const modelNames = ['Claude 3 Opus', 'Claude 3 Sonnet', 'Claude 3 Haiku', 'Claude 3.7 Sonnet', 'Claude 4', 'Amazon Titan'];
    const sortedTeams = [...ALL_TEAMS].sort();
    
    // Array to store model totals
    const modelTotals = Array(6).fill(0);
    let grandTotal = 0;
    
    sortedTeams.forEach(team => {
        const teamTotal = teamMetrics[team]?.monthly || 0;
        const teamHash = team.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        
        let distribution = [
            20 + (teamHash % 30),
            15 + ((teamHash * 2) % 25),
            10 + ((teamHash * 3) % 20),
            5 + ((teamHash * 4) % 15),
            10 + ((teamHash * 6) % 20),
            5 + ((teamHash * 5) % 10)
        ];
        
        const sum = distribution.reduce((acc, val) => acc + val, 0);
        distribution = distribution.map(val => Math.round((val / sum) * 100));
        
        const currentSum = distribution.reduce((acc, val) => acc + val, 0);
        distribution[distribution.length - 1] += (100 - currentSum);
        
        const modelUsage = distribution.map(percentage => 
            Math.round((teamTotal * percentage) / 100)
        );
        
        // Calculate the sum of all model usage for this team
        const teamModelSum = modelUsage.reduce((sum, usage) => sum + usage, 0);
        
        let rowHtml = `
            <tr>
                <td>${team}</td>
        `;
        
        modelUsage.forEach((usage, index) => {
            rowHtml += `<td>${usage}</td>`;
            // Add to model totals
            modelTotals[index] += usage;
        });
        
        rowHtml += `<td><strong>${teamModelSum}</strong></td>`;
        rowHtml += '</tr>';
        
        tableBody.innerHTML += rowHtml;
        
        // Add to grand total
        grandTotal += teamModelSum;
    });
    
    // Add totals row
    if (ALL_TEAMS.length > 0) {
        let totalsRowHtml = `
            <tr style="border-top: 2px solid #1e4a72; background-color: #f8f9fa;">
                <td style="font-weight: bold;">TOTAL</td>
        `;
        
        modelTotals.forEach(total => {
            totalsRowHtml += `<td style="font-weight: bold;">${total}</td>`;
        });
        
        totalsRowHtml += `<td style="font-weight: bold;"><strong>${grandTotal}</strong></td>`;
        totalsRowHtml += '</tr>';
        
        tableBody.innerHTML += totalsRowHtml;
    }
    
    if (ALL_TEAMS.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8">No teams found</td>
            </tr>
        `;
    }
}

// Navigation function
function navigateToBlockingTab() {
    showTab('blocking-management-tab');
}

// Export functions
function exportTableToCSV(tableId, filename) {
    try {
        const table = document.getElementById(tableId);
        const rows = table.querySelectorAll('tr');
        
        let csvContent = '';
        
        // Process each row
        rows.forEach((row, index) => {
            const cells = row.querySelectorAll('th, td');
            const rowData = [];
            
            cells.forEach(cell => {
                let cellText = cell.textContent.trim();
                
                // Clean up progress bar text (remove percentage and keep only the number)
                if (cellText.includes('%') && cellText.includes('\n')) {
                    // Extract just the percentage value
                    const percentageMatch = cellText.match(/(\d+)%/);
                    if (percentageMatch) {
                        cellText = percentageMatch[1] + '%';
                    }
                }
                
                // Handle status badges - extract just the text
                if (cell.querySelector('.status-badge')) {
                    const badge = cell.querySelector('.status-badge');
                    cellText = badge.textContent.trim();
                }
                
                // Escape commas and quotes in CSV
                if (cellText.includes(',') || cellText.includes('"') || cellText.includes('\n')) {
                    cellText = '"' + cellText.replace(/"/g, '""') + '"';
                }
                
                rowData.push(cellText);
            });
            
            // Skip empty rows or loading rows
            if (rowData.length > 0 && !rowData[0].includes('loading') && !rowData[0].includes('Connecting')) {
                csvContent += rowData.join(',') + '\n';
            }
        });
        
        // Create and download the file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            
            // Generate filename with current date
            const now = new Date();
            const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD format
            const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-'); // HH-MM-SS format
            
            link.setAttribute('download', `${filename}-${dateStr}-${timeStr}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Show success message
            updateConnectionStatus('success', `${filename} exported successfully`);
        }
    } catch (error) {
        console.error('Error exporting table:', error);
        updateConnectionStatus('error', 'Failed to export data: ' + error.message);
    }
}

// Export functions for each table
function exportUserUsageTable() {
    exportTableToCSV('user-usage-table', 'user-usage-details');
}

function exportTeamUsageTable() {
    exportTableToCSV('team-usage-table', 'team-usage-details');
}

function exportTeamUsersTable() {
    exportTableToCSV('team-users-table', 'users-in-team');
}

function exportConsumptionDetailsTable() {
    exportTableToCSV('consumption-details-table', 'user-consumption-last-10-days');
}

function exportModelUsageTable() {
    exportTableToCSV('model-usage-table', 'model-usage-by-team');
}

function exportUserBlockingStatusTable() {
    exportTableToCSV('user-blocking-status-table', 'current-user-status-manual-blocking');
}

function exportBlockingOperationsTable() {
    exportAllBlockingOperationsToCSV();
}

function exportAllBlockingOperationsToCSV() {
    try {
        if (allOperations.length === 0) {
            updateConnectionStatus('error', 'No operations data to export');
            return;
        }
        
        let csvContent = '';
        
        // Add CSV headers
        csvContent += 'Timestamp,User,Person,Operation,Reason,Performed By\n';
        
        // Process all operations (not just current page)
        allOperations.forEach(op => {
            const timestamp = formatDateTime(op.timestamp, true);
            const userId = op.user_id || 'Unknown';
            const personTag = getUserPersonTag(op.user_id) || 'Unknown';
            const operation = op.operation || 'Unknown';
            const reason = op.reason || 'No reason provided';
            const performedBy = op.performed_by || 'System';
            
            // Escape commas and quotes in CSV
            const rowData = [timestamp, userId, personTag, operation, reason, performedBy].map(field => {
                let fieldText = String(field).trim();
                if (fieldText.includes(',') || fieldText.includes('"') || fieldText.includes('\n')) {
                    fieldText = '"' + fieldText.replace(/"/g, '""') + '"';
                }
                return fieldText;
            });
            
            csvContent += rowData.join(',') + '\n';
        });
        
        // Create and download the file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            
            // Generate filename with current date
            const now = new Date();
            const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD format
            const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-'); // HH-MM-SS format
            
            link.setAttribute('download', `recent-blocking-operations-ALL-${dateStr}-${timeStr}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Show success message with count
            updateConnectionStatus('success', `All ${allOperations.length} blocking operations exported successfully`);
        }
    } catch (error) {
        console.error('Error exporting all blocking operations:', error);
        updateConnectionStatus('error', 'Failed to export operations data: ' + error.message);
    }
}

function exportCostVsRequestsTable() {
    exportTableToCSV('cost-vs-requests-table', 'daily-cost-vs-requests-analysis');
}

function exportCostAnalysisTable() {
    exportTableToCSV('cost-analysis-table', 'bedrock-cost-analysis-last-10-days');
}
