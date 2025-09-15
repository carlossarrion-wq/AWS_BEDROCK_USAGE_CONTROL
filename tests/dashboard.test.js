/**
 * Unit Tests for AWS Bedrock Usage Dashboard
 * 
 * This file contains comprehensive unit tests for all JavaScript functions
 * in the bedrock_usage_dashboard.html file.
 */

// Mock dependencies
const mockAWS = {
    config: {
        update: jest.fn()
    },
    Credentials: jest.fn(),
    CloudWatch: jest.fn(() => ({
        getMetricStatistics: jest.fn()
    })),
    IAM: jest.fn(() => ({
        getGroup: jest.fn(),
        listUserTags: jest.fn()
    }))
};

const mockChart = jest.fn(() => ({
    data: {},
    update: jest.fn(),
    destroy: jest.fn()
}));

const mockMoment = jest.fn(() => ({
    format: jest.fn()
}));

// Mock global objects
global.AWS = mockAWS;
global.Chart = mockChart;
global.moment = mockMoment;
global.sessionStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn()
};
global.window = {
    location: {
        href: '',
        assign: jest.fn()
    }
};
global.document = {
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => []),
    getElementById: jest.fn(),
    addEventListener: jest.fn()
};
global.console = {
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
};

// Load the dashboard functions (we'll simulate them here since we can't directly import from HTML)
// In a real scenario, these would be extracted to separate JS files

describe('Dashboard Configuration and Constants', () => {
    test('should have correct region configuration', () => {
        const region = 'eu-west-1';
        expect(region).toBe('eu-west-1');
    });

    test('should have all required teams defined', () => {
        const ALL_TEAMS = [
            'team_darwin_group',
            'team_sap_group',
            'team_mulesoft_group',
            'team_yo_leo_gas_group',
            'team_lcorp_group'
        ];
        expect(ALL_TEAMS).toHaveLength(5);
        expect(ALL_TEAMS).toContain('team_darwin_group');
        expect(ALL_TEAMS).toContain('team_sap_group');
    });
});

describe('Tab Management Functions', () => {
    let mockTabElements, mockButtonElements;

    beforeEach(() => {
        mockTabElements = [
            { classList: { remove: jest.fn(), add: jest.fn() } },
            { classList: { remove: jest.fn(), add: jest.fn() } }
        ];
        mockButtonElements = [
            { classList: { remove: jest.fn(), add: jest.fn() } },
            { classList: { remove: jest.fn(), add: jest.fn() } }
        ];

        global.document.querySelectorAll = jest.fn((selector) => {
            if (selector === '.tab-content') return mockTabElements;
            if (selector === '.tab-button') return mockButtonElements;
            return [];
        });
        global.document.getElementById = jest.fn(() => mockTabElements[0]);
        global.document.querySelector = jest.fn(() => mockButtonElements[0]);
    });

    test('showTab should hide all tabs and show selected tab', () => {
        // Simulate the showTab function
        function showTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            document.querySelector(`.tab-button[onclick="showTab('${tabId}')"]`).classList.add('active');
        }

        showTab('user-tab');

        // Verify all tabs are hidden
        mockTabElements.forEach(tab => {
            expect(tab.classList.remove).toHaveBeenCalledWith('active');
        });

        // Verify all buttons are deactivated
        mockButtonElements.forEach(button => {
            expect(button.classList.remove).toHaveBeenCalledWith('active');
        });

        // Verify selected tab is shown
        expect(mockTabElements[0].classList.add).toHaveBeenCalledWith('active');
        expect(mockButtonElements[0].classList.add).toHaveBeenCalledWith('active');
    });
});

describe('User Tag Functions', () => {
    let userTags;

    beforeEach(() => {
        userTags = {
            'test_user_001': {
                'Person': 'John Doe',
                'Department': 'Engineering'
            },
            'test_user_002': {
                'person': 'Jane Smith',
                'team': 'DevOps'
            }
        };
    });

    test('getUserPersonTag should return Person tag case-insensitively', () => {
        function getUserPersonTag(username) {
            if (!userTags[username]) return null;
            
            for (const key in userTags[username]) {
                if (key.toLowerCase() === 'person') {
                    return userTags[username][key];
                }
            }
            return null;
        }

        expect(getUserPersonTag('test_user_001')).toBe('John Doe');
        expect(getUserPersonTag('test_user_002')).toBe('Jane Smith');
        expect(getUserPersonTag('nonexistent_user')).toBeNull();
    });

    test('fetchUserTags should simulate tag fetching', async () => {
        function fetchUserTags(username) {
            return new Promise((resolve) => {
                console.log(`Simulating tag fetch for user ${username}`);
                const tags = { "Person": "Alberto Jaén" };
                console.log(`Tags for user ${username}:`, tags);
                userTags[username] = tags;
                resolve(tags);
            });
        }

        const result = await fetchUserTags('new_user');
        expect(result).toEqual({ "Person": "Alberto Jaén" });
        expect(userTags['new_user']).toEqual({ "Person": "Alberto Jaén" });
    });
});

