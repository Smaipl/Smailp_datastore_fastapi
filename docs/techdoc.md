
---

# Техническое задание (ТЗ)

**Название:** Система хранения логов (Log Storage Service)
**Язык:** Python
**База данных:** PostgreSQL
**Развёртывание:** Docker Compose (app, postgres, caddy/nginx)
**Фазы:**

  * Этап 1 — API (сохранение/выгрузка)
  * Этап 2 — веб-админка

---

## 1. Цели и общие требования

1. Собирать логи через HTTP POST и сохранять в PostgreSQL. Поле «Дата и время» генерируется в БД автоматически при вставке (timestamp with time zone, default now()).
2. Предоставлять REST API для:

   * сохранения записи (POST)
   * получения записей по фильтрам (GET) с пагинацией и сортировкой (частично — поведение зависит от роли: admin/user)
3. Параметры запроса GET:

    * `from` — datetime ISO (начало диапазона created_at)
    * `to` — datetime ISO (конец диапазона created_at)
    * `unique_channel_number` — string
    * `channel_name` — string
    * `bot_number` — string
    * `server` — string (server_name)
    * `page` — int (по умолчанию 1)
    * `page_size` — int (по умолчанию 10, макс, например 100)
    * `sort_by` — поле для сортировки (по дефолту `created_at`)
    * `order` — `asc|desc` (по дефолту `desc`)   
4. Авторизация по токену (Bearer). Два уровня: `admin` и `user`. Эндпоинт для генерации токенов.
5. Асинхронность API (поддержка высокой нагрузки).
6. Лёгкая админка (браузерная) на том же сервере для просмотра/фильтрации/настроек времени жизни записей.
7. Логика удаления старых записей: конфигурируемое retention-days (по умолчанию 30), удаление осуществляется в момент вставки новой записи (как триггер: после вставки запускается проверка и удаление старых записей).

---

## 2. Входные данные (формат POST)

Пример запроса — массив JSON. Поля приходят массивом, дата/время заполняется автоматически в БД. 

```shell
curl -X POST "[https://example.com/webhook"](https://example.com/webhook") \
  -H "Authorization: Bearer 12345_XXXXXXXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '[
        "+1234567890",
        "sender123",
        "",
        "Hello!",
        "telegram",
        "promt_001",
        "gpt-5",
        "...my_api_key",
        100,
        80,
        20,
        "no errors",
        "last function log",
        "node-01"
      ]'
```

---

## 3. API спецификация (REST)

**Базовый путь:** `/api/v1`

### Аутентификация

* Все запросы с авторизацией: Header `Authorization: Bearer <token>`
* Система токенов: токены хранятся в таблице `api_tokens` с привязкой к роли (`admin`/`user`), expiry (опционально), created_by и comment.
* Эндпоинт генерации токенов: `POST /api/v1/tokens/generate` — требует `admin` (или авторизация по логину-паролю для админки). Возвращает `token`, `role`, `expires_at` (опционально).

---

### POST /api/v1/logs — сохранить запись

* Заголовки:

  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* Тело: JSON — массив значений (как в примере) или опционально — объект с именованными полями (рекомендуется поддержать оба формата; на первом этапе — массив как в примере).
* Обработка:

  * Валидация токена и роли (user может сохранять).
  * Преобразование массива в поля таблицы (см. mapping выше).
  * Вставка в `logs` (created_at DEFAULT now()).
  * После вставки — запуск функции очистки старых записей (см. retention).
* Ответ:

  * 201 Created + JSON `{ "id": <log_id>, "created_at": "<ts>" }`
  * При ошибке — 4xx/5xx с подробным сообщением.


#### Маппинг для POST (массив) — порядок элементов, который ожидает сервер

##### (POST должен принимать массив значений в этом порядке)

