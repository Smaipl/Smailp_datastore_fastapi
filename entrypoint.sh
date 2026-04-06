#!/bin/sh
set -e

echo "⏳ Waiting for database..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

echo "✅ Database is up, applying migrations..."

# Применяем все миграции с продолжением при ошибках
for migration_file in $(ls ./migrations/*.sql | sort); do
  echo "Applying ${migration_file}..."
  psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB" \
    -v ON_ERROR_STOP=0 -f "${migration_file}"
done

echo "✅ Migrations applied"

# Запускаем приложение
exec "$@"
