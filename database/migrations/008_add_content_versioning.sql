-- Migration 008: Add content generation versioning and tracking
-- Purpose: Track which plugin version, prompt, and model generated each content item
-- Date: 2026-01-24

BEGIN;

-- Add generation tracking fields
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS plugin_version VARCHAR(50);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS model_used VARCHAR(100);
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS generation_timestamp TIMESTAMP;
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS generation_context JSONB DEFAULT '{}';

-- Add comments for documentation
COMMENT ON COLUMN content_queue.plugin_version IS 'Plugin version that generated content (e.g., "twitter-v1.6-notoken")';
COMMENT ON COLUMN content_queue.prompt_version IS 'Prompt template version used (e.g., "TWITTER_GENERATION_THREAD_v1.6-notoken")';
COMMENT ON COLUMN content_queue.model_used IS 'LLM model used for generation (e.g., "qwen/qwen3-32b")';
COMMENT ON COLUMN content_queue.generation_timestamp IS 'When content was generated';
COMMENT ON COLUMN content_queue.generation_context IS 'Full snapshot of generation config for debugging';

-- Add index for querying by version
CREATE INDEX IF NOT EXISTS idx_content_queue_plugin_version ON content_queue(plugin_version);
CREATE INDEX IF NOT EXISTS idx_content_queue_model_used ON content_queue(model_used);

COMMIT;
