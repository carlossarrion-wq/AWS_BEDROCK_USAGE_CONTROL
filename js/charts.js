// Chart Update Functions for AWS Bedrock Usage Dashboard

function updateUserMonthlyChart(data) {
    if (userMonthlyChart) {
        userMonthlyChart.data = data;
        userMonthlyChart.update();
    } else {
        userMonthlyChart = new Chart(
            document.getElementById('user-monthly-chart'),
            {
                type: 'bar',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Monthly Bedrock Requests by User'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Requests'
                            }
                        }
                    }
                }
            }
        );
    }
}

function updateUserDailyChart(data) {
    if (userDailyChart) {
        userDailyChart.data = data;
        userDailyChart.update();
    } else {
        userDailyChart = new Chart(
            document.getElementById('user-daily-chart'),
            {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Daily Usage Trend'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Requests'
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

function updateAccessMethodChart(data) {
    if (accessMethodChart) {
        accessMethodChart.data = data;
        accessMethodChart.update();
    } else {
        accessMethodChart = new Chart(
            document.getElementById('access-method-chart'),
            {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        },
                        title: {
                            display: true,
                            text: 'Access Method Distribution Today'
                        }
                    }
                }
            }
        );
    }
}

function updateTeamMonthlyChart(data) {
    if (teamMonthlyChart) {
        teamMonthlyChart.data = data;
        teamMonthlyChart.update();
    } else {
        teamMonthlyChart = new Chart(
            document.getElementById('team-monthly-chart'),
            {
                type: 'bar',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Monthly Bedrock Requests by Team'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Requests'
                            }
                        }
                    }
                }
            }
        );
    }
}

function updateTeamDailyChart(data) {
    if (teamDailyChart) {
        teamDailyChart.data = data;
        teamDailyChart.update();
    } else {
        teamDailyChart = new Chart(
            document.getElementById('team-daily-chart'),
            {
                type: 'line',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Daily Team Usage Trend'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Requests'
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

function updateModelDistributionChart(data) {
    if (modelDistributionChart) {
        modelDistributionChart.data = data;
        modelDistributionChart.update();
    } else {
        modelDistributionChart = new Chart(
            document.getElementById('model-distribution-chart'),
            {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 12
                            }
                        },
                        title: {
                            display: true,
                            text: 'Model Usage Distribution (%)'
                        }
                    }
                }
            }
        );
    }
}

