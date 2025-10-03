
---

## 🔹 Вариант: база в контейнере, приложение — локально из IDE

### 1. Запускаем только PostgreSQL (без `app` и без `caddy`)

В `docker-compose.yml` у вас 3 сервиса: `db`, `app`, `caddy`.
Для отладки достаточно поднять **только БД**:

```bash
docker compose up db
```

Postgres поднимется на `localhost:5432`.

---

### 2. Настраиваем `.env` для локальной отладки

Создайте `.env.dev` (например):

```dotenv
# App configs
APP_HOST=127.0.0.1
APP_PORT=8000
RETENTION_DAYS=30
TOKEN_PEPPER=please-change-me

# Database (контейнер слушает localhost:5432)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=logs_db
POSTGRES_USER=logs_user
POSTGRES_PASSWORD=logs_pass
```

---

### 3. Устанавливаем зависимости локально

(в виртуальное окружение или в IDE):

```bash
pip install -r requirements.txt
```

---

### 4. Применяем миграции к базе

Когда контейнер `db` запущен, примените SQL миграцию вручную:

```bash
psql -h localhost -U logs_user -d logs_db -f migrations/001_create_tables.sql
```

Пароль: `logs_pass` (см. `.env`).

---

### 5. Запускаем FastAPI в режиме разработки

```bash
uvicorn app.main:app --reload --port 8000
```

⚡ Теперь сервис работает на `http://127.0.0.1:8000` и будет автоматически перезапускаться при изменении кода.

Swagger доступен на `http://127.0.0.1:8000/docs`.

---

### 6. Использование в IDE


* В **VSCode**: в `launch.json` добавьте:

  ```json
  {
    "name": "FastAPI",
    "type": "python",
    "request": "launch",
    "module": "uvicorn",
    "args": ["app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
    "jinja": true
  }
  ```

---

## 🔹 Вариант: база на внешнем сервере

Если Postgres у вас не в docker, а, например, на `db.example.com:5432`, то просто меняете в `.env.dev`:

```dotenv
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_DB=logs_db
POSTGRES_USER=logs_user
POSTGRES_PASSWORD=secret
```

И запускаете приложение локально тем же способом (`uvicorn --reload`).

---

## 🔹 Итого

1. Поднять только Postgres (`docker compose up db`).
2. Настроить `.env.dev` для локального запуска.
3. Применить SQL миграции.
4. Запустить `uvicorn app.main:app --reload` из IDE.
5. Работать с API на `http://127.0.0.1:8000`.

---

