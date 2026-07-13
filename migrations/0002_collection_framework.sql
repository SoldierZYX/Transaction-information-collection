CREATE TABLE IF NOT EXISTS task_locks (
    lock_key TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    records_fetched INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_source_health_source_observed
    ON source_health (source_id, observed_at);