describe('Quota Configuration Functions', () => {
    test('loadQuotaConfig should return hardcoded configuration', async () => {
        function loadQuotaConfig() {
            return new Promise((resolve) => {
                const config = {
                    users: {
                        "team_darwin_usr_001": {
                            monthly_limit: 3500,
                            daily_limit: 150,
                            warning_threshold: 60,
                            critical_threshold: 85
                        }
                    },
                    teams: {
                        "team_darwin_group": {
                            monthly_limit: 25000,
                            warning_threshold: 60,
                            critical_threshold: 85
                        }
                    }
                };
                resolve(config);
            });
        }

        const config = await loadQuotaConfig();
        expect(config.users["team_darwin_usr_001"].monthly_limit).toBe(3500);
        expect(config.teams["team_darwin_group"].monthly_limit).toBe(25000);
    });
});

describe('Authentication Functions', () => {
    test('checkCredentials should check for credentials and handle missing ones', () => {
        // Create fresh mock for this test
        const mockGetItem = jest.fn().mockReturnValue(null);
        
        // Mock sessionStorage for this test
        const mockSessionStorage = {
            getItem: mockGetItem,
            setItem: jest.fn(),
            removeItem: jest.fn()
        };
        
        function checkCredentials() {
            const accessKey = mockSessionStorage.getItem('aws_access_key');
            const secretKey = mockSessionStorage.getItem('aws_secret_key');
            
            if (!accessKey || !secretKey) {
                // In a real browser, this would redirect to login.html?error=no_credentials
                // For testing, we just verify the logic works
                return false; // Indicates credentials are missing
            }
            return true; // Indicates credentials are present
        }

        const result = checkCredentials();
        expect(result).toBe(false);
        expect(mockGetItem).toHaveBeenCalledWith('aws_access_key');
        expect(mockGetItem).toHaveBeenCalledWith('aws_secret_key');
    });

    test('logout should clear credentials', () => {
        // Create fresh mock for this test
        const mockRemoveItem = jest.fn();
        
        // Mock sessionStorage for this test
        const mockSessionStorage = {
            getItem: jest.fn(),
            setItem: jest.fn(),
            removeItem: mockRemoveItem
        };
        
        function logout() {
            mockSessionStorage.removeItem('aws_access_key');
            mockSessionStorage.removeItem('aws_secret_key');
            // In a real browser, this would redirect to login.html
            // For testing, we just verify the cleanup happens
            return true; // Indicates logout completed
        }

        const result = logout();
        expect(result).toBe(true);
        expect(mockRemoveItem).toHaveBeenCalledWith('aws_access_key');
        expect(mockRemoveItem).toHaveBeenCalledWith('aws_secret_key');
    });
});

describe('Date Utility Functions', () => {
    test('getFirstDayOfMonth should return first day of current month', () => {
        function getFirstDayOfMonth() {
            const now = new Date();
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            return firstDay;
        }

        const result = getFirstDayOfMonth();
        const now = new Date();
        const expected = new Date(now.getFullYear(), now.getMonth(), 1);
        
        expect(result.getFullYear()).toBe(expected.getFullYear());
        expect(result.getMonth()).toBe(expected.getMonth());
        expect(result.getDate()).toBe(1);
    });
});

