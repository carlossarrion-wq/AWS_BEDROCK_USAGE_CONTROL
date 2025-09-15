# AWS Bedrock Usage Dashboard - Unit Tests

This directory contains comprehensive unit tests for all JavaScript functions in the AWS Bedrock Usage Dashboard (`bedrock_usage_dashboard.html`).

## Overview

The test suite covers all major functionality of the dashboard including:

- **Configuration and Constants** - Region settings, team definitions
- **Tab Management** - UI tab switching functionality
- **User Tag Functions** - User metadata handling
- **Quota Configuration** - Limit and threshold management
- **Authentication** - Login/logout and credential management
- **Date Utilities** - Date manipulation functions
- **Data Loading** - AWS data fetching and processing
- **AWS CloudWatch Integration** - Metrics retrieval and processing
- **Chart Updates** - Chart.js integration and updates
- **Alert Management** - User and team alert generation
- **IAM Integration** - User and group management
- **Data Processing** - User and team data aggregation
- **Table Updates** - Dynamic table population
- **Model Distribution** - Usage distribution calculations
- **Error Handling** - Graceful error management
- **Utility Functions** - Helper functions and calculations
- **Integration Tests** - End-to-end workflow testing

## Test Structure

```
tests/
├── dashboard.test.js    # Main test file with all test suites
├── setup.js            # Jest setup and global mocks
└── README.md           # This file
```

## Prerequisites

Before running the tests, ensure you have Node.js installed (version 14 or higher recommended).

## Installation

1. Install dependencies:
```bash
npm install
```

This will install:
- Jest (testing framework)
- jsdom (DOM environment for testing)

## Running Tests

### Basic Test Run
```bash
npm test
```

### Watch Mode (runs tests when files change)
```bash
npm run test:watch
```

### Verbose Output
```bash
npm run test:verbose
```

### Coverage Report
```bash
npm run test:coverage
```

This generates a coverage report in the `coverage/` directory and displays coverage statistics in the terminal.

## Test Categories

### 1. Dashboard Configuration and Constants
Tests the basic configuration values and team definitions used throughout the dashboard.

### 2. Tab Management Functions
Tests the `showTab()` function that handles switching between User and Team consumption tabs.

### 3. User Tag Functions
Tests functions that handle user metadata:
- `getUserPersonTag()` - Retrieves person tags case-insensitively
- `fetchUserTags()` - Simulates fetching user tags from AWS

### 4. Quota Configuration Functions
Tests the `loadQuotaConfig()` function that loads user and team quotas and thresholds.

### 5. Authentication Functions
Tests credential management:
- `checkCredentials()` - Validates stored AWS credentials
- `logout()` - Clears credentials and redirects

### 6. Date Utility Functions
Tests date manipulation functions:
- `getFirstDayOfMonth()` - Calculates first day of current month

### 7. Data Loading Functions
Tests data loading and error handling:
- `showEmptyData()` - Initializes empty data structures
- `showUserError()` / `showTeamError()` - Display error messages

### 8. AWS CloudWatch Integration
Tests CloudWatch API integration:
- `getMetricData()` - Fetches metric data with error handling
- `getDailyMetricData()` - Processes daily usage data
- Handles both successful responses and error conditions

### 9. Chart Update Functions
Tests Chart.js integration:
- `updateUserMonthlyChart()` - Updates or creates user monthly charts
- Handles both chart updates and new chart creation

### 10. Alert Update Functions
Tests alert generation:
- `updateUserAlerts()` - Generates user usage alerts
- Identifies high usage users and categorizes alerts

### 11. IAM Integration Functions
Tests AWS IAM integration:
- `fetchUsersFromIAM()` - Fetches users and tags from IAM
- Handles both successful data retrieval and error conditions

### 12. Data Processing Functions
Tests data aggregation and processing:
- `loadUserMonthlyData()` - Processes user monthly metrics
- `loadUserDailyData()` - Creates date labels and daily data
- `loadUserUsageDetails()` - Populates user usage tables

### 13. Team Data Processing
Tests team-level data processing:
- `loadTeamMonthlyData()` - Aggregates team monthly data
- `loadTeamUsersData()` - Processes users within teams

### 14. Model Distribution Functions
Tests model usage distribution:
- `loadModelDistributionData()` - Generates consistent model usage percentages

### 15. Error Handling Functions
Tests graceful error handling for:
- Missing user data
- Empty metrics data
- Missing quota configuration

### 16. Utility Functions
Tests helper functions:
- Percentage calculations
- Array sorting
- Safe array access with fallbacks

### 17. Integration Tests
Tests complete data flow scenarios:
- Complete dashboard data consistency
- Empty state handling

## Mocking Strategy

The tests use comprehensive mocking for:

- **AWS SDK** - All AWS service calls are mocked
- **Chart.js** - Chart creation and updates are mocked
- **DOM APIs** - Document and window objects are mocked
- **Session Storage** - Browser storage is mocked
- **Date/Time** - Fixed dates for consistent testing
- **Console** - Console output is suppressed during tests

## Test Utilities

The `setup.js` file provides global test utilities:

- `testUtils.createMockElement()` - Creates mock DOM elements
- `testUtils.createMockAWSResponse()` - Creates mock AWS API responses
- `testUtils.createMockUserData()` - Creates mock user data structures
- `testUtils.createMockTeamData()` - Creates mock team data structures

## Coverage Goals

The test suite aims for high coverage across:

- **Function Coverage** - All JavaScript functions are tested
- **Branch Coverage** - All conditional branches are tested
- **Line Coverage** - All executable lines are covered
- **Error Paths** - All error handling paths are tested

## Best Practices

The tests follow these best practices:

1. **Isolation** - Each test is independent and doesn't affect others
2. **Mocking** - External dependencies are properly mocked
3. **Assertions** - Clear, specific assertions for expected behavior
4. **Error Testing** - Both success and failure scenarios are tested
5. **Edge Cases** - Boundary conditions and edge cases are covered
6. **Documentation** - Tests are well-documented and self-explanatory

## Continuous Integration

These tests are designed to run in CI/CD environments. The test configuration:

- Uses jsdom for browser environment simulation
- Suppresses console output to reduce noise
- Provides detailed coverage reporting
- Handles async operations properly
- Cleans up after each test

## Troubleshooting

### Common Issues

1. **Tests failing due to timing** - Async operations are properly awaited
2. **Mock not working** - Check that mocks are set up in `beforeEach` blocks
3. **Coverage issues** - Ensure all code paths are tested

### Debug Mode

To debug tests, you can:

1. Enable console output by commenting out console mocks in `setup.js`
2. Use `test.only()` to run specific tests
3. Add `console.log()` statements in test functions
4. Use Jest's `--verbose` flag for detailed output

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Add appropriate mocks for any new dependencies
3. Include both positive and negative test cases
4. Update this README if adding new test categories
5. Ensure tests are deterministic and don't rely on external state

## Performance

The test suite is optimized for performance:

- Mocks are lightweight and fast
- Tests run in parallel where possible
- Setup and teardown are efficient
- No real network calls or file system operations

## Security

Tests follow security best practices:

- No real AWS credentials are used
- All external calls are mocked
- No sensitive data is logged or stored
- Tests run in isolated environments
