-- Additional models for messaging and enhanced features
-- Run this after the main marketplace_transformation.sql migration

-- Conversations table for in-app messaging
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_id INTEGER REFERENCES physical_assessment_requests(id) ON DELETE SET NULL,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT different_users CHECK (user1_id != user2_id),
    CONSTRAINT unique_conversation UNIQUE (user1_id, user2_id)
);

CREATE INDEX idx_conversations_user1 ON conversations(user1_id);
CREATE INDEX idx_conversations_user2 ON conversations(user2_id);
CREATE INDEX idx_conversations_request ON conversations(request_id);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_receiver ON messages(receiver_id);
CREATE INDEX idx_messages_unread ON messages(receiver_id, is_read) WHERE is_read = FALSE;

-- Analytics/metrics tables
CREATE TABLE IF NOT EXISTS platform_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    total_bids INTEGER DEFAULT 0,
    active_subscriptions INTEGER DEFAULT 0,
    revenue_mrr NUMERIC(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date)
);

CREATE INDEX idx_metrics_date ON platform_metrics(metric_date DESC);

-- User activity log
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL, -- login, bid_submitted, message_sent, etc.
    activity_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_user ON user_activity_log(user_id, created_at DESC);
CREATE INDEX idx_activity_type ON user_activity_log(activity_type, created_at DESC);

-- Add file size and S3 key to request_documents
ALTER TABLE request_documents 
ADD COLUMN IF NOT EXISTS file_size INTEGER,
ADD COLUMN IF NOT EXISTS s3_key VARCHAR(500);

-- Add portfolio image S3 key
ALTER TABLE bidder_portfolio
ADD COLUMN IF NOT EXISTS s3_key VARCHAR(500);

-- Search index for full-text search on requests
CREATE INDEX IF NOT EXISTS idx_requests_search 
ON physical_assessment_requests 
USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Function to update conversation timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations 
    SET last_message_at = NEW.created_at 
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_timestamp();

-- Function to record daily metrics
CREATE OR REPLACE FUNCTION record_daily_metrics()
RETURNS void AS $$
DECLARE
    today DATE := CURRENT_DATE;
    metric_row platform_metrics%ROWTYPE;
BEGIN
    -- Calculate metrics for today
    SELECT 
        today,
        (SELECT COUNT(*) FROM users),
        (SELECT COUNT(*) FROM users WHERE last_login >= today - INTERVAL '7 days'),
        (SELECT COUNT(*) FROM physical_assessment_requests),
        (SELECT COUNT(*) FROM bid_submissions),
        (SELECT COUNT(*) FROM bidder_companies WHERE subscription_status = 'active'),
        0 -- Revenue calculation would go here
    INTO metric_row.metric_date, metric_row.total_users, metric_row.active_users,
         metric_row.total_requests, metric_row.total_bids, metric_row.active_subscriptions,
         metric_row.revenue_mrr;
    
    -- Insert or update
    INSERT INTO platform_metrics (
        metric_date, total_users, active_users, total_requests, 
        total_bids, active_subscriptions, revenue_mrr
    ) VALUES (
        metric_row.metric_date, metric_row.total_users, metric_row.active_users,
        metric_row.total_requests, metric_row.total_bids, metric_row.active_subscriptions,
        metric_row.revenue_mrr
    )
    ON CONFLICT (metric_date) DO UPDATE SET
        total_users = EXCLUDED.total_users,
        active_users = EXCLUDED.active_users,
        total_requests = EXCLUDED.total_requests,
        total_bids = EXCLUDED.total_bids,
        active_subscriptions = EXCLUDED.active_subscriptions,
        revenue_mrr = EXCLUDED.revenue_mrr;
END;
$$ LANGUAGE plpgsql;

-- View for trending requests
CREATE OR REPLACE VIEW trending_requests AS
SELECT 
    par.*,
    COUNT(bs.id) as bid_count,
    o.name as organization_name,
    o.industry,
    o.company_size
FROM physical_assessment_requests par
LEFT JOIN bid_submissions bs ON par.id = bs.request_id
LEFT JOIN organizations o ON par.organization_id = o.id
WHERE par.status = 'published'
    AND par.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY par.id, o.name, o.industry, o.company_size
ORDER BY bid_count DESC, par.created_at DESC
LIMIT 20;

-- Grant permissions (adjust user as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

COMMENT ON TABLE conversations IS 'In-app messaging conversations between users';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON TABLE platform_metrics IS 'Daily aggregated platform metrics for analytics';
COMMENT ON TABLE user_activity_log IS 'User activity tracking for analytics and security';
