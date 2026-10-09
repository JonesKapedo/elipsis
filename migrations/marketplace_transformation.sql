-- Elipsis Marketplace Transformation Database Migration
-- Run this on your NEON PostgreSQL database
-- Date: 2026-10-09

BEGIN;

-- ========================================
-- ENHANCE EXISTING TABLES
-- ========================================

-- Users table enhancements
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(20) DEFAULT 'client';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

COMMENT ON COLUMN users.user_type IS 'User account type: client (needs automation) or bidder (delivers automation)';
COMMENT ON COLUMN users.is_admin IS 'Admin users can verify and publish marketplace requests';

-- Organizations table enhancements
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS annual_revenue_min NUMERIC(15, 2);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS annual_revenue_max NUMERIC(15, 2);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS company_size VARCHAR(20);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(50);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website VARCHAR(500);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN organizations.annual_revenue_min IS 'Minimum annual revenue in USD';
COMMENT ON COLUMN organizations.annual_revenue_max IS 'Maximum annual revenue in USD';
COMMENT ON COLUMN organizations.company_size IS 'Calculated: small, medium, or big based on employees/revenue';

-- Assessments table enhancement
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS scope VARCHAR(50) DEFAULT 'whole_organization';

COMMENT ON COLUMN assessments.scope IS 'Assessment scope: whole_organization or department';

-- ========================================
-- CREATE NEW TABLES
-- ========================================

-- Bidder Companies (service providers)
CREATE TABLE IF NOT EXISTS bidder_companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    services_offered TEXT,
    rate_card TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    website VARCHAR(500),
    description TEXT,
    experience_years INTEGER,
    subscription_status VARCHAR(20) DEFAULT 'inactive' CHECK (subscription_status IN ('active', 'inactive', 'cancelled')),
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bidder_companies_user_id ON bidder_companies(user_id);
CREATE INDEX idx_bidder_companies_subscription ON bidder_companies(subscription_status);

COMMENT ON TABLE bidder_companies IS 'Companies that deliver automation services (marketplace sellers)';

