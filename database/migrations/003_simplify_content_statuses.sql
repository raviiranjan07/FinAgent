-- Migration: Simplify content_queue statuses from 9 to 5
-- Date: 2026-01-22
-- Description: Remove unused statuses and streamline publishing workflow
--
-- Simplified Status Flow:
--   pending_generation → generating → ready_to_schedule → published
--                                                        ↓
--                                                     failed
--
-- Removed: pending, approved, rejected, scheduled (4 statuses)
-- Kept: pending_generation, generating, ready_to_schedule, published, failed (5 statuses)

BEGIN;

-- Step 1: Migrate existing data to valid statuses
-- Convert unused statuses to the closest equivalent
UPDATE content_queue
SET status = 'pending_generation'
WHERE status IN ('pending', 'approved', 'rejected');

-- Convert 'scheduled' to 'published' if platform_post_id exists, else 'ready_to_schedule'
UPDATE content_queue
SET status = CASE
    WHEN platform_post_id IS NOT NULL OR published_at IS NOT NULL THEN 'published'
    ELSE 'ready_to_schedule'
END
WHERE status = 'scheduled';

-- Step 2: Drop old constraint
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS content_queue_status_check;

-- Step 3: Add new simplified constraint with only 5 statuses
ALTER TABLE content_queue ADD CONSTRAINT check_status
    CHECK (status IN (
        'pending_generation',
        'generating',
        'ready_to_schedule',
        'published',
        'failed'
    ));

-- Step 4: Verify migration (optional - for logging purposes)
-- Count statuses after migration
DO $$
DECLARE
    status_counts RECORD;
BEGIN
    RAISE NOTICE 'Content Queue Status Distribution After Migration:';
    FOR status_counts IN
        SELECT status, COUNT(*) as count
        FROM content_queue
        GROUP BY status
        ORDER BY status
    LOOP
        RAISE NOTICE '  % : %', status_counts.status, status_counts.count;
    END LOOP;
END $$;

COMMIT;
