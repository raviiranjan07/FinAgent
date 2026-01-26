-- Migration: Add Scheduled Publishing Status and Retry Tracking
-- Created: 2026-01-24
-- Purpose: Enable scheduled publishing worker with retry logic and health monitoring

-- ============================================================================
-- 1. Add 'scheduled' status to content_queue constraint
-- ============================================================================

-- Drop existing constraint
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS content_queue_status_check;

-- Add new constraint with 'scheduled' status
ALTER TABLE content_queue ADD CONSTRAINT check_status
    CHECK (status IN (
        'pending_generation',
        'generating',
        'ready_to_schedule',
        'scheduled',        -- NEW: Content scheduled for future publishing
        'published',
        'failed'
    ));

COMMENT ON COLUMN content_queue.status IS 'Publishing status: pending_generation → generating → ready_to_schedule → scheduled → published | failed';

-- ============================================================================
-- 2. Add retry tracking columns to content_queue
-- ============================================================================

ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS publish_attempts INTEGER DEFAULT 0;

ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS last_publish_attempt TIMESTAMP;

COMMENT ON COLUMN content_queue.publish_attempts IS 'Total number of publish attempts (never resets, for monitoring)';
COMMENT ON COLUMN content_queue.retry_count IS 'Current retry cycle count (resets on success, max 3 for retry logic)';
COMMENT ON COLUMN content_queue.last_publish_attempt IS 'Timestamp of last publish attempt (for exponential backoff calculation)';

-- ============================================================================
-- 3. Create indexes for worker queries
-- ============================================================================

-- Index for finding scheduled items in publish window (scheduled_for <= now + 1 min)
CREATE INDEX IF NOT EXISTS idx_content_queue_scheduled_for ON content_queue(scheduled_for)
WHERE status = 'scheduled' AND scheduled_for IS NOT NULL;

-- Index for finding failed items ready for retry
CREATE INDEX IF NOT EXISTS idx_content_queue_failed_retry ON content_queue(status, retry_count, last_publish_attempt)
WHERE status = 'failed' AND retry_count < 3;

-- Index for monitoring published content
CREATE INDEX IF NOT EXISTS idx_content_queue_published_at ON content_queue(published_at DESC)
WHERE status = 'published';

-- Index for finding pending/scheduled items by status
CREATE INDEX IF NOT EXISTS idx_content_queue_status ON content_queue(status);

-- ============================================================================
-- 4. Create worker health monitoring table (optional but recommended)
-- ============================================================================

CREATE TABLE IF NOT EXISTS worker_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_name VARCHAR(50) NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB,
    UNIQUE(worker_name)
);

COMMENT ON TABLE worker_health IS 'Health monitoring for background workers (Twitter publishing, analytics sync, etc.)';
COMMENT ON COLUMN worker_health.worker_name IS 'Unique worker identifier (e.g., twitter_publishing_worker)';
COMMENT ON COLUMN worker_health.last_heartbeat IS 'Last successful heartbeat timestamp';
COMMENT ON COLUMN worker_health.status IS 'Worker status: active, stopped, error';
COMMENT ON COLUMN worker_health.success_count IS 'Total successful operations';
COMMENT ON COLUMN worker_health.failure_count IS 'Total failed operations';

CREATE INDEX IF NOT EXISTS idx_worker_health_heartbeat ON worker_health(last_heartbeat DESC);

-- ============================================================================
-- 5. Add helper function to calculate next retry time (optional)
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_next_retry_time(
    last_attempt TIMESTAMP,
    retry_count INTEGER
)
RETURNS TIMESTAMP AS $$
BEGIN
    -- Exponential backoff: 1s, 2s, 4s
    RETURN last_attempt + (POWER(2, LEAST(retry_count, 2)) || ' seconds')::INTERVAL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_next_retry_time IS 'Calculate next retry time using exponential backoff (1s, 2s, 4s)';

-- ============================================================================
-- 6. Insert migration record
-- ============================================================================

INSERT INTO migrations (version, description, applied_at)
VALUES (11, 'Add scheduled status and retry tracking for publishing worker', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;
