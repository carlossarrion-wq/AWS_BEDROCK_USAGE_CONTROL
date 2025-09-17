// Cost Analysis Functions for AWS Bedrock Usage Dashboard

// Global variables for cost analysis
let costRequestsData = {};

// Cost Analysis Functions
function generateBackfillCostData() {
    const now = new Date();
    costData = {};
    costRequestsData = {
        dailyCosts: [],
        dailyRequests: [],
        costPerRequest: [],
        correlationData: []
    };
    
    BEDROCK_SERVICES.forEach((service, serviceIndex) => {
        costData[service] = [];
        
        // Generate realistic cost data for last 10 days
        for (let i = 9; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            
            // Base cost varies by service type
            let baseCost = 0;
            switch (service) {
                case 'Amazon Bedrock':
                    baseCost = Math.random() * 5 + 2; // $2-7
                    break;
                case 'Claude 3.7 Sonnet (Bedrock Edition)':
                    baseCost = Math.random() * 25 + 15; // $15-40
                    break;
                case 'Claude 3 Sonnet (Bedrock Edition)':
                    baseCost = Math.random() * 15 + 8; // $8-23
                    break;
                case 'Claude 3 Haiku (Bedrock Edition)':
                    baseCost = Math.random() * 8 + 3; // $3-11
                    break;
                case 'Claude 3 Opus (Bedrock Edition)':
                    baseCost = Math.random() * 35 + 20; // $20-55
                    break;
                case 'Amazon Titan Text (Bedrock Edition)':
                    baseCost = Math.random() * 6 + 2; // $2-8
                    break;
            }
            
            // Add some variation based on day of week (lower on weekends)
            const dayOfWeek = date.getDay();
            if (dayOfWeek === 0 || dayOfWeek === 6) {
                baseCost *= 0.6; // 40% reduction on weekends
            }
            
            // Add some random variation
            baseCost *= (0.8 + Math.random() * 0.4); // ±20% variation
            
            costData[service].push(parseFloat(baseCost.toFixed(2)));
        }
    });
    
    // Generate realistic request data that correlates with costs
    generateRequestsData();
    
    console.log('Generated backfill cost data:', costData);
    console.log('Generated requests correlation data:', costRequestsData);
}

// Generate realistic request data that correlates with cost data
function generateRequestsData() {
    const dailyCosts = Array(10).fill(0);
    
    // Calculate daily cost totals
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        for (let i = 0; i < 10; i++) {
            dailyCosts[i] += serviceCosts[i] || 0;
        }
    });
    
    costRequestsData.dailyCosts = dailyCosts;
    costRequestsData.dailyRequests = [];
    costRequestsData.costPerRequest = [];
    costRequestsData.correlationData = [];
    
    // Generate request data with realistic correlation to costs
    for (let i = 0; i < 10; i++) {
        const cost = dailyCosts[i];
        
        // Base requests calculation with some correlation to cost
        // Higher costs generally mean more requests, but with variation for different service types
        let baseRequests = Math.floor(cost * (800 + Math.random() * 400)); // 800-1200 requests per dollar
        
        // Add day-of-week variation (lower on weekends)
        const date = new Date();
        date.setDate(date.getDate() - (9 - i));
        const dayOfWeek = date.getDay();
        if (dayOfWeek === 0 || dayOfWeek === 6) {
            baseRequests *= 0.7; // 30% reduction on weekends
        }
        
        // Add some random variation to make it more realistic
        baseRequests *= (0.85 + Math.random() * 0.3); // ±15% variation
        baseRequests = Math.max(1, Math.floor(baseRequests)); // Ensure at least 1 request
        
        costRequestsData.dailyRequests.push(baseRequests);
        
        // Calculate cost per request
        const costPerRequest = baseRequests > 0 ? cost / baseRequests : 0;
        costRequestsData.costPerRequest.push(costPerRequest);
        
        // Create correlation data point
        costRequestsData.correlationData.push({
            x: baseRequests,
            y: cost,
            date: moment(date).format('D MMM')
        });
    }
}

