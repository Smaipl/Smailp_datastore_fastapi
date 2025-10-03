#!/bin/sh
set -e

echo "⏳ Waiting for database..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

echo "✅ Database is up, applying migrations..."

for f in /migrations/*.sql; do
  echo "Applying migration: $f"
  psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB" -f "$f"
done

echo "✅ Migrations applied"

exec "$@"
