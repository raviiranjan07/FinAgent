-- Migration 013: Add pending_hitl status to content_queue
-- Date: 2026-01-25
-- Purpose: Enforce HITL review gate for Twitter content

-- Drop existing constraint
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;

-- Add new constraint with pending_hitl status
ALTER TABLE content_queue ADD CONSTRAINT check_status
CHECK (status IN (
    'pending_generation',   -- Initial state, before generation
    'generating',           -- Twitter plugin is running
    'pending_hitl',         -- NEW: Awaiting human approval after generation
    'ready_to_schedule',    -- Approved, ready for scheduling
    'scheduled',            -- Scheduled for future publish
    'published',            -- Published to Twitter
    'failed'                -- Generation or publishing failed
));

-- Add comment
COMMENT ON COLUMN content_queue.status IS 'Content lifecycle status: pending_generation → generating → pending_hitl → ready_to_schedule → scheduled → published';
