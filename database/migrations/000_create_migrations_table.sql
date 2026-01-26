-- Migration: Create migrations tracking table
-- Purpose: Track which migrations have been applied to prevent re-running
-- Date: 2026-01-22

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- Add index for quick lookups
CREATE INDEX IF NOT EXISTS idx_migrations_name ON schema_migrations(migration_name);

-- Add comment
COMMENT ON TABLE schema_migrations IS 'Tracks which migrations have been applied to this database';

-- Insert record for this migration itself
INSERT INTO schema_migrations (migration_name, notes)
VALUES ('000_create_migrations_table', 'Initial migration tracking table')
ON CONFLICT (migration_name) DO NOTHING;
