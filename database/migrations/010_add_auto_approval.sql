-- Migration: Add Auto-Approval System
-- Created: 2026-01-24
-- Purpose: Add auto-approval tracking, confidence scoring, and audit history

-- ============================================================================
-- 1. Add auto-approval tracking to evaluations table
-- ============================================================================

ALTER TABLE evaluations
ADD COLUMN IF NOT EXISTS auto_approved BOOLEAN DEFAULT FALSE;

ALTER TABLE evaluations
ADD COLUMN IF NOT EXISTS confidence_score FLOAT;

ALTER TABLE evaluations
ADD COLUMN IF NOT EXISTS confidence_signals JSONB;

ALTER TABLE evaluations
ADD COLUMN IF NOT EXISTS similar_outputs_count INTEGER;

COMMENT ON COLUMN evaluations.auto_approved IS 'Whether this evaluation was auto-approved (true) or manually reviewed (false)';
COMMENT ON COLUMN evaluations.confidence_score IS 'Weighted confidence score (0-100) calculated from multiple signals';
COMMENT ON COLUMN evaluations.confidence_signals IS 'JSON object containing breakdown of confidence signals (clarity, similarity, event_type, intent, source)';
COMMENT ON COLUMN evaluations.similar_outputs_count IS 'Number of similar outputs with PASS verdict found during auto-approval';

-- ============================================================================
-- 2. Create auto-approval audit history table
-- ============================================================================

CREATE TABLE IF NOT EXISTS auto_approval_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    output_id UUID NOT NULL REFERENCES outputs(id) ON DELETE CASCADE,
    confidence_score FLOAT NOT NULL,
    confidence_signals JSONB NOT NULL,
    similar_outputs JSONB NOT NULL,
    auto_approved BOOLEAN NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE auto_approval_history IS 'Audit trail for all auto-approval decisions (both approved and rejected)';
COMMENT ON COLUMN auto_approval_history.output_id IS 'Reference to the output being evaluated';
COMMENT ON COLUMN auto_approval_history.confidence_score IS 'Final weighted confidence score (0-100)';
COMMENT ON COLUMN auto_approval_history.confidence_signals IS 'Detailed breakdown of all signals (clarity, similarity, event_type, intent, source)';
COMMENT ON COLUMN auto_approval_history.similar_outputs IS 'Array of similar output IDs found (with similarity scores)';
COMMENT ON COLUMN auto_approval_history.auto_approved IS 'Decision: true = auto-approved, false = requires manual review';
COMMENT ON COLUMN auto_approval_history.reason IS 'Human-readable explanation of decision';

CREATE INDEX IF NOT EXISTS idx_auto_approval_history_output_id ON auto_approval_history(output_id);
CREATE INDEX IF NOT EXISTS idx_auto_approval_history_created_at ON auto_approval_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auto_approval_history_auto_approved ON auto_approval_history(auto_approved);

-- ============================================================================
-- 3. Create confidence stats cache table
-- ============================================================================

CREATE TABLE IF NOT EXISTS confidence_stats_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stat_type VARCHAR(50) NOT NULL,
    stat_key VARCHAR(100) NOT NULL,
    pass_rate FLOAT NOT NULL DEFAULT 0.0,
    total_count INTEGER NOT NULL DEFAULT 0,
    pass_count INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stat_type, stat_key)
);

COMMENT ON TABLE confidence_stats_cache IS 'Cached pass rates for event_type, intent, and source (for performance)';
COMMENT ON COLUMN confidence_stats_cache.stat_type IS 'Type of statistic: event_type, intent, or source';
COMMENT ON COLUMN confidence_stats_cache.stat_key IS 'The key value (e.g., FINANCE_POLICY, EXPLANATORY, RBI_PRESS)';
COMMENT ON COLUMN confidence_stats_cache.pass_rate IS 'Percentage of PASS verdicts (0.0-100.0)';
COMMENT ON COLUMN confidence_stats_cache.total_count IS 'Total number of evaluations for this key';
COMMENT ON COLUMN confidence_stats_cache.pass_count IS 'Number of PASS verdicts for this key';

CREATE INDEX IF NOT EXISTS idx_confidence_stats_cache_type_key ON confidence_stats_cache(stat_type, stat_key);

-- ============================================================================
-- 4. Create indexes for auto-approval queries
-- ============================================================================

-- Index for finding similar outputs by event_type (used in similarity search)
CREATE INDEX IF NOT EXISTS idx_outputs_event_type ON outputs(event_type) WHERE event_type IS NOT NULL;

-- Index for evaluations by verdict (used in pass rate calculations)
CREATE INDEX IF NOT EXISTS idx_evaluations_verdict ON evaluations(verdict) WHERE verdict IS NOT NULL;

-- Index for auto-approved evaluations
CREATE INDEX IF NOT EXISTS idx_evaluations_auto_approved ON evaluations(auto_approved) WHERE auto_approved = TRUE;

-- Note: Migration tracking is handled automatically by run_migrations.py via schema_migrations table
