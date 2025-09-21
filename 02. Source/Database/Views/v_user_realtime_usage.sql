-- =====================================================
-- View: v_user_realtime_usage
-- Description: Real-time user usage check (for blocking decisions)
-- =====================================================

CREATE VIEW v_user_realtime_usage AS
SELECT 
    u.user_id,
    u.team,
    u.daily_limit,
    u.monthly_limit,
    u.is_blocked,
    u.blocked_until,
    u.admin_protection_by,
    -- Today's usage
    COALESCE(today.request_count, 0) as today_requests,
    COALESCE(today.total_cost, 0) as today_cost,
    -- This month's usage
    COALESCE(month.request_count, 0) as monthly_requests,
    COALESCE(month.total_cost, 0) as monthly_cost,
    -- Usage percentages
    ROUND((COALESCE(today.request_count, 0) / u.daily_limit) * 100, 2) as daily_usage_percent,
    ROUND((COALESCE(month.request_count, 0) / u.monthly_limit) * 100, 2) as monthly_usage_percent,
    -- Last request timestamp
    COALESCE(today.last_request, '1970-01-01 00:00:00') as last_request_time
FROM users u
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as request_count,
        SUM(cost_usd) as total_cost,
        MAX(request_timestamp) as last_request
    FROM bedrock_requests 
    WHERE date_only = CURDATE()
    GROUP BY user_id
) today ON u.user_id = today.user_id
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as request_count,
        SUM(cost_usd) as total_cost
    FROM bedrock_requests 
    WHERE date_only >= DATE_FORMAT(NOW(), '%Y-%m-01')
    GROUP BY user_id
) month ON u.user_id = month.user_id;
