-- Migration: Add pending_generation and failed statuses to content_queue
-- Date: 2026-01-21
-- Description: Enable non-blocking queue-based content generation

BEGIN;

-- Drop existing status constraint
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS content_queue_status_check;

-- Add updated constraint with new statuses
ALTER TABLE content_queue ADD CONSTRAINT check_status
    CHECK (status IN (
        'pending',
        'approved',
        'rejected',
        'pending_generation',
        'generating',
        'ready_to_schedule',
        'scheduled',
        'published',
        'failed'
    ));

-- Add error_message column for failed items
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS error_message TEXT;

COMMIT;
