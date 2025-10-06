
---

# 📦 Log Storage Service (FastAPI + PostgreSQL + Caddy)

Сервис для хранения логов и управления токенами.  

---

## 📂 Структура проекта

```bash
logservice/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── auth.py
│   ├── db.py
│   ├── init_admin.py
│   ├── schemas.py
│   └── utils.py
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── datasource.yaml
├── migrations/
│   ├── 001_create_tables.sql
│   ├── 002_add_indexes.sql
│   └── 003_create_user_read.sql
├── .env
├── .dockerignore
├── Caddyfile
├── Caddyfile.dev
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── README.md
├── requirements.txt
└── run_in_deployment_mode.md

```

---

## ⚙️ Конфигурация (.env)

Все настройки выносятся в файл `.env`:

### Важные параметры

* **RETENTION_DAYS** — количество дней хранения логов (старые записи удаляются при вставке).
* **TOKEN_PEPPER** — «соль» для хэширования токенов (обязательно заменить в продакшене).
* **POSTGRES_HOST** — можно указать внешний сервер БД (например, `db.company.net`).
* **DOMAIN** и **EMAIL** — для автоматического получения TLS-сертификата в Caddy.
* **TOKEN_PEPPER** — критически важная "соль" для хэширования токенов (обязательна к замене в продакшене)
* **RETENTION_DAYS** — автоматическое удаление старых записей (по умолчанию 30 дней)
* **GRAFANA_ADMIN_PASSWORD** - админиский пароль для Grafana
* **POSTGRES_READ_USER** - пользователь для чтения данных из БД
* **POSTGRES_READ_PASSWORD** - пароль для пользователя для чтения данных из БД

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
docker-compose exec app python -m app.init_admin
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

### GET `/api/v1/logs`
Получение логов с фильтрацией и пагинацией

#### Заголовки:
  * `Authorization: Bearer <token>`

#### Параметры запроса (опциональны):
  * `from` — datetime ISO (начало диапазона created_at)
  * `to` — datetime ISO (конец диапазона created_at)
  * `unique_channel_number` — Поиск по номеру канала (нестрогий, регистронезависимый)
  * `unique_client_number` — Поиск по номеру клиента (нестрогий, регистронезависимый)
  * `client_phrase` — Поиск по фразе клиента (нестрогий, регистронезависимый)
  * `bot_phrase` — Поиск по фразе бота (нестрогий, регистронезависимый)
  * `channel_name` — Поиск по названию канала (нестрогий, регистронезависимый)
  * `bot_number` — Поиск по номеру бота (нестрогий, регистронезависимый)
  * `llm` — Поиск по модели LLM (нестрогий, регистронезависимый)
  * `function_error` — Поиск по ошибке функции (нестрогий, регистронезависимый)
  * `server` — Поиск по имени сервера (нестрогий, регистронезависимый)
  * `page` — Номер страницы (начиная с 1)
  * `page_size` — Размер страницы (1-100)
  * `sort_by` — Поле для сортировки (по дефолту `created_at`)
  * `order` — `asc|desc` (по дефолту `desc`)

#### Особенности поиска:
  - Поиск выполняется по подстроке в любом месте значения
  - Регистр не имеет значения (Telegram = TELEGRAM = telegram)
  - Спецсимволы обрабатываются корректно (особенно "+" в начале значения)
  - Примеры:
    - `unique_channel_number=+555` - найдет "+555", "123+555", "+555abc"
    - `channel_name=tele` - найдет "Telegram", "my_tele_bot", "TELEPORT"
    - `bot_number=22` - найдет "bot022", "22-bot", "superbot22"
    - `unique_client_number=client` - найдет "client_omega", "user_client", "superclient"
    - `client_phrase=привет` - найдет "Приветствие", "приветствие", "Скажи привет"
    - `bot_phrase=помощь` - найдет "Нужна помощь?", "Помощь", "Техподдержка"
    - `llm=gpt` - найдет "GPT-4", "gpt-3.5", "ChatGPT"
    - `function_error=timeout` - найдет "Connection timeout", "timeout_error", "TimeoutException"

#### Правила выдачи в зависимости от роли:
  * `user`:
    * Если нет параметров фильтра — возвращается пустой список
    * Если есть хотя бы один параметр фильтра — фильтруем по заданным параметрам
  * `admin`:
    * Если нет параметров фильтра — возвращаются все записи
    * Если заданы фильтры — применяются

#### Пример запроса:
```bash
curl -X GET "http://localhost/api/v1/logs?from=2025-01-01T00:00:00Z&to=2025-12-31T23:59:59Z&channel_name=telegram&page=1&page_size=10" \
  -H "Authorization: Bearer <TOKEN>"
```

#### Ответ:
```json
{
  "page": 1,
  "page_size": 10,
  "total": 12345,
  "items": [
    {
      "id": 1,
      "unique_channel_number": "ch_001",
      "unique_client_number": "client123",
      "client_phrase": "hello",
      "bot_phrase": "hi",
      "channel_name": "telegram",
      "bot_number": "bot001",
      "llm": "gpt-5",
      "api_key_masked": "***",
      "tokens_spent_smaipl": 100,
      "inbound_without_coefficient": 80,
      "outbound_without_coefficient": 20,
      "function_error": null,
      "function_call_and_params": "{}",
      "server_name": "srv01",
      "created_at": "2025-01-01T12:34:56.789012+00:00"
    },
    ...
  ]
}
```

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

## 🛠️ Архитектурные изменения (v2.0)

### Новые возможности:
- **Pydantic валидация**: Все запросы и ответы API валидируются через схемы в `app/schemas.py`
- **Автоматические индексы**: GIN-индексы для ускорения текстового поиска по логам
- **Healthcheck эндпоинт**: `GET /healthcheck` для мониторинга состояния сервиса
- **Обработка ошибок БД**: Автоматический реконнект при проблемах с подключением к PostgreSQL

### Актуальные версии зависимостей:
- uvicorn==0.30.2
- starlette==0.40.0
- fastapi==0.116.0

## 🔧 Роли

* **admin**:
  - Генерация токенов
  - Полный доступ ко всем логам без ограничений
  - Создание/удаление записей
* **user**:
  - Создание записей логов
  - Чтение логов с обязательным применением фильтров
  - При отсутствии фильтров возвращается пустой список

## 🩺 Health Check

Для мониторинга состояния сервиса добавлен эндпоинт:

```http
GET /healthcheck
```

**Ответы:**
```json
// Успех
{
  "status": "ok",
  "database": "connected"
}

// Ошибка
{
  "status": "error",
  "database": "disconnected",
  "error": "описание ошибки"
}
```

**Параметры:**
- `status`: Общий статус сервиса (ok/error)
- `database`: Состояние подключения к БД
- `error`: Описание ошибки (при наличии)


---

## 📊 Администрирование БД

### Индексы
Для ускорения поиска добавлены GIN-индексы по всем текстовым полям:
```sql
CREATE INDEX logs_unique_channel_number_gin_idx ON logs USING gin (unique_channel_number gin_trgm_ops);
-- ... и аналогично для других полей ...
```

### Миграции
Все миграции находятся в папке `migrations`:
1. `001_create_tables.sql` - создание таблиц
2. `002_add_indexes.sql` - добавление индексов для производительности

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