// Load cost analysis data
async function loadCostAnalysisData() {
    try {
        updateConnectionStatus('connecting', 'Loading cost analysis data...');
        
        // Show loading indicators
        showCostLoadingIndicators();
        
        // For prototype, generate backfill data
        // In production, this would fetch from AWS Cost Explorer API
        generateBackfillCostData();
        
        // Load cost analysis sections
        loadCostAnalysisTable();
        loadCostVsRequestsTable();
        loadCostAnalysisCharts();
        updateCostAnalysisAlerts();
        
        updateConnectionStatus('connected', 'Cost analysis data loaded successfully');
        
    } catch (error) {
        console.error('Error loading cost analysis data:', error);
        showCostError('Failed to load cost analysis data: ' + error.message);
        updateConnectionStatus('error', 'Failed to load cost data');
    }
}

// Show cost loading indicators
function showCostLoadingIndicators() {
    document.getElementById('cost-alerts-container').innerHTML = `
        <div class="alert info">
            <div class="loading-spinner"></div>
            <strong>Loading:</strong> Fetching cost data from AWS Cost Explorer...
        </div>
    `;
    
    document.querySelector('#cost-analysis-table tbody').innerHTML = `
        <tr>
            <td colspan="12">
                <div class="loading-spinner"></div>
                Loading cost analysis data...
            </td>
        </tr>
    `;
}

// Show cost error
function showCostError(message) {
    const alertsContainer = document.getElementById('cost-alerts-container');
    alertsContainer.innerHTML = `
        <div class="alert critical">
            <strong>Error:</strong> ${message}
        </div>
    `;
}

// Load cost analysis table
function loadCostAnalysisTable() {
    const tableBody = document.querySelector('#cost-analysis-table tbody');
    tableBody.innerHTML = '';
    
    // Update table headers with actual dates
    updateCostAnalysisHeaders();
    
    // Array to store daily totals
    const dailyTotals = Array(10).fill(0);
    
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        
        let rowHtml = `
            <tr>
                <td><strong>${service}</strong></td>
        `;
        
        let serviceTotal = 0;
        for (let i = 0; i < 10; i++) {
            const cost = serviceCosts[i] || 0;
            rowHtml += `<td>$${cost.toFixed(2)}</td>`;
            
            // Add to daily totals and service total
            dailyTotals[i] += cost;
            serviceTotal += cost;
        }
        
        rowHtml += `<td><strong>$${serviceTotal.toFixed(2)}</strong></td>`;
        rowHtml += '</tr>';
        
        tableBody.innerHTML += rowHtml;
    });
    
    // Add totals row
    if (BEDROCK_SERVICES.length > 0) {
        let totalsRowHtml = `
            <tr style="border-top: 2px solid #1e4a72; background-color: #f8f9fa;">
                <td style="font-weight: bold;">TOTAL</td>
        `;
        
        let grandTotal = 0;
        for (let i = 0; i < 10; i++) {
            totalsRowHtml += `<td style="font-weight: bold;">$${dailyTotals[i].toFixed(2)}</td>`;
            grandTotal += dailyTotals[i];
        }
        
        totalsRowHtml += `<td style="font-weight: bold; color: #1e4a72;">$${grandTotal.toFixed(2)}</td>`;
        totalsRowHtml += '</tr>';
        
        tableBody.innerHTML += totalsRowHtml;
    }
}

