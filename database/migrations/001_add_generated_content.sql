-- Migration: Add generated_content table and update content_queue status constraint
-- Date: 2026-01-21
-- Description: Adds Twitter content generation support

BEGIN;

-- Drop existing status constraints on content_queue
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS check_status;
ALTER TABLE content_queue DROP CONSTRAINT IF EXISTS content_queue_status_check;

-- Add updated status constraint with new statuses
ALTER TABLE content_queue ADD CONSTRAINT check_status
    CHECK (status IN ('pending', 'approved', 'rejected', 'generating', 'ready_to_schedule', 'scheduled', 'published'));

-- Create generated_content table
CREATE TABLE IF NOT EXISTS generated_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    output_id UUID REFERENCES outputs(id) ON DELETE CASCADE,
    content_queue_id UUID REFERENCES content_queue(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    content_text TEXT NOT NULL,
    hashtags JSONB DEFAULT '[]',
    character_count INTEGER,
    format_style VARCHAR(50),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for generated_content
CREATE INDEX IF NOT EXISTS idx_generated_content_platform ON generated_content(platform);
CREATE INDEX IF NOT EXISTS idx_generated_content_output_id ON generated_content(output_id);
CREATE INDEX IF NOT EXISTS idx_generated_content_queue_id ON generated_content(content_queue_id);

COMMIT;
