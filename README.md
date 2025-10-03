
---

# 📦 Log Storage Service (FastAPI + PostgreSQL + Caddy)

Сервис для хранения логов и управления токенами.  
Этап 1 проекта: REST API для записи и получения логов.  
Просмотр логов можно реализовать подключением **Metabase** или **Grafana** к PostgreSQL.  

---

## 📂 Структура проекта

logservice/
├── app/
│   ├── **init**.py
│   ├── main.py              # FastAPI-приложение (эндпоинты)
│   ├── auth.py              # Авторизация по токенам
│   ├── db.py                # Подключение к БД
│   ├── models.py            # SQL схемы (asyncpg)
│   ├── utils.py             # Хэширование токенов
│   └── init_admin.py        # Скрипт создания первого admin-токена
│
├── migrations/
│   └── 001_create_tables.sql
│
├── .env                     # Конфигурация приложения
├── .dockerignore
├── Caddyfile
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md


---

## ⚙️ Конфигурация (.env)

Все настройки выносятся в файл `.env`:

```dotenv
# FastAPI
APP_HOST=0.0.0.0
APP_PORT=8000
RETENTION_DAYS=30
TOKEN_PEPPER=please-change-me

# Database
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=logs_db
POSTGRES_USER=logs_user
POSTGRES_PASSWORD=logs_pass

# Caddy (для HTTPS)
DOMAIN=logs.example.com
EMAIL=admin@example.com
````

### Важные параметры

* **RETENTION_DAYS** — количество дней хранения логов (старые записи удаляются при вставке).
* **TOKEN_PEPPER** — «соль» для хэширования токенов (обязательно заменить в продакшене).
* **POSTGRES_HOST** — можно указать внешний сервер БД (например, `db.company.net`).
* **DOMAIN** и **EMAIL** — для автоматического получения TLS-сертификата в Caddy.

---

## 🚀 Запуск

1. Подготовить `.env`.
2. Собрать и запустить контейнеры:

   ```bash
   docker-compose up --build -d
   ```
3. Приложение доступно:

   * API: `http://localhost/api/v1/...`
   * Swagger UI: `http://localhost/docs`
   * PostgreSQL: `localhost:5432`

---

## 🗝 Создание первого admin-токена

После первого запуска БД в таблице `api_tokens` нет записей.
Чтобы создать первый токен администратора:

```bash
docker-compose run --rm app python init_admin.py
```

Вывод будет таким:

```
Admin token created:
<RAW_TOKEN>
```

⚠️ **Сохраните токен** — он показывается только один раз.
Далее используйте его как Bearer-токен в заголовках запросов.

---

## 🔑 Управление токенами

### POST `/api/v1/tokens/generate` (только admin)

Создать новый токен (admin/user).

#### Запрос:

```bash
curl -X POST http://localhost/api/v1/tokens/generate \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"role":"user","comment":"for webhook"}'
```

#### Ответ:

```json
{
  "token": "raw_token_value",
  "role": "user"
}
```

---

## 📝 Работа с логами

### POST `/api/v1/logs`

Создать запись лога.

Поддерживаются **два формата** тела запроса:

#### 1. Массив (14 элементов строго по порядку):

Порядок полей:

```
unique_channel_number,
unique_client_number,
client_phrase,
bot_phrase,
channel_name,
bot_number,
llm,
api_key_masked,
tokens_spent_smaipl,
inbound_without_coefficient,
outbound_without_coefficient,
function_error,
function_call_and_params,
server_name
```

##### Пример:

```bash
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[ "ch_001", "client123", "hello", "hi", "telegram", "bot001",
        "gpt-5", "***", 100, 80, 20, null, "{}", "srv01" ]'
```

#### 2. Объект (именованный JSON):

```bash
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "unique_channel_number":"ch_001",
    "unique_client_number":"client123",
    "client_phrase":"hello",
    "bot_phrase":"hi",
    "channel_name":"telegram",
    "bot_number":"bot001",
    "llm":"gpt-5",
    "api_key_masked":"***",
    "tokens_spent_smaipl":100,
    "inbound_without_coefficient":80,
    "outbound_without_coefficient":20,
    "function_error":null,
    "function_call_and_params":"{}",
    "server_name":"srv01"
  }'
```

#### Ответ:

```json
{
  "id": 42,
  "created_at": "2025-10-02T12:34:56.789012+00:00"
}
```

⚠️ После вставки автоматически выполняется удаление записей старше `RETENTION_DAYS`.

---

## 🔍 OpenAPI / Swagger

Документация по API доступна по адресу:

```
http://localhost/docs
```

---

## 📦 Миграции

Схема таблиц описана в `migrations/001_create_tables.sql`.
При первом запуске они применяются автоматически через скрипт в `Dockerfile`.

Таблицы:

* `logs` — хранение логов.
* `api_tokens` — токены с ролями (`admin` / `user`).

---

## 🔒 Авторизация

* Все эндпоинты требуют заголовок:

  ```
  Authorization: Bearer <TOKEN>
  ```
* Токены хранятся в таблице `api_tokens` в виде **SHA256(token+PEPPER)**.
* При генерации/инициализации отображается **сырой токен** — храните его сами.

---

## 🔧 Роли

* **admin**: может генерировать токены, писать и читать логи.
* **user**: может писать и читать логи (но если запрос без фильтров — вернёт пустой список).

---

## 📊 Просмотр логов

В текущем этапе API не содержит интерфейса для просмотра.
Для визуализации подключите:

* **Metabase** — быстрый просмотр таблиц, дашборды.
* **Grafana** — графики и метрики.

Подключение: PostgreSQL → таблица `logs`.

---

## 🌍 Продакшн-деплой

* В `Caddyfile` укажите:

  ```caddyfile
  logs.example.com {
      reverse_proxy app:8000
      tls admin@example.com
  }
  ```
* Caddy автоматически получит сертификат Let’s Encrypt.
* Используйте отдельный внешний PostgreSQL при высокой нагрузке.
* Обязательно замените:

  * `TOKEN_PEPPER`
  * `DJANGO_SECRET_KEY` (если добавите Django на этапе 2)

---

## ✅ Краткое резюме

* **FastAPI API** — хранение логов, токены, retention.
* **PostgreSQL** — надёжное хранилище.
* **Caddy** — HTTPS и обратный прокси.
* **init_admin.py** — генерация первого админского токена.
* **Metabase/Grafana** — дальнейший просмотр логов без дополнительного кода.

```

---

🔥 Теперь у вас полный **README.md** с документацией по работе и деплою сервиса.  
Хотите, я дополню README ещё и схемой (архитектурной диаграммой) в PNG/SVG для наглядности?
```
