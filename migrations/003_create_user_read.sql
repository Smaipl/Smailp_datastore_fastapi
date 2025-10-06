-- Создаём пользователя для чтения, если его нет
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_read') THEN
        CREATE ROLE user_read LOGIN PASSWORD 'user_read_password';
    END IF;
END
$$;

-- Раздаём права только на чтение
GRANT CONNECT ON DATABASE logs_db TO user_read;
GRANT USAGE ON SCHEMA public TO user_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO user_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO user_read;
