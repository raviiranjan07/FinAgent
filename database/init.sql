-- FinAgent Database Initialization
-- PostgreSQL + pgvector setup for Pre-MVP

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Events table: Raw RSS events with embeddings
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    link TEXT,
    source VARCHAR(100) NOT NULL,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding VECTOR(384),  -- all-minilm embedding dimension
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Outputs table: LLM generated content
CREATE TABLE IF NOT EXISTS outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    llm_output TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    intent VARCHAR(50) NOT NULL,
    clarity_issues JSONB DEFAULT '[]',
    hitl_required BOOLEAN DEFAULT FALSE,
    hitl_risk_level VARCHAR(20),
    output_embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evaluations table: Human verdicts
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    output_id UUID REFERENCES outputs(id) ON DELETE CASCADE,
    verdict VARCHAR(10) NOT NULL CHECK (verdict IN ('PASS', 'FAIL')),
    failure_reason TEXT,
    comment TEXT,
    evaluator VARCHAR(100),
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content queue table: For publishing workflow
CREATE TABLE IF NOT EXISTS content_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    output_id UUID REFERENCES outputs(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'scheduled', 'published')),
    edited_content TEXT,
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    platform VARCHAR(50),
    platform_post_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_published_at ON events(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outputs_event_id ON outputs(event_id);
CREATE INDEX IF NOT EXISTS idx_outputs_event_type ON outputs(event_type);
CREATE INDEX IF NOT EXISTS idx_evaluations_verdict ON evaluations(verdict);
CREATE INDEX IF NOT EXISTS idx_content_queue_status ON content_queue(status);

-- Vector similarity index (IVFFlat for faster approximate search)
-- Note: Run this after inserting initial data for better performance
-- CREATE INDEX IF NOT EXISTS idx_events_embedding ON events
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for content_queue updated_at
CREATE TRIGGER update_content_queue_updated_at
    BEFORE UPDATE ON content_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
