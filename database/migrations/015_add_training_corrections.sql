-- Migration 015: Add training correction fields for three-verdict system
-- Purpose: Enable PASS/ACCEPT/FAIL verdicts with training data collection
-- Date: 2026-01-30

-- 1. Add corrected classification fields to evaluations table
ALTER TABLE evaluations
ADD COLUMN IF NOT EXISTS corrected_event_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS corrected_intent VARCHAR(50);

-- 2. Update verdict constraint to allow ACCEPT
ALTER TABLE evaluations DROP CONSTRAINT IF EXISTS check_verdict;
ALTER TABLE evaluations ADD CONSTRAINT check_verdict
    CHECK (verdict IN ('PASS', 'FAIL', 'ACCEPT'));

-- 3. Add index for training data export queries
CREATE INDEX IF NOT EXISTS idx_evaluations_corrected_event_type
    ON evaluations(corrected_event_type)
    WHERE corrected_event_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_evaluations_corrected_intent
    ON evaluations(corrected_intent)
    WHERE corrected_intent IS NOT NULL;

-- Training data export query example:
-- SELECT
--     e.title AS event_title,
--     e.summary AS event_summary,
--     o.event_type AS original_type,
--     o.intent AS original_intent,
--     ev.corrected_event_type,
--     ev.corrected_intent,
--     ev.verdict
-- FROM evaluations ev
-- JOIN outputs o ON ev.output_id = o.id
-- JOIN events e ON o.event_id = e.id
-- WHERE ev.corrected_event_type IS NOT NULL;
