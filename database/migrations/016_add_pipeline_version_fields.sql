-- Add pipeline version tracking to content_queue
-- This allows running v1 (via outputs) and v2 (direct) pipelines in parallel

ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS pipeline_version VARCHAR(10) DEFAULT 'v1';
-- Values: 'v1' (old pipeline via outputs) or 'v2' (new direct pipeline)

ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS source_event_id UUID;
-- Direct link to event (for v2 pipeline, nullable for backward compatibility)

ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS generation_intent VARCHAR(50);
-- Store which intent was used for generation (enables regeneration with different intent)

-- Add index for filtering by pipeline version
CREATE INDEX IF NOT EXISTS idx_content_queue_pipeline_version ON content_queue(pipeline_version);

-- Add index for event lookups (v2 pipeline)
CREATE INDEX IF NOT EXISTS idx_content_queue_source_event_id ON content_queue(source_event_id);
