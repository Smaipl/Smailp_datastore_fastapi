Миграции выполняются **автоматически при старте контейнера `app`** 🚀

* Миграции будут храниться в `migrations/`
* Они будут называться с префиксом по порядку (`001_...sql`, `002_...sql` и т.д.)
* Все запросы пишем с `IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, чтобы повторный запуск не ломал схему

---

## 🔹 Новый `entrypoint.sh`

Создаём файл `entrypoint.sh` (рядом с `Dockerfile`):

```bash
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
```

---

## 🔹 Обновляем `Dockerfile`

Добавляем `entrypoint.sh` и делаем его исполняемым:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc libpq-dev postgresql-client && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app /app
COPY migrations /migrations
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🔹 Как это работает

1. При старте контейнера `app`:

   * ждём, пока PostgreSQL ответит (`pg_isready`).
   * прогоняем все SQL-файлы из `migrations/` **по алфавиту** (значит по номеру).
   * каждый раз при старте все `.sql` применяются заново.

2. Благодаря `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` миграции можно запускать повторно без ошибок.

3. Новые миграции (`002_...sql`, `003_...sql`) будут автоматически применяться при следующем рестарте контейнера.

---

## 🔹 Пример каталога миграций

```
migrations/
  001_create_tables.sql
  002_add_indexes.sql
  003_create_user_read.sql
```

## 🔹 Описание миграции 003_create_user_read.sql

Добавляет пользователя `user_read` с правами только на чтение всех таблиц:

- Создает роль `user_read` без возможности логина
- Выдает права:
  - `CONNECT` к базе данных
  - `USAGE` схемы public
  - `SELECT` на все существующие и будущие таблицы
- В Down-миграции:
  - Отзывает все выданные права
  - Удаляет роль

Для применения миграции выполните:

```bash
docker-compose exec db psql -U logs_user -d logs_db -f /migrations/003_create_user_read.sql
```


---
