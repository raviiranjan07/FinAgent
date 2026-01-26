-- Migration: Add generation_metadata column to outputs table
-- Purpose: Store immutable snapshot of LLM generation configuration for audit trail and reproducibility
-- Date: 2026-01-22

-- Add generation_metadata column (idempotent - safe to run multiple times)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'outputs' AND column_name = 'generation_metadata'
    ) THEN
        ALTER TABLE outputs
        ADD COLUMN generation_metadata JSONB DEFAULT '{}'::jsonb NOT NULL;
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN outputs.generation_metadata IS
'Immutable snapshot of generation configuration including model, prompt version, temperature, and generation parameters. Used for audit trail, debugging, and reproducibility.';

-- Create index for querying by metadata fields (optional, for analytics)
-- Example: Find all outputs generated with a specific model or prompt version
CREATE INDEX IF NOT EXISTS idx_outputs_generation_metadata_gin ON outputs USING GIN (generation_metadata);

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'outputs' AND column_name = 'generation_metadata';
