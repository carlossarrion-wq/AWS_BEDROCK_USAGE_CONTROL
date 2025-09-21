-- =====================================================
-- Table: users
-- Description: Stores user information and quotas
-- =====================================================

CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    team VARCHAR(100) NOT NULL,
    person_tag VARCHAR(255),
    daily_limit INT DEFAULT 250,
    monthly_limit INT DEFAULT 5000,
    warning_threshold INT DEFAULT 60,
    critical_threshold INT DEFAULT 85,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_reason VARCHAR(500),
    blocked_until TIMESTAMP NULL,
    admin_protection_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_team (team),
    INDEX idx_person_tag (person_tag),
    INDEX idx_blocked (is_blocked),
    INDEX idx_blocked_until (blocked_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default system user
INSERT IGNORE INTO users (user_id, team, person_tag) VALUES 
('system', 'admin', 'System User');
