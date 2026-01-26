-- Migration: Alter content_queue table for Twitter plugin
-- Purpose: Add Twitter-specific fields to existing content_queue table
-- Date: 2026-01-22

BEGIN;

-- Add event reference columns (denormalized for quick access)
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS event_title VARCHAR(500);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS event_type VARCHAR(50);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS event_url VARCHAR(500);

-- Add impact framing (JSON stored as TEXT)
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS impact_framing TEXT;

-- Add format decision columns
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS format VARCHAR(20);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS thread_length INTEGER DEFAULT 1;

-- Add Twitter content columns
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS content_text TEXT;
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS hashtags VARCHAR(200);

-- Add twitter_post_id (keep platform_post_id for backward compatibility)
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS twitter_post_id VARCHAR(100);

-- Update status constraint to include new statuses
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;
ALTER TABLE content_queue ADD CONSTRAINT check_status
    CHECK (status IN ('pending_generation', 'generating', 'ready_to_schedule', 'published', 'failed'));

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_content_queue_format ON content_queue(format);
CREATE INDEX IF NOT EXISTS idx_content_queue_event_type ON content_queue(event_type);

-- Update existing records to have default values
UPDATE content_queue SET format = 'SINGLE' WHERE format IS NULL;
UPDATE content_queue SET thread_length = 1 WHERE thread_length IS NULL;

-- Now make format NOT NULL (after setting defaults)
ALTER TABLE content_queue ALTER COLUMN format SET NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN content_queue.event_title IS 'Denormalized event title for quick access';
COMMENT ON COLUMN content_queue.event_type IS 'Event classification (FINANCE_POLICY, MACRO_ECONOMIC, etc.)';
COMMENT ON COLUMN content_queue.event_url IS 'Original event URL';
COMMENT ON COLUMN content_queue.impact_framing IS 'JSON containing angle analysis: primary_angle, what_this_is_not, why_it_matters, reader_lens, discussion_hook';
COMMENT ON COLUMN content_queue.format IS 'Twitter format: SINGLE (1 tweet) or THREAD (3 tweets)';
COMMENT ON COLUMN content_queue.thread_length IS 'Number of tweets in thread (1 for SINGLE, 3 for THREAD)';
COMMENT ON COLUMN content_queue.content_text IS 'Generated Twitter content - for SINGLE: tweet text, for THREAD: JSON array of tweets';
COMMENT ON COLUMN content_queue.hashtags IS 'Comma-separated hashtags';
COMMENT ON COLUMN content_queue.twitter_post_id IS 'Twitter post ID after successful publishing';

COMMIT;
