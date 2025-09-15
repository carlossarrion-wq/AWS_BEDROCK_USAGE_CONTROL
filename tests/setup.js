/**
 * Jest Setup File
 * 
 * This file contains global setup and configuration for Jest tests.
 * It runs before each test file and sets up common mocks and utilities.
 */

// Global test utilities
global.testUtils = {
    // Helper to create mock DOM elements
    createMockElement: (tagName = 'div', attributes = {}) => {
        const element = {
            tagName: tagName.toUpperCase(),
            classList: {
                add: jest.fn(),
                remove: jest.fn(),
                contains: jest.fn(),
                toggle: jest.fn()
            },
            innerHTML: '',
            textContent: '',
            style: {},
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            getAttribute: jest.fn(),
            setAttribute: jest.fn(),
            ...attributes
        };
        return element;
    },

    // Helper to create mock AWS responses
    createMockAWSResponse: (data, error = null) => {
        return {
            promise: () => error ? Promise.reject(error) : Promise.resolve(data)
        };
    },

    // Helper to create mock user data
    createMockUserData: (username, options = {}) => {
        return {
            username,
            personTag: options.personTag || 'Test User',
            team: options.team || 'test_team',
            monthly: options.monthly || 1000,
            daily: options.daily || Array(10).fill(0).map((_, i) => i === 8 ? 50 : 0),
            quota: {
                monthly_limit: options.monthlyLimit || 3000,
                daily_limit: options.dailyLimit || 150,
                warning_threshold: options.warningThreshold || 60,
                critical_threshold: options.criticalThreshold || 85
            }
        };
    },

    // Helper to create mock team data
    createMockTeamData: (teamName, options = {}) => {
        return {
            teamName,
            monthly: options.monthly || 5000,
            daily: options.daily || Array(10).fill(0).map((_, i) => i === 8 ? 200 : 0),
            users: options.users || ['user1', 'user2'],
            quota: {
                monthly_limit: options.monthlyLimit || 25000,
                warning_threshold: options.warningThreshold || 60,
                critical_threshold: options.criticalThreshold || 85
            }
        };
    }
};

// Mock console methods to reduce noise in tests
global.console = {
    ...console,
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn(),
    debug: jest.fn()
};

// Mock Date to ensure consistent test results
const OriginalDate = Date;
const mockDate = new OriginalDate('2024-01-15T10:00:00.000Z');
global.Date = class extends OriginalDate {
    constructor(...args) {
        if (args.length === 0) {
            super(mockDate.getTime());
        } else {
            super(...args);
        }
    }
    
    static now() {
        return mockDate.getTime();
    }
};

// Mock Math.random for consistent test results
global.Math.random = jest.fn(() => 0.5);

// Setup global error handling for tests
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Clean up after each test
afterEach(() => {
    jest.clearAllMocks();
    
    // Reset DOM mocks
    if (global.document) {
        global.document.getElementById = jest.fn();
        global.document.querySelector = jest.fn();
        global.document.querySelectorAll = jest.fn(() => []);
    }
    
    // Reset window mocks
    if (global.window) {
        global.window.location.href = '';
    }
    
    // Reset sessionStorage mocks
    if (global.sessionStorage) {
        if (global.sessionStorage.getItem.mockClear) {
            global.sessionStorage.getItem.mockClear();
        }
        if (global.sessionStorage.setItem.mockClear) {
            global.sessionStorage.setItem.mockClear();
        }
        if (global.sessionStorage.removeItem.mockClear) {
            global.sessionStorage.removeItem.mockClear();
        }
    }
});

// Setup before all tests
beforeAll(() => {
    // Suppress console output during tests unless explicitly needed
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
});

// Cleanup after all tests
afterAll(() => {
    jest.restoreAllMocks();
});