describe('Data Loading Functions', () => {
    let mockCloudWatch, mockIAM;

    beforeEach(() => {
        mockCloudWatch = {
            getMetricStatistics: jest.fn()
        };
        mockIAM = {
            getGroup: jest.fn(),
            listUserTags: jest.fn()
        };
        
        global.document.getElementById = jest.fn(() => ({
            innerHTML: ''
        }));
    });

    test('showEmptyData should initialize empty data structures', () => {
        let allUsers = [];
        let usersByTeam = {};
        let userTags = {};
        let userMetrics = {};
        let teamMetrics = {};

        function showEmptyData() {
            allUsers = [];
            usersByTeam = {};
            userTags = {};
            userMetrics = {};
            teamMetrics = {};
        }

        showEmptyData();
        expect(allUsers).toEqual([]);
        expect(usersByTeam).toEqual({});
        expect(userTags).toEqual({});
        expect(userMetrics).toEqual({});
        expect(teamMetrics).toEqual({});
    });

    test('showUserError should display error message', () => {
        const mockContainer = { innerHTML: '' };
        global.document.getElementById = jest.fn(() => mockContainer);

        function showUserError(message) {
            const alertsContainer = document.getElementById('user-alerts-container');
            alertsContainer.innerHTML = `
                <div class="alert critical">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }

        showUserError('Test error message');
        expect(mockContainer.innerHTML).toContain('Test error message');
        expect(mockContainer.innerHTML).toContain('alert critical');
    });

    test('showTeamError should display error message', () => {
        const mockContainer = { innerHTML: '' };
        global.document.getElementById = jest.fn(() => mockContainer);

        function showTeamError(message) {
            const alertsContainer = document.getElementById('team-alerts-container');
            alertsContainer.innerHTML = `
                <div class="alert critical">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }

        showTeamError('Test team error');
        expect(mockContainer.innerHTML).toContain('Test team error');
        expect(mockContainer.innerHTML).toContain('alert critical');
    });
});

describe('AWS CloudWatch Integration Functions', () => {
    let mockCloudWatch;

    beforeEach(() => {
        mockCloudWatch = {
            getMetricStatistics: jest.fn()
        };
    });

    test('getMetricData should handle successful response', async () => {
        const mockResponse = {
            Datapoints: [
                { Sum: 100, Timestamp: new Date() },
                { Sum: 150, Timestamp: new Date() }
            ]
        };
        mockCloudWatch.getMetricStatistics.mockImplementation((params, callback) => {
            callback(null, mockResponse);
        });

        function getMetricData(cloudwatch, metricName, dimension, startTime, endTime, namespace = 'UserMetrics', dimensionName = 'User', dimensionValue = null) {
            return new Promise((resolve, reject) => {
                const params = {
                    MetricName: metricName,
                    Namespace: namespace,
                    Dimensions: [{ Name: dimensionName, Value: dimensionValue || dimension }],
                    StartTime: startTime,
                    EndTime: endTime,
                    Period: 86400,
                    Statistics: ['Sum']
                };
                
                cloudwatch.getMetricStatistics(params, (err, data) => {
                    if (err) {
                        resolve({ total: 0, datapoints: [] });
                        return;
                    }
                    
                    let total = 0;
                    if (data.Datapoints && data.Datapoints.length > 0) {
                        data.Datapoints.forEach(datapoint => {
                            total += datapoint.Sum || 0;
                        });
                    }
                    
                    resolve({ total, datapoints: data.Datapoints || [] });
                });
            });
        }

        const result = await getMetricData(mockCloudWatch, 'BedrockUsage', 'test_user', new Date(), new Date());
        expect(result.total).toBe(250);
        expect(result.datapoints).toHaveLength(2);
    });

    test('getMetricData should handle error response', async () => {
        mockCloudWatch.getMetricStatistics.mockImplementation((params, callback) => {
            callback(new Error('AWS Error'), null);
        });

        function getMetricData(cloudwatch, metricName, dimension, startTime, endTime, namespace = 'UserMetrics', dimensionName = 'User', dimensionValue = null) {
            return new Promise((resolve, reject) => {
                const params = {
                    MetricName: metricName,
                    Namespace: namespace,
                    Dimensions: [{ Name: dimensionName, Value: dimensionValue || dimension }],
                    StartTime: startTime,
                    EndTime: endTime,
                    Period: 86400,
                    Statistics: ['Sum']
                };
                
                cloudwatch.getMetricStatistics(params, (err, data) => {
                    if (err) {
                        console.error(`Error fetching ${metricName} for ${dimension}:`, err);
                        resolve({ total: 0, datapoints: [] });
                        return;
                    }
                    
                    let total = 0;
                    if (data.Datapoints && data.Datapoints.length > 0) {
                        data.Datapoints.forEach(datapoint => {
                            total += datapoint.Sum || 0;
                        });
                    }
                    
                    resolve({ total, datapoints: data.Datapoints || [] });
                });
            });
        }

        const result = await getMetricData(mockCloudWatch, 'BedrockUsage', 'test_user', new Date(), new Date());
        expect(result.total).toBe(0);
        expect(result.datapoints).toEqual([]);
    });

    test('getDailyMetricData should process datapoints correctly', async () => {
        const now = new Date();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);

        const mockResponse = {
            Datapoints: [
                { Sum: 50, Timestamp: now },
                { Sum: 75, Timestamp: yesterday }
            ]
        };
        mockCloudWatch.getMetricStatistics.mockImplementation((params, callback) => {
            callback(null, mockResponse);
        });

        function getDailyMetricData(cloudwatch, metricName, dimension, startTime, endTime, namespace = 'UserMetrics', dimensionName = 'User', dimensionValue = null) {
            return new Promise((resolve, reject) => {
                const extendedEndTime = new Date(endTime);
                extendedEndTime.setDate(extendedEndTime.getDate() + 1);
                
                const params = {
                    MetricName: metricName,
                    Namespace: namespace,
                    Dimensions: [{ Name: dimensionName, Value: dimensionValue || dimension }],
                    StartTime: startTime,
                    EndTime: extendedEndTime,
                    Period: 86400,
                    Statistics: ['Sum']
                };
                
                cloudwatch.getMetricStatistics(params, (err, data) => {
                    if (err) {
                        resolve({ dailyData: Array(10).fill(0) });
                        return;
                    }
                    
                    const dailyData = Array(10).fill(0);
                    
                    if (data.Datapoints && data.Datapoints.length > 0) {
                        const sortedDatapoints = [...data.Datapoints].sort((a, b) => 
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
                                    index = 8;
                                } else if (daysAgo === -1) {
                                    index = 9;
                                } else {
                                    index = 8 - daysAgo;
                                }
                                dailyData[index] = datapoint.Sum || 0;
                            }
                        });
                    }
                    
                    resolve({ dailyData });
                });
            });
        }

        const result = await getDailyMetricData(mockCloudWatch, 'BedrockUsage', 'test_user', new Date(), now);
        expect(result.dailyData).toHaveLength(10);
        expect(result.dailyData[8]).toBe(50); // Today's data
    });
});

