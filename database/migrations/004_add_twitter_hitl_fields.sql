-- Migration 004: Add HITL fields to content_queue table
-- Adds fields for tracking AI-suggested verdicts for Twitter content

BEGIN;

-- Add HITL decision fields
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS hitl_required BOOLEAN DEFAULT FALSE;
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS hitl_risk_level VARCHAR(20);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS suggested_verdict VARCHAR(20);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS suggested_verdict_reason VARCHAR(100);

-- Add index for querying by suggested verdict
CREATE INDEX IF NOT EXISTS idx_content_queue_suggested_verdict ON content_queue(suggested_verdict);
CREATE INDEX IF NOT EXISTS idx_content_queue_hitl_required ON content_queue(hitl_required);

COMMIT;