```
POST body (JSON array) — порядок элементов:
0  — unique_channel_number            (Уникальный номер канала общения)
1  — unique_client_number             (Уникальный номер клиента)
2  — client_phrase                    (Фраза клиента)
3  — bot_phrase                       (Фраза бота)
4  — channel_name                     (Канал связи)
5  — bot_number                       (Номер бота)
6  — llm                              (LLM)
7  — api_key_masked                   (Ключ)
8  — tokens_spent_smaipl              (Расход в токенах SMAIPL) — numeric/int
9  — inbound_without_coefficient      (Входящие без коэффициента) — numeric
10 — outbound_without_coefficient     (Исходящие без коэффициента) — numeric
11 — function_error                   (Ошибка при выполнении функции)
12 — function_call_and_params         (Вызов функции и параметры)
13 — server_name                      (Сервер)
(Дата и время -> created_at генерируется в БД)
```

##### Если приходит именованный объект:

```json
{
  "unique_channel_number": "...",
  "unique_client_number": "...",
  "client_phrase": "...",
  "bot_phrase": "...",
  "channel_name": "...",
  "bot_number": "...",
  "llm": "...",
  "api_key_masked": "...",
  "tokens_spent_smaipl": 123,
  "inbound_without_coefficient": 45,
  "outbound_without_coefficient": 78,
  "function_error": "...",
  "function_call_and_params": "...",
  "server_name": "..."
}
```

### GET /api/v1/logs — получить записи (фильтры + пагинация)

* Заголовки:

  * `Authorization: Bearer <token>`

* Query params (опционально):

  * `from` — datetime ISO (начало диапазона created_at)
  * `to` — datetime ISO (конец диапазона created_at)
  * `unique_channel_number` — string
  * `channel_name` — string
  * `bot_number` — string
  * `server` — string (server_name)
  * `page` — int (по умолчанию 1)
  * `page_size` — int (по умолчанию 10, макс, например 100)
  * `sort_by` — поле для сортировки (по дефолту `created_at`)
  * `order` — `asc|desc` (по дефолту `desc`)

* Правила выдачи в зависимости от роли:

  * `user`:
    * Если нет параметров фильтра — возвращаем пустой набор / 200 с пустым списком.
    * Если есть хотя бы один параметр фильтра — фильтруем по заданным параметрам и возвращаем результаты (с пагинацией).

  * `admin`:
    * Если нет параметров фильтра — возвращаем все записи, отсортированные по `created_at desc`, с пагинацией.
    * Если заданы фильтры — применяем их.

* Ответ:

  * 200 OK `{ "page": N, "page_size": M, "total": T, "items": [ ... ] }`

### Примеры

* Сохранение (curl) в body — массив.
```shell
curl -X POST "[https://example.com/webhook"](https://example.com/webhook") \
  -H "Authorization: Bearer 12345_XXXXXXXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '[
        "+1234567890",
        "sender123",
        "",
        "Hello!",
        "telegram",
        "promt_001",
        "gpt-5",
        "...my_api_key",
        100,
        80,
        20,
        "no errors",
        "last function log",
        "node-01"
      ]'
```

* Получение: `GET /api/v1/logs?from=2025-09-01T00:00:00Z&to=2025-09-30T23:59:59Z&channel_name=telegram&page=1&page_size=10`

* Ответ:

```json
{
  "page": 1,
  "page_size": 10,
  "total": 12345,
  "items": [ { <log record> }, ... ]
}
```

---

## 4. Администрирование токенов

* Эндпоинты:

  * `POST /api/v1/tokens/generate` — генерирует новый токен (только admin)
  * `GET /api/v1/tokens` — список токенов (admin)
  * `DELETE /api/v1/tokens/{id}` — отозвать токен (admin)

---

## 5. Политика хранения и автоматическая очистка (retention)

* Глобальная настройка `RETENTION_DAYS` (по умолчанию 30).
* Механизм удаления: при каждой вставке (POST /logs) выполняется `DELETE FROM logs WHERE created_at < now() - interval 'RETENTION_DAYS days'`.
* В админке — поле для настройки `RETENTION_DAYS`.

---

## 6. Админка (Этап 2)

**Развёртывание:** на том же сервере/домене, базовый путь `/admin`

Функциональность:

