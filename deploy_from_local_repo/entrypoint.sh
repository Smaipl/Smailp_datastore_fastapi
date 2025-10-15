#!/bin/sh
set -e

echo "⏳ Waiting for database..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

echo "✅ Database is up, applying migrations..."

# Применяем миграции
psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB" \
  -f /migrations/001_create_tables.sql \
  -f /migrations/002_add_indexes.sql \
  -f /migrations/003_create_user_read.sql \
  -f /migrations/004_add_tokens_user.sql

echo "✅ Migrations applied"

# Запускаем приложение
exec "$@"
