-- migrations/001_create_jobs.sql
-- Reference DDL — the application creates this automatically via aiosqlite.
-- Run manually if you want to inspect or pre-create the schema.

CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'pending',
    -- pending | extracting | validating | routing | complete | failed | loop_detected
    customer_id  TEXT NOT NULL,
    doc_type     TEXT NOT NULL,
    file_path    TEXT NOT NULL,   -- local path or S3 key
    extraction   TEXT,            -- ExtractionResult JSON
    validation   TEXT,            -- ValidationResult JSON
    decision     TEXT,            -- RouterDecision JSON
    retry_count  INTEGER NOT NULL DEFAULT 0,
    token_usage  INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created  ON jobs(created_at DESC);
