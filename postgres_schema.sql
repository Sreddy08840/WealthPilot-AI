-- ============================================================================
-- WealthPilot AI - Autonomous Portfolio Rebalancing System
-- Production-Ready PostgreSQL Database Schema Design
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. Users Table
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('client', 'advisor', 'portfolio_manager', 'compliance_officer', 'system_agent', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. Risk Categories Table
-- ============================================================================
CREATE TABLE risk_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE CHECK (name IN ('Conservative', 'Moderately Conservative', 'Balanced', 'Growth', 'Aggressive')),
    target_allocations JSONB NOT NULL, -- Format: {"SPY": 0.45, "QQQ": 0.10, "AGG": 0.30, "BIL": 0.10, "GLD": 0.05}
    drift_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.050 CHECK (drift_threshold > 0.000 AND drift_threshold < 1.000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. Portfolios Table
-- ============================================================================
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_number VARCHAR(50) NOT NULL UNIQUE,
    client_name VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    risk_category_id INTEGER NOT NULL REFERENCES risk_categories(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'closed')),
    auto_rebalance BOOLEAN NOT NULL DEFAULT FALSE,
    tax_optimized BOOLEAN NOT NULL DEFAULT TRUE,
    cash_balance NUMERIC(15,2) NOT NULL DEFAULT 0.00 CHECK (cash_balance >= 0.00),
    current_value NUMERIC(15,2) NOT NULL DEFAULT 0.00 CHECK (current_value >= 0.00),
    last_rebalanced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. Asset Classes Table
-- ============================================================================
CREATE TABLE asset_classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- e.g. 'US Equities', 'Fixed Income', 'Cash', 'Commodities'
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Helper Table: Assets Core
CREATE TABLE assets (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    asset_class_id INTEGER NOT NULL REFERENCES asset_classes(id) ON DELETE RESTRICT,
    is_restricted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. Holdings Table
-- ============================================================================
CREATE TABLE holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_symbol VARCHAR(20) NOT NULL REFERENCES assets(symbol) ON DELETE RESTRICT,
    shares NUMERIC(16,4) NOT NULL DEFAULT 0.0000 CHECK (shares >= 0.0000),
    market_value NUMERIC(15,2) NOT NULL DEFAULT 0.00 CHECK (market_value >= 0.00),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_portfolio_asset UNIQUE (portfolio_id, asset_symbol)
);

-- ============================================================================
-- 6. Tax Lots Table
-- ============================================================================
CREATE TABLE tax_lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_symbol VARCHAR(20) NOT NULL REFERENCES assets(symbol) ON DELETE RESTRICT,
    shares NUMERIC(16,4) NOT NULL CHECK (shares > 0.0000),
    purchase_price NUMERIC(10,2) NOT NULL CHECK (purchase_price > 0.00),
    purchase_date TIMESTAMPTZ NOT NULL,
    is_harvested BOOLEAN NOT NULL DEFAULT FALSE,
    harvested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 7. Market Prices Table (Timeseries layout)
-- ============================================================================
CREATE TABLE market_prices (
    asset_symbol VARCHAR(20) NOT NULL REFERENCES assets(symbol) ON DELETE RESTRICT,
    price NUMERIC(10,2) NOT NULL CHECK (price > 0.00),
    price_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_symbol, price_timestamp)
);

-- ============================================================================
-- 8. Rebalancing Decisions Table
-- ============================================================================
CREATE TABLE rebalancing_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    trigger_type VARCHAR(30) NOT NULL CHECK (trigger_type IN ('Threshold', 'Calendar', 'Event')),
    status VARCHAR(30) NOT NULL DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'approved', 'rejected', 'executing', 'completed', 'failed')),
    drift_before NUMERIC(5,4) NOT NULL CHECK (drift_before >= 0.0000),
    drift_after NUMERIC(5,4) CHECK (drift_after >= 0.0000),
    tax_savings_estimate NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    shap_explanations JSONB, -- Attributions of features
    reviewer_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    reviewer_comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 9. Trade Orders Table
