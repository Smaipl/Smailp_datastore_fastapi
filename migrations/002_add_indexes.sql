-- Добавляем индексы для полей фильтрации
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Индекс для полей с текстовым поиском
CREATE INDEX IF NOT EXISTS logs_unique_channel_number_gin_idx ON logs USING gin (unique_channel_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_unique_client_number_gin_idx ON logs USING gin (unique_client_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_client_phrase_gin_idx ON logs USING gin (client_phrase gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_bot_phrase_gin_idx ON logs USING gin (bot_phrase gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_channel_name_gin_idx ON logs USING gin (channel_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_bot_number_gin_idx ON logs USING gin (bot_number gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_llm_gin_idx ON logs USING gin (llm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_function_error_gin_idx ON logs USING gin (function_error gin_trgm_ops);
CREATE INDEX IF NOT EXISTS logs_server_name_gin_idx ON logs USING gin (server_name gin_trgm_ops);

-- Индекс для поля created_at (используется в очистке и сортировке)
CREATE INDEX IF NOT EXISTS logs_created_at_idx ON logs (created_at);
