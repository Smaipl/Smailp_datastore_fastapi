-- Table for system logs
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    host TEXT,
    logger TEXT,
    level TEXT,
    filename TEXT,
    funcname TEXT,
    lineno INTEGER,
    message TEXT,
    path TEXT
);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_system_logs_logger ON system_logs (logger);
CREATE INDEX IF NOT EXISTS idx_system_logs_host ON system_logs (host);