-- ============================================================================
CREATE TABLE trade_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rebalancing_decision_id UUID NOT NULL REFERENCES rebalancing_decisions(id) ON DELETE CASCADE,
    asset_symbol VARCHAR(20) NOT NULL REFERENCES assets(symbol) ON DELETE RESTRICT,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    shares NUMERIC(16,4) NOT NULL CHECK (shares > 0.0000),
    limit_price NUMERIC(10,2) CHECK (limit_price > 0.00),
    executed_price NUMERIC(10,2) CHECK (executed_price > 0.00),
    status VARCHAR(30) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'partially_filled', 'filled', 'cancelled', 'rejected')),
    tax_impact NUMERIC(15,2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 10. Compliance Logs Table
-- ============================================================================
CREATE TABLE compliance_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rebalancing_decision_id UUID NOT NULL REFERENCES rebalancing_decisions(id) ON DELETE CASCADE,
    rule_name VARCHAR(100) NOT NULL, -- Wash Sale Rule, Restricted Ticker Check, Concentration Limit
    status VARCHAR(30) NOT NULL CHECK (status IN ('pass', 'fail', 'warning', 'bypass')),
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 11. Agent Activity Logs Table
-- ============================================================================
CREATE TABLE agent_activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rebalancing_decision_id UUID NOT NULL REFERENCES rebalancing_decisions(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL, -- Portfolio Monitor, Tax Optimizer, Compliance Auditor, Execution Planner
    activity_type VARCHAR(50) NOT NULL, -- thinking, tool_call, validation, completion
    log_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 12. Audit Trail Table (Range-Partitioned by month on created_at)
-- ============================================================================
CREATE TABLE audit_trail (
    id UUID NOT NULL DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL, -- USER_UPDATE, PARAM_CHANGE, REBALANCE_EXECUTION
    details TEXT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    old_state JSONB,
    new_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (created_at);

-- Create sample default partitions (e.g. for Q3/Q4 2026)
CREATE TABLE audit_trail_2026_06 PARTITION OF audit_trail
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');
    
CREATE TABLE audit_trail_2026_07 PARTITION OF audit_trail
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');

CREATE TABLE audit_trail_2026_08 PARTITION OF audit_trail
    FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');

-- ============================================================================
-- Indexes Optimization
-- ============================================================================

-- Portfolios search & user associations
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX idx_portfolios_risk_category ON portfolios(risk_category_id);

-- Holdings retrieval for portfolio allocations
CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);

-- Tax lot search optimization (essential for fast HIFO picking)
-- Composite index sorted by portfolio/symbol and lot purchase price descending
CREATE INDEX idx_tax_lots_hifo ON tax_lots(portfolio_id, asset_symbol, purchase_price DESC) WHERE is_harvested = FALSE;

-- Market prices fast lookup (gets latest price for ticker quickly)
CREATE INDEX idx_market_prices_latest ON market_prices(asset_symbol, price_timestamp DESC);

-- Decisions query indexes
CREATE INDEX idx_rebalancing_decisions_portfolio ON rebalancing_decisions(portfolio_id);
CREATE INDEX idx_rebalancing_decisions_status ON rebalancing_decisions(status);
-- GIN index for fast filtering inside JSONB SHAP attributions
CREATE INDEX idx_rebalancing_decisions_shap ON rebalancing_decisions USING gin (shap_explanations);

-- Trade orders lookup
CREATE INDEX idx_trade_orders_decision ON trade_orders(rebalancing_decision_id);
CREATE INDEX idx_trade_orders_status ON trade_orders(status);

-- Compliance logs lookup
CREATE INDEX idx_compliance_logs_decision ON compliance_logs(rebalancing_decision_id);

-- Agent activity logs lookup
CREATE INDEX idx_agent_activity_logs_decision ON agent_activity_logs(rebalancing_decision_id);

-- ============================================================================
-- Triggers for updated_at timestamps auto-updating
-- ============================================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_modtime BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_risk_categories_modtime BEFORE UPDATE ON risk_categories FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_portfolios_modtime BEFORE UPDATE ON portfolios FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_assets_modtime BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_rebalancing_decisions_modtime BEFORE UPDATE ON rebalancing_decisions FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_trade_orders_modtime BEFORE UPDATE ON trade_orders FOR EACH ROW EXECUTE FUNCTION update_modified_column();
