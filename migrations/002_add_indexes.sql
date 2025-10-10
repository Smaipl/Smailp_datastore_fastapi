-- Добавляем индексы для полей фильтрации
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Индекс для полей с текстовым поиском
CREATE INDEX IF NOT EXISTS logs_channel_id_gin_idx ON logs USING gin (channel_id gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_user_social_id_gin_idx ON logs USING gin (user_social_id gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_user_message_gin_idx ON logs USING gin (user_message gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_bot_reply_gin_idx ON logs USING gin (bot_reply gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_channel_name_gin_idx ON logs USING gin (channel_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_bot_id_gin_idx ON logs USING gin (bot_id gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_llm_gin_idx ON logs USING gin (llm gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_function_error_gin_idx ON logs USING gin (function_error gin_trgm_ops);

CREATE INDEX IF NOT EXISTS logs_server_name_gin_idx ON logs USING gin (server_name gin_trgm_ops);