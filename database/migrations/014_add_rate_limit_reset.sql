-- Migration: Add Rate Limit Reset Tracking and Orphaned Tweet Handling
-- Created: 2026-01-26
-- Purpose: Store Twitter rate limit reset timestamp to prevent immediate retries during rate limit periods
--          Store orphaned tweet IDs when thread posting fails mid-sequence for cleanup

-- ============================================================================
-- 1. Add rate_limit_reset column to content_queue
-- ============================================================================

ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS rate_limit_reset TIMESTAMP;

COMMENT ON COLUMN content_queue.rate_limit_reset IS 'Twitter API rate limit reset timestamp from x-rate-limit-reset header (Unix timestamp converted to datetime). Worker must wait until this time before retrying if rate limited (429 error).';

-- ============================================================================
-- 2. Add orphaned_tweet_ids column to content_queue
-- ============================================================================

ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS orphaned_tweet_ids JSONB;

COMMENT ON COLUMN content_queue.orphaned_tweet_ids IS 'Array of Twitter tweet IDs that were posted before thread failed mid-sequence. Used for cleanup or manual review. Example: ["1234567890", "0987654321"]';

-- ============================================================================
-- 3. Create indexes for rate limit and orphaned tweets queries
-- ============================================================================

-- Index for finding items that are past rate limit reset time
CREATE INDEX IF NOT EXISTS idx_content_queue_rate_limit ON content_queue(rate_limit_reset)
WHERE status = 'failed' AND rate_limit_reset IS NOT NULL;

-- Index for finding items with orphaned tweets
CREATE INDEX IF NOT EXISTS idx_content_queue_orphaned ON content_queue(status)
WHERE orphaned_tweet_ids IS NOT NULL;

-- Note: Migration tracking is handled automatically by run_migrations.py via schema_migrations table
