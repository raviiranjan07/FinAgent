-- Migration: Add LLM model tracking to outputs
-- Created: 2026-01-24
-- Purpose: Track which LLM model (Gemini, Groq, Ollama) generated each output

-- Add llm_model column to outputs table
ALTER TABLE outputs ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);

-- Add index for filtering by model
CREATE INDEX IF NOT EXISTS idx_outputs_llm_model ON outputs(llm_model);

-- Add comment
COMMENT ON COLUMN outputs.llm_model IS 'LLM model used to generate output (e.g., gemini-2.5-flash, qwen/qwen3-32b, llama3)';

-- Insert migration record
INSERT INTO migrations (version, description, applied_at)
VALUES (12, 'Add llm_model column to outputs table', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;
