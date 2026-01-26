-- Migration 009: Add unique constraint on output_id
-- Purpose: Prevent duplicate processing of the same output
-- Date: 2026-01-24

BEGIN;

-- Delete any existing duplicates before adding constraint
-- Keep only the most recent one for each output_id
WITH duplicates AS (
    SELECT id, output_id,
           ROW_NUMBER() OVER (PARTITION BY output_id ORDER BY created_at DESC) as rn
    FROM content_queue
)
DELETE FROM content_queue
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Add unique constraint on output_id
-- This ensures each output can only be processed once
ALTER TABLE content_queue
ADD CONSTRAINT unique_content_queue_output_id UNIQUE (output_id);

-- Add comment
COMMENT ON CONSTRAINT unique_content_queue_output_id ON content_queue
IS 'Ensures each output is processed only once - prevents duplicate content generation';

COMMIT;