* Авторизация по логину/паролю (admin users). Пароли хранить безопасно (bcrypt).
* Просмотр записей с таблицей:

  * Пагинация (настраиваемая, default 10)
  * Фильтры (те же, что и в API)
  * Сортировка: кликабельные заголовки (один уровень сортировки)
* UI:

  * Таблица записей; возможность раскрыть запись/просмотреть raw JSON.
  * Настройка `RETENTION_DAYS`.
  * Управление API-токенами (генерация/удаление).
* Реализация: серверный шаблон (Django templates). 

---

## 7. Технологический стек

1. **Django + Django REST Framework (DRF) + PostgreSQL** с uvicorn + asgiref для работы.
2. **Очистка / background jobs:** для этапа 1 — реализовать удаление синхронно при вставке. На будущее — можно вынести в background worker (asyncio tasks).
3. **Docker Compose:** сервисы: app, postgres, caddy (https).
4. **Логирование и мониторинг:** хранить ошибки сервиса, метрики запросов (Prometheus / Grafana) — опционально в будущем.

---

## 8. Таблицы (миграции)

1. **logs**

```sql
CREATE TABLE logs (
  id BIGSERIAL PRIMARY KEY,
  unique_channel_number TEXT,
  unique_client_number TEXT,
  client_phrase TEXT,
  bot_phrase TEXT,
  channel_name TEXT,
  bot_number TEXT,
  llm TEXT,
  api_key_masked TEXT,
  tokens_spent_smaipl BIGINT,
  inbound_without_coefficient BIGINT,
  outbound_without_coefficient BIGINT,
  function_error TEXT,
  function_call_and_params TEXT,
  server_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индексы для ускорения фильтров/сортировки:
CREATE INDEX idx_logs_created_at ON logs (created_at DESC);
CREATE INDEX idx_logs_unique_channel_number ON logs (unique_channel_number);
CREATE INDEX idx_logs_channel_name ON logs (channel_name);
CREATE INDEX idx_logs_bot_number ON logs (bot_number);
CREATE INDEX idx_logs_server_name ON logs (server_name);
```

2. **api_tokens**

```sql
CREATE TABLE api_tokens (
  id bigserial PRIMARY KEY,
  token_hash text NOT NULL,
  role varchar(10) NOT NULL, -- 'admin'|'user'
  comment text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NULL,
  created_by text NULL
);
CREATE UNIQUE INDEX ux_api_tokens_token_hash ON api_tokens (token_hash);
```

3. **users** (для админки; использовать встроенную модель Django User)

* id, username, password_hash, is_admin, created_at

---

## 9. Безопасность

* Токены: выдавать в виде случайного длинного секретного ключа; хранить в базе только хэш (bcrypt/sha256+pepper).
* HTTPS — Caddy в docker-compose.
* SQL-инъекции: использовать ORM или параметризованные запросы.

---

## 10. Тесты

* Unit tests для: парсинга POST, валидации, авторизации токенов, фильтров GET, retention-logic.
* Integration test: end-to-end с тестовой БД (docker-compose test).

---

## 11. Docker Compose (схема)

* services:

  * app (Gunicorn/uvicorn + код)
  * postgres (volume)
  * caddy (https)
* Environment variables: DATABASE_URL, SECRET_KEY, RETENTION_DAYS, ADMIN_CREDENTIALS (для инициализации).

---

## 12. План работ (микро-этапы)

**Этап 1 (API) — минимально работоспособный:**

1. Создать проект, настройки Docker Compose.
2. Модель `logs`, миграции.
3. Реализовать `POST /api/v1/logs` (парсинг массива, валидация, вставка, retention-delete).
4. Реализовать `GET /api/v1/logs` с фильтрами и пагинацией, поведение role-based (admin/user).
5. Таблица `api_tokens`, генерация токенов, middleware авторизации.
6. Тесты основных сценариев.
7. Документация API (OpenAPI / Swagger).

**Этап 2 (Админка):**

1. Реализовать логин/аутентификацию админа.
2. UI просмотра логов, фильтры, пагинация, сортировка.
3. Управление токенами.
4. Настройка RETENTION_DAYS из UI.
5. Тесты, документация, деплой.

---