-- Bidder Portfolio (showcase work)
CREATE TABLE IF NOT EXISTS bidder_portfolio (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER NOT NULL REFERENCES bidder_companies(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bidder_portfolio_company ON bidder_portfolio(bidder_company_id);

COMMENT ON TABLE bidder_portfolio IS 'Portfolio images and work samples for bidder companies';

-- Physical Assessment Requests
CREATE TABLE IF NOT EXISTS physical_assessment_requests (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    requirements TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'published', 'completed', 'cancelled')),
    payment_status VARCHAR(20) DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid', 'paid')),
    payment_amount NUMERIC(10, 2),
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    published_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_requests_status ON physical_assessment_requests(status);
CREATE INDEX idx_requests_organization ON physical_assessment_requests(organization_id);
CREATE INDEX idx_requests_user ON physical_assessment_requests(user_id);
CREATE INDEX idx_requests_published ON physical_assessment_requests(published_at DESC);

COMMENT ON TABLE physical_assessment_requests IS 'Requests for physical automation assessments and implementation';
COMMENT ON COLUMN physical_assessment_requests.status IS 'Workflow: pending → verified → published → completed/cancelled';

-- Request Documents
CREATE TABLE IF NOT EXISTS request_documents (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES physical_assessment_requests(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_request_documents_request ON request_documents(request_id);

COMMENT ON TABLE request_documents IS 'Documents attached to physical assessment requests (reports, specs, etc.)';

-- Bid Submissions
CREATE TABLE IF NOT EXISTS bid_submissions (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES physical_assessment_requests(id) ON DELETE CASCADE,
    bidder_company_id INTEGER NOT NULL REFERENCES bidder_companies(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    proposed_timeline VARCHAR(255),
    proposed_cost NUMERIC(10, 2),
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN ('submitted', 'accepted', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bid_submissions_request ON bid_submissions(request_id);
CREATE INDEX idx_bid_submissions_bidder ON bid_submissions(bidder_company_id);
CREATE INDEX idx_bid_submissions_status ON bid_submissions(status);

COMMENT ON TABLE bid_submissions IS 'Bids placed by bidder companies on published requests';

-- Bidder Feedback
CREATE TABLE IF NOT EXISTS bidder_feedback (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER NOT NULL REFERENCES bidder_companies(id) ON DELETE CASCADE,
    request_id INTEGER NOT NULL REFERENCES physical_assessment_requests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bidder_feedback_company ON bidder_feedback(bidder_company_id);
CREATE INDEX idx_bidder_feedback_rating ON bidder_feedback(rating);

COMMENT ON TABLE bidder_feedback IS 'Client feedback and ratings for bidder companies after service delivery';

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    bidder_company_id INTEGER NOT NULL REFERENCES bidder_companies(id) ON DELETE CASCADE,
    plan_type VARCHAR(20) DEFAULT 'monthly' CHECK (plan_type IN ('monthly', 'quarterly', 'yearly')),
    amount NUMERIC(10, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

CREATE INDEX idx_subscriptions_bidder ON subscriptions(bidder_company_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);

COMMENT ON TABLE subscriptions IS 'Subscription records for bidder companies to access marketplace';

-- ========================================
-- HELPER FUNCTIONS
-- ========================================

-- Function to calculate company size
CREATE OR REPLACE FUNCTION calculate_company_size(
    p_employee_count INTEGER,
    p_revenue_avg NUMERIC
) RETURNS VARCHAR(20) AS $$
BEGIN
    -- Priority: Employee count first, then revenue
    IF p_employee_count IS NOT NULL THEN
        IF p_employee_count > 500 THEN
            RETURN 'big';
        ELSIF p_employee_count >= 50 THEN
            RETURN 'medium';
        ELSE
            RETURN 'small';
        END IF;
    END IF;
    
    IF p_revenue_avg IS NOT NULL THEN
        IF p_revenue_avg > 50000000 THEN  -- >$50M
            RETURN 'big';
        ELSIF p_revenue_avg >= 5000000 THEN  -- $5M-$50M
            RETURN 'medium';
        ELSE
            RETURN 'small';
        END IF;
    END IF;
    
    RETURN 'small';  -- Default
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_company_size IS 'Calculate company size (small/medium/big) based on employees and revenue';

-- Trigger to auto-update company_size
CREATE OR REPLACE FUNCTION update_company_size()
RETURNS TRIGGER AS $$
BEGIN
    NEW.company_size := calculate_company_size(
        NEW.employee_count,
        (NEW.annual_revenue_min + NEW.annual_revenue_max) / 2
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_company_size ON organizations;
CREATE TRIGGER trigger_update_company_size
    BEFORE INSERT OR UPDATE OF employee_count, annual_revenue_min, annual_revenue_max
    ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_company_size();

-- ========================================
-- DATA UPDATES
-- ========================================

-- Update existing company sizes
UPDATE organizations
SET company_size = calculate_company_size(
    employee_count,
    (COALESCE(annual_revenue_min, 0) + COALESCE(annual_revenue_max, 0)) / 2
)
WHERE company_size IS NULL;

-- ========================================
-- VIEWS FOR REPORTING
-- ========================================

-- Marketplace requests with company info
CREATE OR REPLACE VIEW v_marketplace_requests AS
SELECT 
    r.id,
    r.title,
    r.message,
    r.requirements,
    r.status,
    r.payment_status,
    r.created_at,
    r.published_at,
    o.name as organization_name,
    o.company_size,
    o.industry,
    o.city,
    o.country,
    u.email as requester_email,
    u.name as requester_name,
    (SELECT COUNT(*) FROM request_documents WHERE request_id = r.id) as document_count,
    (SELECT COUNT(*) FROM bid_submissions WHERE request_id = r.id) as bid_count
FROM physical_assessment_requests r
JOIN organizations o ON r.organization_id = o.id
JOIN users u ON r.user_id = u.id;

COMMENT ON VIEW v_marketplace_requests IS 'Marketplace requests with enriched company and requester information';

-- Bidder company profiles with ratings
CREATE OR REPLACE VIEW v_bidder_profiles AS
SELECT 
    bc.id,
    bc.company_name,
    bc.location,
    bc.services_offered,
    bc.description,
    bc.experience_years,
    bc.subscription_status,
    bc.created_at,
    u.email,
    u.name as contact_name,
    COALESCE(AVG(bf.rating), 0) as avg_rating,
    COUNT(DISTINCT bf.id) as feedback_count,
    COUNT(DISTINCT bs.id) as bid_count,
    (SELECT COUNT(*) FROM bidder_portfolio WHERE bidder_company_id = bc.id) as portfolio_count
FROM bidder_companies bc
JOIN users u ON bc.user_id = u.id
LEFT JOIN bidder_feedback bf ON bc.id = bf.bidder_company_id
LEFT JOIN bid_submissions bs ON bc.id = bs.bidder_company_id
GROUP BY bc.id, u.email, u.name;

COMMENT ON VIEW v_bidder_profiles IS 'Bidder company profiles with aggregated ratings and statistics';

-- ========================================
-- SAMPLE DATA (OPTIONAL - FOR TESTING)
-- ========================================

-- Create admin user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@elipsis.ai') THEN
        INSERT INTO users (email, name, password_hash, role, user_type, is_admin)
        VALUES (
            'admin@elipsis.ai',
            'Admin User',
            '$pbkdf2-sha256$29000$N.b8v9favb7i7P1/73.vNQ$vhL7TgmF6wXJCZx8bKxFzLvPzxYxXHxH8xL9TgmF6wY',  -- Change this password!
            'admin',
            'client',
            TRUE
        );
    END IF;
END $$;

COMMIT;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Run these to verify migration success:

-- Check new columns
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' AND column_name IN ('user_type', 'is_admin');
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'organizations' AND column_name IN ('company_size', 'annual_revenue_min');

-- Check new tables
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%bidder%' OR table_name LIKE '%request%';

-- Check indexes
-- SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename IN ('bidder_companies', 'physical_assessment_requests', 'bid_submissions');

-- Migration complete!
-- Next steps:
-- 1. Update .env with ELIPSIS_DATABASE_URL pointing to this database
-- 2. Deploy updated application code
-- 3. Test user registration, marketplace, and admin features
