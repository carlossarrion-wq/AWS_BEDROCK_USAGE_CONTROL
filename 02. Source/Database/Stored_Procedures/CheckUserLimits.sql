-- =====================================================
-- Stored Procedure: CheckUserLimits
-- Description: Check if user should be blocked (called on each request)
-- =====================================================

DELIMITER //

CREATE PROCEDURE CheckUserLimits(
    IN p_user_id VARCHAR(255),
    OUT p_should_block BOOLEAN,
    OUT p_block_reason VARCHAR(500),
    OUT p_daily_usage INT,
    OUT p_monthly_usage INT,
    OUT p_daily_percent DECIMAL(5,2),
    OUT p_monthly_percent DECIMAL(5,2)
)
BEGIN
    DECLARE v_daily_limit INT DEFAULT 250;
    DECLARE v_monthly_limit INT DEFAULT 5000;
    DECLARE v_critical_threshold INT DEFAULT 85;
    DECLARE v_is_blocked BOOLEAN DEFAULT FALSE;
    DECLARE v_blocked_until TIMESTAMP;
    DECLARE v_admin_protection VARCHAR(255);
    
    -- Get user limits and current status
    SELECT daily_limit, monthly_limit, critical_threshold, is_blocked, blocked_until, admin_protection_by
    INTO v_daily_limit, v_monthly_limit, v_critical_threshold, v_is_blocked, v_blocked_until, v_admin_protection
    FROM users 
    WHERE user_id = p_user_id;
    
    -- Get current usage
    SELECT 
        COALESCE(today_requests, 0),
        COALESCE(monthly_requests, 0),
        COALESCE(daily_usage_percent, 0),
        COALESCE(monthly_usage_percent, 0)
    INTO p_daily_usage, p_monthly_usage, p_daily_percent, p_monthly_percent
    FROM v_user_realtime_usage
    WHERE user_id = p_user_id;
    
    -- Check if already blocked
    IF v_is_blocked = TRUE THEN
        -- Check if block has expired
        IF v_blocked_until IS NOT NULL AND v_blocked_until <= NOW() THEN
            -- Unblock user
            UPDATE users 
            SET is_blocked = FALSE, blocked_reason = NULL, blocked_until = NULL
            WHERE user_id = p_user_id;
            SET p_should_block = FALSE;
            SET p_block_reason = NULL;
        ELSE
            SET p_should_block = TRUE;
            SET p_block_reason = 'User is currently blocked';
        END IF;
    ELSE
        -- Check limits (only if not admin protected)
        IF v_admin_protection IS NULL THEN
            IF p_daily_percent >= v_critical_threshold OR p_monthly_percent >= v_critical_threshold THEN
                SET p_should_block = TRUE;
                SET p_block_reason = CONCAT('Usage limit exceeded: ', 
                    GREATEST(p_daily_percent, p_monthly_percent), '% of limit');
                
                -- Auto-block user
                UPDATE users 
                SET is_blocked = TRUE, 
                    blocked_reason = p_block_reason,
                    blocked_until = DATE_ADD(NOW(), INTERVAL 1 DAY)
                WHERE user_id = p_user_id;
                
                -- Log blocking operation
                INSERT INTO blocking_operations (user_id, operation, reason, performed_by)
                VALUES (p_user_id, 'block', p_block_reason, 'system');
            ELSE
                SET p_should_block = FALSE;
                SET p_block_reason = NULL;
            END IF;
        ELSE
            SET p_should_block = FALSE;
            SET p_block_reason = NULL;
        END IF;
    END IF;
END //

DELIMITER ;