// Update cost analysis table headers with actual dates
function updateCostAnalysisHeaders() {
    for (let i = 0; i < 10; i++) {
        const date = new Date();
        const daysBack = 9 - i;
        date.setDate(date.getDate() - daysBack);
        
        const headerElement = document.getElementById(`cost-day-${daysBack}`);
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

// Load cost analysis charts
function loadCostAnalysisCharts() {
    // Calculate daily totals for trend chart
    const dailyTotals = Array(10).fill(0);
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        for (let i = 0; i < 10; i++) {
            dailyTotals[i] += serviceCosts[i] || 0;
        }
    });
    
    // Update cost trend chart
    updateCostTrendChart(dailyTotals);
    
    // Calculate service totals for distribution chart
    const serviceTotals = BEDROCK_SERVICES.map(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        return serviceCosts.reduce((sum, cost) => sum + cost, 0);
    });
    
    // Update service cost distribution chart
    updateServiceCostChart(serviceTotals);
    
    // Update cost per request and correlation charts
    updateCostPerRequestChart(dailyTotals);
    updateCostRequestsCorrelationChart(dailyTotals);
}

// Update cost analysis alerts
function updateCostAnalysisAlerts() {
    const alertsContainer = document.getElementById('cost-alerts-container');
    alertsContainer.innerHTML = '';
    
    // Calculate total cost for last 10 days
    let totalCost = 0;
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        totalCost += serviceCosts.reduce((sum, cost) => sum + cost, 0);
    });
    
    // Calculate today's cost
    let todayCost = 0;
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        todayCost += serviceCosts[9] || 0; // Today is index 9
    });
    
    // Calculate yesterday's cost for comparison
    let yesterdayCost = 0;
    BEDROCK_SERVICES.forEach(service => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        yesterdayCost += serviceCosts[8] || 0; // Yesterday is index 8
    });
    
    // Calculate average daily cost
    const avgDailyCost = totalCost / 10;
    
    // General info alert
    alertsContainer.innerHTML += `
        <div class="alert info">
            <strong>Cost Summary:</strong> Total cost for last 10 days: $${totalCost.toFixed(2)} | Average daily cost: $${avgDailyCost.toFixed(2)}
        </div>
    `;
    
    // Today vs yesterday comparison
    const costChange = todayCost - yesterdayCost;
    const costChangePercent = yesterdayCost > 0 ? ((costChange / yesterdayCost) * 100) : 0;
    
    if (Math.abs(costChangePercent) > 20) {
        const alertClass = costChange > 0 ? 'critical' : 'success';
        const changeDirection = costChange > 0 ? 'increased' : 'decreased';
        const changeIcon = costChange > 0 ? '📈' : '📉';
        
        alertsContainer.innerHTML += `
            <div class="alert ${alertClass}">
                <strong>${changeIcon} Cost Alert:</strong> Today's cost ($${todayCost.toFixed(2)}) has ${changeDirection} by ${Math.abs(costChangePercent).toFixed(1)}% compared to yesterday ($${yesterdayCost.toFixed(2)})
            </div>
        `;
    }
    
    // High cost service alert
    const highestCostService = BEDROCK_SERVICES.reduce((highest, service) => {
        const serviceCosts = costData[service] || Array(10).fill(0);
        const serviceTotal = serviceCosts.reduce((sum, cost) => sum + cost, 0);
        const currentHighestCosts = costData[highest] || Array(10).fill(0);
        const currentHighestTotal = currentHighestCosts.reduce((sum, cost) => sum + cost, 0);
        
        return serviceTotal > currentHighestTotal ? service : highest;
    }, BEDROCK_SERVICES[0]);
    
    const highestServiceCosts = costData[highestCostService] || Array(10).fill(0);
    const highestServiceTotal = highestServiceCosts.reduce((sum, cost) => sum + cost, 0);
    const highestServicePercent = ((highestServiceTotal / totalCost) * 100);
    
    if (highestServicePercent > 40) {
        alertsContainer.innerHTML += `
            <div class="alert">
                <strong>💰 High Usage:</strong> ${highestCostService} accounts for ${highestServicePercent.toFixed(1)}% of total costs ($${highestServiceTotal.toFixed(2)})
            </div>
        `;
    }
}