function updateCostTrendChart(dailyTotals) {
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
            label: 'Total Daily Cost',
            data: dailyTotals,
            backgroundColor: '#27ae60',
            borderColor: '#27ae60',
            borderWidth: 2,
            fill: false,
            tension: 0.4
        }]
    };
    
    if (costTrendChart) {
        costTrendChart.data = chartData;
        costTrendChart.update();
    } else {
        costTrendChart = new Chart(
            document.getElementById('cost-trend-chart'),
            {
                type: 'line',
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
                            text: 'Daily Cost Trend - Last 10 Days'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Cost (USD)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
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

function updateServiceCostChart(serviceTotals) {
    const colors = CHART_COLORS.services;
    
    const chartData = {
        labels: BEDROCK_SERVICES,
        datasets: [{
            label: 'Service Cost Distribution',
            data: serviceTotals,
            backgroundColor: colors.slice(0, BEDROCK_SERVICES.length),
            borderWidth: 1
        }]
    };
    
    if (serviceCostChart) {
        serviceCostChart.data = chartData;
        serviceCostChart.update();
    } else {
        serviceCostChart = new Chart(
            document.getElementById('service-cost-chart'),
            {
                type: 'pie',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 12,
                                generateLabels: function(chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            return {
                                                text: `${label}: $${value.toFixed(2)}`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                strokeStyle: data.datasets[0].backgroundColor[i],
                                                lineWidth: 1,
                                                hidden: false,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: 'Service Cost Distribution (Last 10 Days)'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: $${value.toFixed(2)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            }
        );
    }
}

function updateCostPerRequestChart(dailyTotals) {
    // Use enhanced cost analysis data if available, otherwise fallback to user metrics
    let costPerRequestData;
    let dailyRequests;
    
    if (typeof costRequestsData !== 'undefined' && costRequestsData.costPerRequest) {
        // Use the enhanced cost analysis data
        costPerRequestData = costRequestsData.costPerRequest;
        dailyRequests = costRequestsData.dailyRequests;
    } else {
        // Fallback to calculating from user metrics
        dailyRequests = Array(10).fill(0);
        if (typeof allUsers !== 'undefined' && allUsers.length > 0) {
            allUsers.forEach(username => {
                const userDailyData = userMetrics[username]?.daily || Array(10).fill(0);
                for (let i = 0; i < 10; i++) {
                    dailyRequests[i] += userDailyData[i] || 0;
                }
            });
        } else {
            // Generate fallback request data if no user data available
            for (let i = 0; i < 10; i++) {
                const cost = dailyTotals[i];
                dailyRequests[i] = Math.floor(cost * (900 + Math.random() * 200)); // 900-1100 requests per dollar
            }
        }
        
        // Calculate cost per request for each day
        costPerRequestData = dailyTotals.map((cost, index) => {
            const requests = dailyRequests[index];
            return requests > 0 ? cost / requests : 0;
        });
    }
    
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
    
    // Add trend line calculation
    const trendData = calculateTrendLine(costPerRequestData);
    
    const chartData = {
        labels: dateLabels,
        datasets: [{
            label: 'Cost per Request',
            data: costPerRequestData,
            backgroundColor: '#e67e22',
            borderColor: '#e67e22',
            borderWidth: 3,
            fill: false,
            tension: 0.4,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointBackgroundColor: '#e67e22',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }, {
            label: 'Trend',
            data: trendData,
            backgroundColor: 'rgba(231, 126, 34, 0.1)',
            borderColor: 'rgba(231, 126, 34, 0.5)',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 0
        }]
    };
    
    if (costPerRequestChart) {
        costPerRequestChart.data = chartData;
        costPerRequestChart.update();
    } else {
        costPerRequestChart = new Chart(
            document.getElementById('cost-per-request-chart'),
            {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                boxWidth: 12,
                                padding: 15
                            }
                        },
                        title: {
                            display: true,
                            text: 'Cost per Request Trend - Last 10 Days',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    if (context.datasetIndex === 0) {
                                        const requests = dailyRequests[context.dataIndex];
                                        return [
                                            `Cost per Request: $${context.parsed.y.toFixed(4)}`,
                                            `Total Requests: ${requests.toLocaleString()}`
                                        ];
                                    } else {
                                        return `Trend: $${context.parsed.y.toFixed(4)}`;
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Cost per Request (USD)',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(4);
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Date',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            }
        );
    }
}

function updateCostRequestsCorrelationChart(dailyTotals) {
    // Use enhanced cost analysis data if available, otherwise fallback to user metrics
    let scatterData;
    let dailyRequests;
    
    if (typeof costRequestsData !== 'undefined' && costRequestsData.correlationData) {
        // Use the enhanced cost analysis correlation data
        scatterData = costRequestsData.correlationData;
        dailyRequests = costRequestsData.dailyRequests;
    } else {
        // Fallback to calculating from user metrics
        dailyRequests = Array(10).fill(0);
        if (typeof allUsers !== 'undefined' && allUsers.length > 0) {
            allUsers.forEach(username => {
                const userDailyData = userMetrics[username]?.daily || Array(10).fill(0);
                for (let i = 0; i < 10; i++) {
                    dailyRequests[i] += userDailyData[i] || 0;
                }
            });
        } else {
            // Generate fallback request data if no user data available
            for (let i = 0; i < 10; i++) {
                const cost = dailyTotals[i];
                dailyRequests[i] = Math.floor(cost * (900 + Math.random() * 200)); // 900-1100 requests per dollar
            }
        }
        
        // Create scatter plot data
        scatterData = dailyTotals.map((cost, index) => {
            const date = new Date();
            date.setDate(date.getDate() - (9 - index));
            return {
                x: dailyRequests[index],
                y: cost,
                date: moment(date).format('D MMM')
            };
        });
    }
    
    // Calculate correlation coefficient
    const correlation = calculateCorrelation(scatterData);
    
    // Calculate trend line for correlation
    const trendLine = calculateCorrelationTrendLine(scatterData);
    
    const chartData = {
        datasets: [{
            label: 'Daily Data Points',
            data: scatterData,
            backgroundColor: '#3498db',
            borderColor: '#3498db',
            borderWidth: 2,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointBackgroundColor: '#3498db',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2
        }, {
            label: `Trend Line (R² = ${correlation.rSquared.toFixed(3)})`,
            data: trendLine,
            backgroundColor: 'rgba(52, 152, 219, 0.1)',
            borderColor: 'rgba(52, 152, 219, 0.7)',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 0,
            showLine: true,
            type: 'line'
        }]
    };
    
    if (costRequestsCorrelationChart) {
        costRequestsCorrelationChart.data = chartData;
        costRequestsCorrelationChart.update();
    } else {
        costRequestsCorrelationChart = new Chart(
            document.getElementById('cost-requests-correlation-chart'),
            {
                type: 'scatter',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                boxWidth: 12,
                                padding: 15
                            }
                        },
                        title: {
                            display: true,
                            text: 'Cost vs Requests Correlation Analysis',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    if (context.datasetIndex === 0) {
                                        const point = scatterData[context.dataIndex];
                                        return [
                                            `Date: ${point.date}`,
                                            `Requests: ${context.parsed.x.toLocaleString()}`,
                                            `Cost: $${context.parsed.y.toFixed(2)}`,
                                            `Cost/Request: $${(context.parsed.y / context.parsed.x).toFixed(4)}`
                                        ];
                                    } else {
                                        return `Trend: $${context.parsed.y.toFixed(2)}`;
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Total Requests',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Total Cost (USD)',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'point'
                    }
                }
            }
        );
    }
}

// Helper function to calculate trend line for time series data
function calculateTrendLine(data) {
    const n = data.length;
    const xValues = Array.from({length: n}, (_, i) => i);
    const yValues = data;
    
    // Calculate linear regression
    const sumX = xValues.reduce((sum, x) => sum + x, 0);
    const sumY = yValues.reduce((sum, y) => sum + y, 0);
    const sumXY = xValues.reduce((sum, x, i) => sum + x * yValues[i], 0);
    const sumXX = xValues.reduce((sum, x) => sum + x * x, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    
    return xValues.map(x => slope * x + intercept);
}

// Helper function to calculate correlation coefficient and trend line for scatter plot
function calculateCorrelation(data) {
    const n = data.length;
    const xValues = data.map(point => point.x);
    const yValues = data.map(point => point.y);
    
    const sumX = xValues.reduce((sum, x) => sum + x, 0);
    const sumY = yValues.reduce((sum, y) => sum + y, 0);
    const sumXY = xValues.reduce((sum, x, i) => sum + x * yValues[i], 0);
    const sumXX = xValues.reduce((sum, x) => sum + x * x, 0);
    const sumYY = yValues.reduce((sum, y) => sum + y * y, 0);
    
    const meanX = sumX / n;
    const meanY = sumY / n;
    
    // Calculate correlation coefficient
    const numerator = sumXY - n * meanX * meanY;
    const denominator = Math.sqrt((sumXX - n * meanX * meanX) * (sumYY - n * meanY * meanY));
    const correlation = denominator !== 0 ? numerator / denominator : 0;
    const rSquared = correlation * correlation;
    
    return {
        correlation,
        rSquared,
        meanX,
        meanY
    };
}

// Helper function to calculate trend line for correlation chart
function calculateCorrelationTrendLine(data) {
    const xValues = data.map(point => point.x);
    const yValues = data.map(point => point.y);
    const n = data.length;
    
    // Calculate linear regression
    const sumX = xValues.reduce((sum, x) => sum + x, 0);
    const sumY = yValues.reduce((sum, y) => sum + y, 0);
    const sumXY = xValues.reduce((sum, x, i) => sum + x * yValues[i], 0);
    const sumXX = xValues.reduce((sum, x) => sum + x * x, 0);
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    
    // Create trend line points
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    
    return [
        { x: minX, y: slope * minX + intercept },
        { x: maxX, y: slope * maxX + intercept }
    ];
}
