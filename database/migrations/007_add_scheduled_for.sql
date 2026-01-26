-- Migration: Add scheduled_for field to content_queue
-- Purpose: Support scheduling tweets for future publishing
-- Date: 2026-01-23

BEGIN;

-- Add scheduled_for column (when tweet should be published)
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMP;

-- Create index for efficient queries of scheduled content
CREATE INDEX IF NOT EXISTS idx_content_queue_scheduled_for
ON content_queue(scheduled_for)
WHERE scheduled_for IS NOT NULL;

-- Create composite index for worker queries (status + scheduled_for)
CREATE INDEX IF NOT EXISTS idx_content_queue_ready_scheduled
ON content_queue(status, scheduled_for)
WHERE status = 'ready_to_schedule' AND scheduled_for IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN content_queue.scheduled_for IS 'Timestamp when this content should be published to Twitter (NULL = publish immediately)';

COMMIT;
