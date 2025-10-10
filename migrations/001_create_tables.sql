CREATE TABLE IF NOT EXISTS logs (
    id BIGSERIAL PRIMARY KEY,
    channel_id TEXT,
    user_social_id TEXT,
    user_message TEXT,
    bot_reply TEXT,
    channel_name TEXT,
    bot_id TEXT,
    llm TEXT,
    api_key TEXT,
    tokens_total BIGINT,
    tokens_in_source BIGINT,
    tokens_out_source BIGINT,
    function_error TEXT,
    function_call_params TEXT,
    server_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Базовые индексы
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_logs_channel_id ON logs (channel_id);

CREATE INDEX IF NOT EXISTS idx_logs_channel_name ON logs (channel_name);

CREATE INDEX IF NOT EXISTS idx_logs_bot_id ON logs (bot_number);

CREATE INDEX IF NOT EXISTS idx_logs_server_name ON logs (server_name);

CREATE TABLE IF NOT EXISTS api_tokens (
    id BIGSERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    role VARCHAR(10) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NULL,
    created_by TEXT NULL
);