// Load cost vs requests table
function loadCostVsRequestsTable() {
    const tableBody = document.querySelector('#cost-vs-requests-table tbody');
    tableBody.innerHTML = '';
    
    // Use enhanced cost analysis data if available
    let dailyCosts, dailyRequests;
    
    if (costRequestsData && costRequestsData.dailyCosts) {
        dailyCosts = costRequestsData.dailyCosts;
        dailyRequests = costRequestsData.dailyRequests;
    } else {
        // Fallback to calculating from service costs and user metrics
        dailyCosts = Array(10).fill(0);
        BEDROCK_SERVICES.forEach(service => {
            const serviceCosts = costData[service] || Array(10).fill(0);
            for (let i = 0; i < 10; i++) {
                dailyCosts[i] += serviceCosts[i] || 0;
            }
        });
        
        // Calculate daily totals for requests (from existing metrics or generate fallback)
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
                const cost = dailyCosts[i];
                dailyRequests[i] = Math.floor(cost * (900 + Math.random() * 200)); // 900-1100 requests per dollar
            }
        }
    }
    
    // Generate table rows for last 10 days
    for (let i = 0; i < 10; i++) {
        const date = new Date();
        const daysBack = 9 - i;
        date.setDate(date.getDate() - daysBack);
        
        const cost = dailyCosts[i];
        const requests = dailyRequests[i];
        const costPerRequest = requests > 0 ? cost / requests : 0;
        
        // Calculate efficiency rating with enhanced thresholds
        let efficiencyRating = 'N/A';
        let efficiencyClass = '';
        if (requests > 0) {
            if (costPerRequest < 0.001) {
                efficiencyRating = 'Excellent';
                efficiencyClass = 'success';
            } else if (costPerRequest < 0.002) {
                efficiencyRating = 'Very Good';
                efficiencyClass = 'info';
            } else if (costPerRequest < 0.005) {
                efficiencyRating = 'Good';
                efficiencyClass = '';
            } else if (costPerRequest < 0.01) {
                efficiencyRating = 'Fair';
                efficiencyClass = 'warning';
            } else {
                efficiencyRating = 'Poor';
                efficiencyClass = 'critical';
            }
        }
        
        // Calculate trends (compare with previous day)
        let costTrend = '-';
        let requestTrend = '-';
        if (i > 0) {
            const prevCost = dailyCosts[i - 1];
            const prevRequests = dailyRequests[i - 1];
            
            if (prevCost > 0) {
                const costChange = ((cost - prevCost) / prevCost) * 100;
                if (Math.abs(costChange) > 5) {
                    costTrend = costChange > 0 ? `+${costChange.toFixed(1)}%` : `${costChange.toFixed(1)}%`;
                } else {
                    costTrend = '~';
                }
            }
            
            if (prevRequests > 0) {
                const requestChange = ((requests - prevRequests) / prevRequests) * 100;
                if (Math.abs(requestChange) > 5) {
                    requestTrend = requestChange > 0 ? `+${requestChange.toFixed(1)}%` : `${requestChange.toFixed(1)}%`;
                } else {
                    requestTrend = '~';
                }
            }
        }
        
        const dateStr = daysBack === 0 ? 'Today' : moment(date).format('D MMM');
        const dayOfWeek = date.getDay();
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
        const weekendClass = isWeekend ? 'weekend' : '';
        
        // Style trends with colors
        const costTrendStyle = costTrend.startsWith('+') ? 'color: #e74c3c;' : 
                             costTrend.startsWith('-') ? 'color: #27ae60;' : '';
        const requestTrendStyle = requestTrend.startsWith('+') ? 'color: #27ae60;' : 
                                requestTrend.startsWith('-') ? 'color: #e74c3c;' : '';
        
        // Add efficiency indicator icon
        let efficiencyIcon = '';
        switch (efficiencyClass) {
            case 'success':
                efficiencyIcon = '🟢';
                break;
            case 'info':
                efficiencyIcon = '🔵';
                break;
            case 'warning':
                efficiencyIcon = '🟡';
                break;
            case 'critical':
                efficiencyIcon = '🔴';
                break;
            default:
                efficiencyIcon = '⚪';
        }
        
        tableBody.innerHTML += `
            <tr class="${weekendClass}">
                <td><strong>${dateStr}</strong></td>
                <td>$${cost.toFixed(2)}</td>
                <td>${requests.toLocaleString()}</td>
                <td><strong>$${costPerRequest.toFixed(4)}</strong></td>
                <td><span class="status-badge ${efficiencyClass}">${efficiencyIcon} ${efficiencyRating}</span></td>
                <td style="${costTrendStyle}">${costTrend}</td>
                <td style="${requestTrendStyle}">${requestTrend}</td>
            </tr>
        `;
    }
    
    // Add summary row with enhanced statistics
    const totalCost = dailyCosts.reduce((sum, cost) => sum + cost, 0);
    const totalRequests = dailyRequests.reduce((sum, requests) => sum + requests, 0);
    const avgCostPerRequest = totalRequests > 0 ? totalCost / totalRequests : 0;
    
    // Calculate overall trends (first vs last day)
    const firstDayCost = dailyCosts[0];
    const lastDayCost = dailyCosts[9];
    const firstDayRequests = dailyRequests[0];
    const lastDayRequests = dailyRequests[9];
    
    let overallCostTrend = '-';
    let overallRequestTrend = '-';
    
    if (firstDayCost > 0) {
        const costChange = ((lastDayCost - firstDayCost) / firstDayCost) * 100;
        overallCostTrend = costChange > 0 ? `+${costChange.toFixed(1)}%` : `${costChange.toFixed(1)}%`;
    }
    
    if (firstDayRequests > 0) {
        const requestChange = ((lastDayRequests - firstDayRequests) / firstDayRequests) * 100;
        overallRequestTrend = requestChange > 0 ? `+${requestChange.toFixed(1)}%` : `${requestChange.toFixed(1)}%`;
    }
    
    // Calculate overall efficiency rating
    let overallEfficiencyRating = 'N/A';
    let overallEfficiencyClass = '';
    let overallEfficiencyIcon = '⚪';
    
    if (totalRequests > 0) {
        if (avgCostPerRequest < 0.001) {
            overallEfficiencyRating = 'Excellent';
            overallEfficiencyClass = 'success';
            overallEfficiencyIcon = '🟢';
        } else if (avgCostPerRequest < 0.002) {
            overallEfficiencyRating = 'Very Good';
            overallEfficiencyClass = 'info';
            overallEfficiencyIcon = '🔵';
        } else if (avgCostPerRequest < 0.005) {
            overallEfficiencyRating = 'Good';
            overallEfficiencyClass = '';
            overallEfficiencyIcon = '⚪';
        } else if (avgCostPerRequest < 0.01) {
            overallEfficiencyRating = 'Fair';
            overallEfficiencyClass = 'warning';
            overallEfficiencyIcon = '🟡';
        } else {
            overallEfficiencyRating = 'Poor';
            overallEfficiencyClass = 'critical';
            overallEfficiencyIcon = '🔴';
        }
    }
    
    tableBody.innerHTML += `
        <tr style="border-top: 2px solid #1e4a72; background-color: #f8f9fa;">
            <td style="font-weight: bold;">TOTALS</td>
            <td style="font-weight: bold;">$${totalCost.toFixed(2)}</td>
            <td style="font-weight: bold;">${totalRequests.toLocaleString()}</td>
            <td style="font-weight: bold; color: #1e4a72;">$${avgCostPerRequest.toFixed(4)}</td>
            <td style="font-weight: bold;"><span class="status-badge ${overallEfficiencyClass}">${overallEfficiencyIcon} ${overallEfficiencyRating}</span></td>
            <td style="font-weight: bold;">${overallCostTrend}</td>
            <td style="font-weight: bold;">${overallRequestTrend}</td>
        </tr>
    `;
}
