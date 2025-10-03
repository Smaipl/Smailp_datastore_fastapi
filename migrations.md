Очень правильный вопрос 👌
В FastAPI (и вообще в «чистых» проектах без Django/Alembic) миграции нужно организовывать отдельно, потому что у нас **нет встроенного механизма как в Django ORM**. В текущем skeleton-е у вас миграции сделаны максимально просто — через SQL-файлы. Давайте разберём подробно.

---

## 🔹 Как сейчас устроено в проекте

1. В папке `migrations/` лежат `.sql` файлы (например `001_create_tables.sql`).
2. В `Dockerfile` и `docker-compose.yml` мы **копируем** эти миграции внутрь контейнера.
3. Но! Сейчас нет автоматического применения — то есть контейнер **не запускает их сам**.
   Вы должны применить их вручную командой:

   ```bash
   psql -h localhost -U logs_user -d logs_db -f migrations/001_create_tables.sql
   ```

   или из контейнера:

   ```bash
   docker-compose exec db psql -U logs_user -d logs_db -f /migrations/001_create_tables.sql
   ```

---

## 🔹 Проблема повторного запуска

* Если вы дважды выполните `001_create_tables.sql`, PostgreSQL выдаст ошибку **«relation already exists»**, если не предусмотрены `IF NOT EXISTS`.
* В моём файле я уже использовал `CREATE TABLE IF NOT EXISTS` и `CREATE INDEX IF NOT EXISTS`.
  👉 значит, при повторном прогоне **ошибки не будет**, но **новые изменения не накатятся**.

То есть `001_create_tables.sql` безопасно применять много раз, но оно не умеет эволюционировать (например, добавить колонку).

---

## 🔹 Что делать, если появятся новые миграции?

Допустим, вы добавили поле в таблицу и создали новый файл `002_add_new_column.sql`:

```sql
ALTER TABLE logs ADD COLUMN new_field TEXT;
```

Чтобы применить:

```bash
docker-compose exec db psql -U logs_user -d logs_db -f /migrations/002_add_new_column.sql
```

⚠️ Автоматически оно **не выполнится** — нужно запускать руками, либо добавить свой механизм миграций.

---

## 🔹 Как сделать удобнее (варианты)

1. **Оставить как есть**

   * Миграции — это просто `.sql` файлы.
   * Применяются руками (или в CI/CD скриптах).
   * Работает надёжно, но требует дисциплины.

2. **Добавить `entrypoint.sh` для авто-прогона всех `.sql`**
   Пример:

   ```bash
   for f in /migrations/*.sql; do
       echo "Applying $f"
       psql "$DATABASE_URL" -f "$f"
   done
   ```

   ⚠️ Минус — без «состояния» оно будет прогонять все файлы каждый раз (но с `IF NOT EXISTS` это безопасно).

Отлично, сделаем так, чтобы миграции прогонялись **автоматически при старте контейнера `app`** 🚀

Мы договорились, что:

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

## 🔹 Важно

* Такой механизм прост и надёжен, но не хранит «состояние» (какие миграции были уже применены).
* Поэтому очень важно:

  * всегда именовать новые миграции с возрастающим номером (`002_`, `003_` и т.д.),
  * не редактировать старые файлы после того, как они уже попали в продакшен.

---

## 🔹 Пример каталога миграций

```
migrations/
  001_create_tables.sql
  002_add_new_column.sql
  003_add_index_logs.sql
```

---