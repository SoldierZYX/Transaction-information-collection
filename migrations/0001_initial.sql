CREATE TABLE IF NOT EXISTS trading_calendar (
    date TEXT NOT NULL,
    market TEXT NOT NULL,
    is_trading_day INTEGER NOT NULL CHECK (is_trading_day IN (0, 1)),
    source_id TEXT NOT NULL,
    PRIMARY KEY (date, market)
);

CREATE TABLE IF NOT EXISTS securities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    name TEXT NOT NULL,
    board TEXT NOT NULL,
    active_from TEXT NOT NULL,
    active_to TEXT,
    source_id TEXT NOT NULL,
    UNIQUE (symbol, exchange, active_from)
);

CREATE TABLE IF NOT EXISTS market_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    amount REAL NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE (trade_date, symbol, source_id)
);

CREATE TABLE IF NOT EXISTS index_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    index_code TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    amount REAL NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE (trade_date, index_code, source_id)
);

CREATE TABLE IF NOT EXISTS sector_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    sector_name TEXT NOT NULL,
    change_pct REAL NOT NULL,
    amount REAL,
    source_id TEXT NOT NULL,
    UNIQUE (trade_date, sector_code, source_id)
);

CREATE TABLE IF NOT EXISTS overseas_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,
    instrument TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT NOT NULL,
    market_status TEXT NOT NULL,
    source_id TEXT NOT NULL,
    UNIQUE (observed_at, instrument, source_id)
);

CREATE TABLE IF NOT EXISTS raw_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    published_at TEXT,
    url TEXT,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    UNIQUE (source_id, external_id),
    UNIQUE (source_id, url, content_hash)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    direction TEXT NOT NULL,
    importance REAL NOT NULL,
    freshness REAL NOT NULL,
    confidence REAL NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_evidence (
    event_id INTEGER NOT NULL REFERENCES events(id),
    raw_record_id INTEGER NOT NULL REFERENCES raw_records(id),
    relation_type TEXT NOT NULL,
    PRIMARY KEY (event_id, raw_record_id, relation_type)
);

CREATE TABLE IF NOT EXISTS event_security_links (
    event_id INTEGER NOT NULL REFERENCES events(id),
    symbol TEXT NOT NULL,
    link_basis TEXT NOT NULL,
    PRIMARY KEY (event_id, symbol, link_basis)
);

CREATE TABLE IF NOT EXISTS event_sector_links (
    event_id INTEGER NOT NULL REFERENCES events(id),
    sector_code TEXT NOT NULL,
    link_basis TEXT NOT NULL,
    PRIMARY KEY (event_id, sector_code, link_basis)
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_key TEXT NOT NULL UNIQUE,
    workflow_type TEXT NOT NULL,
    target_date TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    failure_stage TEXT,
    force_run INTEGER NOT NULL DEFAULT 0 CHECK (force_run IN (0, 1))
);

CREATE TABLE IF NOT EXISTS pool_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id),
    target_date TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    input_snapshot_hash TEXT NOT NULL,
    UNIQUE (workflow_run_id)
);

CREATE TABLE IF NOT EXISTS pool_exclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_run_id INTEGER NOT NULL REFERENCES pool_runs(id),
    symbol TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    UNIQUE (pool_run_id, symbol, reason_code)
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool_run_id INTEGER NOT NULL REFERENCES pool_runs(id),
    symbol TEXT NOT NULL,
    total_score REAL NOT NULL,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL,
    conditions TEXT NOT NULL,
    invalidation TEXT NOT NULL,
    UNIQUE (pool_run_id, symbol)
);

CREATE TABLE IF NOT EXISTS candidate_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    component TEXT NOT NULL,
    score REAL NOT NULL,
    inputs_json TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    UNIQUE (candidate_id, component)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(id),
    type TEXT NOT NULL,
    target_date TEXT NOT NULL,
    cutoff_at TEXT NOT NULL,
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE (workflow_run_id, type)
);

CREATE TABLE IF NOT EXISTS candidate_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    return_close REAL,
    max_gain REAL,
    max_drawdown REAL,
    UNIQUE (report_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    delivery_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    recipients_hash TEXT NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    forced INTEGER NOT NULL DEFAULT 0 CHECK (forced IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ai_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model TEXT NOT NULL,
    input_record_count INTEGER NOT NULL,
    usage_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_records_source_published_at
    ON raw_records (source_id, published_at);
CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_trade_date
    ON market_bars (symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at
    ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_target_date
    ON workflow_runs (target_date, workflow_type);
