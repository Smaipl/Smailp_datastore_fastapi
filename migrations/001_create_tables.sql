CREATE TABLE IF NOT EXISTS logs (
    id BIGSERIAL PRIMARY KEY,
    unique_channel_number TEXT,
    unique_client_number TEXT,
    client_phrase TEXT,
    bot_phrase TEXT,
    channel_name TEXT,
    bot_number TEXT,
    llm TEXT,
    api_key_masked TEXT,
    tokens_spent BIGINT,
    inbound_without_coefficient BIGINT,
    outbound_without_coefficient BIGINT,
    function_error TEXT,
    function_call_and_params TEXT,
    server_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs (created_at DESC);

CREATE TABLE IF NOT EXISTS api_tokens (
    id BIGSERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    role VARCHAR(10) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NULL,
    created_by TEXT NULL
);