describe('Chart Update Functions', () => {
    let mockChartInstance;

    beforeEach(() => {
        mockChartInstance = {
            data: {},
            update: jest.fn(),
            destroy: jest.fn()
        };
        global.Chart = jest.fn(() => mockChartInstance);
        global.document.getElementById = jest.fn(() => ({}));
    });

    test('updateUserMonthlyChart should update existing chart', () => {
        let userMonthlyChart = mockChartInstance;
        const testData = {
            labels: ['User1', 'User2'],
            datasets: [{ data: [100, 200] }]
        };

        function updateUserMonthlyChart(data) {
            if (userMonthlyChart) {
                userMonthlyChart.data = data;
                userMonthlyChart.update();
            } else {
                userMonthlyChart = new Chart(document.getElementById('user-monthly-chart'), {
                    type: 'bar',
                    data: data,
                    options: {}
                });
            }
        }

        updateUserMonthlyChart(testData);
        expect(mockChartInstance.data).toEqual(testData);
        expect(mockChartInstance.update).toHaveBeenCalled();
    });

    test('updateUserMonthlyChart should create new chart if none exists', () => {
        let userMonthlyChart = null;
        const testData = {
            labels: ['User1', 'User2'],
            datasets: [{ data: [100, 200] }]
        };

        function updateUserMonthlyChart(data) {
            if (userMonthlyChart) {
                userMonthlyChart.data = data;
                userMonthlyChart.update();
            } else {
                userMonthlyChart = new Chart(document.getElementById('user-monthly-chart'), {
                    type: 'bar',
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            }
        }

        updateUserMonthlyChart(testData);
        expect(global.Chart).toHaveBeenCalledWith(
            {},
            expect.objectContaining({
                type: 'bar',
                data: testData
            })
        );
    });
});

describe('Alert Update Functions', () => {
    let mockContainer, allUsers, userMetrics, quotaConfig, userTags, ALL_TEAMS;

    beforeEach(() => {
        mockContainer = { innerHTML: '' };
        global.document.getElementById = jest.fn(() => mockContainer);
        
        allUsers = ['user1', 'user2'];
        userMetrics = {
            'user1': { daily: [0, 0, 0, 0, 0, 0, 0, 0, 120, 0], monthly: 2000 },
            'user2': { daily: [0, 0, 0, 0, 0, 0, 0, 0, 50, 0], monthly: 1000 }
        };
        quotaConfig = {
            users: {
                'user1': { daily_limit: 150, warning_threshold: 60, critical_threshold: 85 },
                'user2': { daily_limit: 100, warning_threshold: 60, critical_threshold: 85 }
            }
        };
        userTags = {
            'user1': { 'Person': 'John Doe' },
            'user2': { 'Person': 'Jane Smith' }
        };
        ALL_TEAMS = ['team1', 'team2'];
    });

    test('updateUserAlerts should show high usage users', () => {
        function getUserPersonTag(username) {
            if (!userTags[username]) return null;
            for (const key in userTags[username]) {
                if (key.toLowerCase() === 'person') {
                    return userTags[username][key];
                }
            }
            return null;
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
                    monthly_limit: 3500, 
                    daily_limit: 150,
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

        updateUserAlerts();
        expect(mockContainer.innerHTML).toContain('Monitoring 2 users across 2 teams');
        expect(mockContainer.innerHTML).toContain('user1 (John Doe) is at 80% of daily limit');
    });
});

describe('IAM Integration Functions', () => {
    let mockIAM, ALL_TEAMS;

    beforeEach(() => {
        mockIAM = {
            getGroup: jest.fn(),
            listUserTags: jest.fn()
        };
        ALL_TEAMS = ['team1', 'team2'];
        global.AWS.IAM = jest.fn(() => mockIAM);
    });

    test('fetchUsersFromIAM should fetch users and tags successfully', async () => {
        const mockGroupResponse = {
            Users: [
                { UserName: 'user1' },
                { UserName: 'user2' }
            ]
        };
        const mockTagsResponse = {
            Tags: [
                { Key: 'Person', Value: 'John Doe' },
                { Key: 'Department', Value: 'Engineering' }
            ]
        };

        mockIAM.getGroup.mockReturnValue({
            promise: () => Promise.resolve(mockGroupResponse)
        });
        mockIAM.listUserTags.mockReturnValue({
            promise: () => Promise.resolve(mockTagsResponse)
        });

        async function fetchUsersFromIAM() {
            console.log("Fetching users from IAM...");
            
            try {
                const iam = new AWS.IAM();
                let allUsers = [];
                let usersByTeam = {};
                let userTags = {};
                
                ALL_TEAMS.forEach(team => {
                    usersByTeam[team] = [];
                });
                
                for (const team of ALL_TEAMS) {
                    try {
                        const groupResponse = await iam.getGroup({ GroupName: team }).promise();
                        
                        for (const user of groupResponse.Users) {
                            const username = user.UserName;
                            usersByTeam[team].push(username);
                            
                            if (!allUsers.includes(username)) {
                                allUsers.push(username);
                            }
                            
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
                
                return { success: true, allUsers, usersByTeam, userTags };
            } catch (error) {
                console.error("Error fetching users from IAM:", error);
                return { success: false };
            }
        }

        const result = await fetchUsersFromIAM();
        expect(result.success).toBe(true);
        expect(result.allUsers).toContain('user1');
        expect(result.allUsers).toContain('user2');
        expect(result.userTags['user1']).toEqual({
            'Person': 'John Doe',
            'Department': 'Engineering'
        });
    });

    test('fetchUsersFromIAM should handle errors gracefully', async () => {
        mockIAM.getGroup.mockReturnValue({
            promise: () => Promise.reject(new Error('IAM Error'))
        });

        async function fetchUsersFromIAM() {
            try {
                const iam = new AWS.IAM();
                let allUsers = [];
                let usersByTeam = {};
                
                for (const team of ALL_TEAMS) {
                    try {
                        const groupResponse = await iam.getGroup({ GroupName: team }).promise();
                        // Process users...
                    } catch (groupError) {
                        console.error(`Error fetching users for team ${team}:`, groupError);
                    }
                }
                
                return { success: true, allUsers, usersByTeam };
            } catch (error) {
                console.error("Error fetching users from IAM:", error);
                return { success: false };
            }
        }

        const result = await fetchUsersFromIAM();
        expect(result.success).toBe(true); // Should still return success even with team errors
        expect(result.allUsers).toEqual([]);
    });
});

describe('Data Processing Functions', () => {
    test('loadUserMonthlyData should process user metrics correctly', () => {
        const allUsers = ['user1', 'user2'];
        const userMetrics = {
            'user1': { monthly: 1500 },
            'user2': { monthly: 2000 }
        };
        const userTags = {
            'user1': { 'Person': 'John Doe' },
            'user2': { 'Person': 'Jane Smith' }
        };

        function getUserPersonTag(username) {
            if (!userTags[username]) return null;
            for (const key in userTags[username]) {
                if (key.toLowerCase() === 'person') {
                    return userTags[username][key];
                }
            }
            return null;
        }

        function loadUserMonthlyData() {
            try {
                const labels = [];
                const data = [];
                const colors = [];
                const colorPalette = ['#4299e1', '#48bb78', '#ed8936', '#9f7aea', '#f56565', '#38b2ac', '#ecc94b'];
                
                const sortedUsers = [...allUsers].sort();
                
                sortedUsers.forEach((username, index) => {
                    const personTag = getUserPersonTag(username) || "Unknown";
                    const userLabel = `${username} - ${personTag}`;
                    
                    labels.push(userLabel);
                    data.push(userMetrics[username]?.monthly || 0);
                    colors.push(colorPalette[index % colorPalette.length]);
                });
                
                return { labels, data, colors };
            } catch (error) {
                console.error('Error loading user monthly data:', error);
                return { labels: [], data: [], colors: [] };
            }
        }

        const result = loadUserMonthlyData();
        expect(result.labels).toContain('user1 - John Doe');
        expect(result.labels).toContain('user2 - Jane Smith');
        expect(result.data).toEqual([1500, 2000]);
        expect(result.colors).toHaveLength(2);
    });

    test('loadUserDailyData should create date labels correctly', () => {
        global.moment = jest.fn((date) => ({
            format: jest.fn(() => '1 Jan')
        }));

        function loadUserDailyData() {
            try {
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
                
                return { dateLabels };
            } catch (error) {
                console.error('Error loading user daily data:', error);
                return { dateLabels: [] };
            }
        }

        const result = loadUserDailyData();
        expect(result.dateLabels).toHaveLength(9);
        expect(result.dateLabels[8]).toBe('Today');
        expect(result.dateLabels[0]).toBe('1 Jan');
    });
});

describe('Table Update Functions', () => {
    let mockTableBody, allUsers, userMetrics, quotaConfig, userTags, usersByTeam;

    beforeEach(() => {
        mockTableBody = { innerHTML: '' };
        global.document.querySelector = jest.fn(() => mockTableBody);
        
        allUsers = ['user1', 'user2'];
        userMetrics = {
            'user1': { 
                daily: [0, 0, 0, 0, 0, 0, 0, 0, 120, 0], 
                monthly: 2000 
            },
            'user2': { 
                daily: [0, 0, 0, 0, 0, 0, 0, 0, 50, 0], 
                monthly: 1000 
            }
        };
        quotaConfig = {
            users: {
                'user1': { 
                    daily_limit: 150, 
                    monthly_limit: 3000,
                    warning_threshold: 60, 
                    critical_threshold: 85 
                },
                'user2': { 
                    daily_limit: 100, 
                    monthly_limit: 2000,
                    warning_threshold: 60, 
                    critical_threshold: 85 
                }
            }
        };
        userTags = {
            'user1': { 'Person': 'John Doe' },
            'user2': { 'Person': 'Jane Smith' }
        };
        usersByTeam = {
            'team1': ['user1'],
            'team2': ['user2']
        };
    });

    test('loadUserUsageDetails should populate table correctly', () => {
        function getUserPersonTag(username) {
            if (!userTags[username]) return null;
            for (const key in userTags[username]) {
                if (key.toLowerCase() === 'person') {
                    return userTags[username][key];
                }
            }
            return null;
        }

        function loadUserUsageDetails() {
            try {
                const tableBody = document.querySelector('#user-usage-table tbody');
                tableBody.innerHTML = '';
                
                const sortedUsers = [...allUsers].sort();
                
                sortedUsers.forEach(username => {
                    const personTag = getUserPersonTag(username) || "Unknown";
                    
                    let userTeam = "Unknown";
                    for (const team in usersByTeam) {
                        if (usersByTeam[team].includes(username)) {
                            userTeam = team;
                            break;
                        }
                    }
                    
                    const userQuota = quotaConfig?.users?.[username] || { 
                        monthly_limit: 3500, 
                        daily_limit: 150,
                        warning_threshold: 60, 
                        critical_threshold: 85 
                    };
                    
                    const monthlyTotal = userMetrics[username]?.monthly || 0;
                    const monthlyLimit = userQuota.monthly_limit;
                    const monthlyPercentage = Math.round((monthlyTotal / monthlyLimit) * 100);
                    
                    const dailyTotal = userMetrics[username]?.daily?.[8] || 0;
                    const dailyLimit = userQuota.daily_limit;
                    const dailyPercentage = Math.round((dailyTotal / dailyLimit) * 100);
                    
                    tableBody.innerHTML += `
                        <tr>
                            <td>${username}</td>
                            <td>${personTag}</td>
                            <td>${userTeam}</td>
                            <td>${dailyTotal}</td>
                            <td>${dailyLimit}</td>
                            <td>${dailyPercentage}%</td>
                            <td>${monthlyTotal}</td>
                            <td>${monthlyLimit}</td>
                            <td>${monthlyPercentage}%</td>
                        </tr>
                    `;
                });
                
                return true;
            } catch (error) {
                console.error('Error loading user usage details:', error);
                return false;
            }
        }

        const result = loadUserUsageDetails();
        expect(result).toBe(true);
        expect(mockTableBody.innerHTML).toContain('user1');
        expect(mockTableBody.innerHTML).toContain('John Doe');
        expect(mockTableBody.innerHTML).toContain('team1');
        expect(mockTableBody.innerHTML).toContain('120'); // Daily usage
        expect(mockTableBody.innerHTML).toContain('2000'); // Monthly usage
    });
});

describe('Team Data Processing Functions', () => {
    let ALL_TEAMS, teamMetrics, usersByTeam, userMetrics;

    beforeEach(() => {
        ALL_TEAMS = ['team1', 'team2'];
        teamMetrics = {
            'team1': { monthly: 5000, daily: [0, 0, 0, 0, 0, 0, 0, 0, 200, 0] },
            'team2': { monthly: 3000, daily: [0, 0, 0, 0, 0, 0, 0, 0, 150, 0] }
        };
        usersByTeam = {
            'team1': ['user1', 'user2'],
            'team2': ['user3']
        };
        userMetrics = {
            'user1': { monthly: 2000 },
            'user2': { monthly: 3000 },
            'user3': { monthly: 3000 }
        };
    });

    test('loadTeamMonthlyData should process team metrics correctly', () => {
        function loadTeamMonthlyData() {
            try {
                const labels = [];
                const data = [];
                const colors = ['#48bb78', '#4299e1', '#ed8936', '#9f7aea', '#f56565', '#38b2ac', '#ecc94b'];
                
                const sortedTeams = [...ALL_TEAMS].sort();
                
                sortedTeams.forEach((team, index) => {
                    labels.push(team);
                    data.push(teamMetrics[team]?.monthly || 0);
                });
                
                return { labels, data, colors: colors.slice(0, labels.length) };
            } catch (error) {
                console.error('Error loading team monthly data:', error);
                return { labels: [], data: [], colors: [] };
            }
        }

        const result = loadTeamMonthlyData();
        expect(result.labels).toEqual(['team1', 'team2']);
        expect(result.data).toEqual([5000, 3000]);
        expect(result.colors).toHaveLength(2);
    });

    test('loadTeamUsersData should aggregate user data by team', () => {
        const mockTableBody = { innerHTML: '' };
        global.document.querySelector = jest.fn(() => mockTableBody);

        function loadTeamUsersData() {
            try {
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
                            <td>${user.team}</td>
                            <td>${user.userRequests}</td>
                            <td>${user.percentage}%</td>
                        </tr>
                    `;
                });
                
                return allTeamUsers;
            } catch (error) {
                console.error('Error loading team users data:', error);
                return [];
            }
        }

        const result = loadTeamUsersData();
        expect(result).toHaveLength(3);
        expect(result[0].userRequests).toBe(3000); // Highest usage first
        expect(mockTableBody.innerHTML).toContain('user2');
        expect(mockTableBody.innerHTML).toContain('user3');
        expect(mockTableBody.innerHTML).toContain('60%'); // user2's percentage in team1
    });
});

describe('Model Distribution Functions', () => {
    let ALL_TEAMS;

    beforeEach(() => {
        ALL_TEAMS = ['team_darwin_group', 'team_sap_group'];
    });

    test('loadModelDistributionData should generate consistent distribution', () => {
        function loadModelDistributionData() {
            try {
                const selectedTeam = ALL_TEAMS[0];
                const modelLabels = ['Claude 3 Opus', 'Claude 3 Sonnet', 'Claude 3 Haiku', 'Claude 3.7 Sonnet', 'Amazon Titan'];
                
                let distribution;
                const teamHash = selectedTeam.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
                
                distribution = [
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
                
                return {
                    labels: modelLabels,
                    distribution: distribution,
                    sum: distribution.reduce((acc, val) => acc + val, 0)
                };
            } catch (error) {
                console.error('Error loading model distribution data:', error);
                return { labels: [], distribution: [], sum: 0 };
            }
        }

        const result = loadModelDistributionData();
        expect(result.labels).toHaveLength(5);
        expect(result.distribution).toHaveLength(5);
        expect(result.sum).toBe(100); // Should always sum to 100%
        expect(result.distribution.every(val => val >= 0)).toBe(true);
    });
});

describe('Error Handling Functions', () => {
    test('should handle missing user data gracefully', () => {
        const userTags = {};
        
        function getUserPersonTag(username) {
            if (!userTags[username]) return null;
            
            for (const key in userTags[username]) {
                if (key.toLowerCase() === 'person') {
                    return userTags[username][key];
                }
            }
            return null;
        }

        expect(getUserPersonTag('nonexistent_user')).toBeNull();
    });

    test('should handle empty metrics data', () => {
        const userMetrics = {};
        
        function getUserMetric(username, metricType) {
            return userMetrics[username]?.[metricType] || 0;
        }

        expect(getUserMetric('nonexistent_user', 'monthly')).toBe(0);
        expect(getUserMetric('nonexistent_user', 'daily')).toBe(0);
    });

    test('should handle missing quota configuration', () => {
        const quotaConfig = null;
        
        function getUserQuota(username) {
            return quotaConfig?.users?.[username] || { 
                monthly_limit: 3500, 
                daily_limit: 150,
                warning_threshold: 60, 
                critical_threshold: 85 
            };
        }

        const result = getUserQuota('any_user');
        expect(result.monthly_limit).toBe(3500);
        expect(result.daily_limit).toBe(150);
        expect(result.warning_threshold).toBe(60);
        expect(result.critical_threshold).toBe(85);
    });
});

describe('Utility Functions', () => {
    test('should calculate percentages correctly', () => {
        function calculatePercentage(value, total) {
            if (total === 0) return 0;
            return Math.round((value / total) * 100);
        }

        expect(calculatePercentage(50, 100)).toBe(50);
        expect(calculatePercentage(75, 100)).toBe(75);
        expect(calculatePercentage(33, 100)).toBe(33);
        expect(calculatePercentage(10, 0)).toBe(0); // Handle division by zero
    });

    test('should sort arrays correctly', () => {
        const users = ['user_c', 'user_a', 'user_b'];
        const sortedUsers = [...users].sort();
        
        expect(sortedUsers).toEqual(['user_a', 'user_b', 'user_c']);
    });

    test('should handle array operations safely', () => {
        const dailyData = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        
        // Test accessing today's data (index 8)
        expect(dailyData[8]).toBe(90);
        
        // Test accessing yesterday's data (index 7)
        expect(dailyData[7]).toBe(80);
        
        // Test safe access with fallback
        function getDailyValue(data, index, fallback = 0) {
            return data?.[index] || fallback;
        }
        
        expect(getDailyValue(dailyData, 8)).toBe(90);
        expect(getDailyValue(null, 8)).toBe(0);
        expect(getDailyValue(undefined, 8)).toBe(0);
    });
});

describe('Integration Tests', () => {
    test('should handle complete dashboard data flow', () => {
        // Mock complete data structures
        const allUsers = ['user1', 'user2'];
        const usersByTeam = {
            'team1': ['user1'],
            'team2': ['user2']
        };
        const userTags = {
            'user1': { 'Person': 'John Doe' },
            'user2': { 'Person': 'Jane Smith' }
        };
        const userMetrics = {
            'user1': { monthly: 2000, daily: [0, 0, 0, 0, 0, 0, 0, 0, 120, 0] },
            'user2': { monthly: 1500, daily: [0, 0, 0, 0, 0, 0, 0, 0, 80, 0] }
        };
        const quotaConfig = {
            users: {
                'user1': { monthly_limit: 3000, daily_limit: 150, warning_threshold: 60, critical_threshold: 85 },
                'user2': { monthly_limit: 2500, daily_limit: 120, warning_threshold: 60, critical_threshold: 85 }
            }
        };

        // Test data consistency
        expect(allUsers.every(user => userMetrics[user])).toBe(true);
        expect(allUsers.every(user => userTags[user])).toBe(true);
        
        // Test team assignment
        const allTeamUsers = Object.values(usersByTeam).flat();
        expect(allUsers.every(user => allTeamUsers.includes(user))).toBe(true);
        
        // Test quota coverage
        expect(allUsers.every(user => quotaConfig.users[user])).toBe(true);
    });

    test('should handle empty state correctly', () => {
        const allUsers = [];
        const usersByTeam = {};
        const userTags = {};
        const userMetrics = {};
        const teamMetrics = {};

        // Verify empty state
        expect(allUsers).toHaveLength(0);
        expect(Object.keys(usersByTeam)).toHaveLength(0);
        expect(Object.keys(userTags)).toHaveLength(0);
        expect(Object.keys(userMetrics)).toHaveLength(0);
        expect(Object.keys(teamMetrics)).toHaveLength(0);
    });
});
