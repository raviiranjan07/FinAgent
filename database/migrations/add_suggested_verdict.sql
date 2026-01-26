-- Migration: Add suggested_verdict columns to outputs table
-- Purpose: Store system-generated verdict suggestions for HITL agreement tracking
-- Date: 2026-01-22

ALTER TABLE outputs
ADD COLUMN IF NOT EXISTS suggested_verdict VARCHAR(10),
ADD COLUMN IF NOT EXISTS suggested_verdict_reason VARCHAR(100);

-- Add check constraint to ensure suggested_verdict is only PASS or FAIL (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'check_suggested_verdict'
    ) THEN
        ALTER TABLE outputs
        ADD CONSTRAINT check_suggested_verdict
        CHECK (suggested_verdict IS NULL OR suggested_verdict IN ('PASS', 'FAIL'));
    END IF;
END $$;

-- Create index for filtering by suggested verdict
CREATE INDEX IF NOT EXISTS idx_outputs_suggested_verdict ON outputs(suggested_verdict);

-- Add comment for documentation
COMMENT ON COLUMN outputs.suggested_verdict IS 'System-generated verdict suggestion (PASS/FAIL) for HITL agreement tracking';
COMMENT ON COLUMN outputs.suggested_verdict_reason IS 'Reason for FAIL verdict (ADVICE_DETECTED, HIGH_RISK_CONTENT, MULTIPLE_CLARITY_ISSUES, OFF_TOPIC_CONTENT)';
