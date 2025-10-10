```markdown
---
# Техническое задание (ТЗ)

**Название:** Система хранения логов (Log Storage Service)
**Язык:** Python (FastAPI)
**База данных:** PostgreSQL
**Развёртывание:** Docker Compose (app, postgres, caddy, grafana)
**Фазы:**

  * Этап 1 — API (сохранение/выгрузка) ✅ **РЕАЛИЗОВАНО**
  * Этап 2 — веб-админка ❗**ЗАМЕНЕНО НА GRAFANA**

---

## 1. Цели и общие требования

1. Собирать логи через HTTP POST и сохранять в PostgreSQL. Поле «Дата и время» генерируется в БД автоматически при вставке (timestamp with time zone, default now()).
2. Предоставлять REST API для:

   * сохранения записи (POST)
   * получения записей по фильтрам (GET) с пагинацией и сортировкой (частично — поведение зависит от роли: admin/user)
3. Параметры запроса GET:

    * `from` — datetime ISO (начало диапазона created_at)
    * `to` — datetime ISO (конец диапазона created_at)
    * `channel_id` — string (старый unique_channel_number)
    * `channel_name` — string
    * `bot_id` — string (старый bot_number)
    * `server_name` — string (старый server)
    * `page` — int (по умолчанию 1)
    * `page_size` — int (по умолчанию 10, макс, например 100)
    * `sort_by` — поле для сортировки (по дефолту `created_at`)
    * `order` — `asc|desc` (по дефолту `desc`)   
4. Авторизация по токену (Bearer). Два уровня: `admin` и `user`. Эндпоинт для генерации токенов.
5. Асинхронность API (поддержка высокой нагрузки).
6. **Визуализация и мониторинг:** развернута Grafana для просмотра данных, создания дашбордов и аналитики.
7. Логика удаления старых записей: конфигурируемое retention-days (по умолчанию 30), удаление осуществляется в момент вставки новой записи.
8. **Валидация данных:** строгая типизация и валидация через Pydantic.

---

## 2. Входные данные (формат POST)

Поддерживаются два формата запроса — массив JSON и именованный объект.

### Формат массива (14 элементов строго по порядку):

```shell
curl -X POST "https://example.com/api/v1/logs" \
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

### Формат объекта (именованные поля):

```json
{
  "channel_id": "...",
  "user_social_id": "...",
  "user_message": "...",
  "bot_reply": "...",
  "channel_name": "...",
  "bot_id": "...",
  "llm": "...",
  "api_key": "...",
  "tokens_total": 123,
  "tokens_in_source": 45,
  "tokens_out_source": 78,
  "function_error": "...",
  "function_call_params": "...",
  "server_name": "..."
}
```

---

## 3. API спецификация (REST)

**Базовый путь:** `/api/v1`

### Аутентификация

* Все запросы с авторизацией: Header `Authorization: Bearer <token>`
* Система токенов: токены хранятся в таблице `api_tokens` с привязкой к роли (`admin`/`user`), expiry (опционально), created_by и comment.
* Эндпоинт генерации токенов: `POST /api/v1/tokens/generate` — требует `admin`. Возвращает `token`, `role`, `expires_at` (опционально).

---

### POST /api/v1/logs — сохранить запись

* Заголовки:

  * `Authorization: Bearer <token>`
  * `Content-Type: application/json`
* Тело: JSON — массив значений или объект с именованными полями (поддерживаются оба формата).
* Обработка:

  * **Валидация Pydantic:** строгая проверка типов и формата данных через `LogItem` схему
  * Валидация токена и роли (user может сохранять)
  * Преобразование данных в поля таблицы
  * Вставка в `logs` (created_at DEFAULT now())
  * После вставки — запуск функции очистки старых записей (retention)
* Ответ:

  * 201 Created + JSON `{ "id": <log_id>, "created_at": "<ts>" }` (`LogCreateResponse`)
  * При ошибке валидации — 422 Unprocessable Entity с детализацией ошибок
  * При других ошибках — 4xx/5xx с подробным сообщением

#### Маппинг для POST (массив) — порядок элементов:

```
0  — channel_id               (Уникальный номер канала общения)
1  — user_social_id           (Уникальный номер клиента)
2  — user_message             (Фраза клиента)
3  — bot_reply                (Фраза бота)
4  — channel_name             (Канал связи)
5  — bot_id                   (Номер бота)
6  — llm                      (LLM)
7  — api_key                  (Ключ)
8  — tokens_total             (Расход в токенах SMAIPL) — numeric/int
9  — tokens_in_source         (Входящие без коэффициента) — numeric
10 — tokens_out_source        (Исходящие без коэффициента) — numeric
11 — function_error           (Ошибка при выполнении функции)
12 — function_call_params     (Вызов функции и параметры)
13 — server_name              (Сервер)
```

### GET /api/v1/logs — получить записи (фильтры + пагинация)

* Заголовки:

  * `Authorization: Bearer <token>`

* Query params (опционально):

    * `from` — datetime ISO (начало диапазона created_at)
    * `to` — datetime ISO (конец диапазона created_at)
    * `channel_id` — string (старый unique_channel_number)
    * `channel_name` — string
    * `bot_id` — string (старый bot_number)
    * `server_name` — string (старый server)
    * `page` — int (по умолчанию 1)
    * `page_size` — int (по умолчанию 10, макс, например 100)
    * `sort_by` — поле для сортировки (по дефолту `created_at`)
    * `order` — `asc|desc` (по дефолту `desc`)  

* Дополнительные параметры поиска (нестрогий поиск по подстроке):
  * `user_social_id`
  * `user_message`
  * `bot_reply`
  * `llm`
  * `function_error`

* **Валидация Pydantic:** все query-параметры проходят строгую проверку типов
* Правила выдачи в зависимости от роли:

  * `user`:
    * Если нет параметров фильтра — возвращаем пустой набор
    * Если есть хотя бы один параметр фильтра — фильтруем по заданным параметрам

  * `admin`:
    * Если нет параметров фильтра — возвращаем все записи
    * Если заданы фильтры — применяем их

* Ответ:

  * 200 OK `LogsListResponse`: `{ "page": N, "page_size": M, "total": T, "items": [ ... ] }`

### GET /healthcheck — проверка состояния сервиса

* Ответ:
  * 200 OK `HealthCheckResponse`: `{ "status": "ok", "database": "connected" }`
  * 500 Error `HealthCheckResponse`: `{ "status": "error", "database": "disconnected", "error": "..." }`

---

## 4. Администрирование токенов

* Эндпоинты:

  * `POST /api/v1/tokens/generate` — генерирует новый токен (только admin)
  * `GET /api/v1/tokens` — список токенов (admin) ❗**НЕ РЕАЛИЗОВАНО**
  * `DELETE /api/v1/tokens/{id}` — отозвать токен (admin) ❗**НЕ РЕАЛИЗОВАНО**

* **Валидация Pydantic:** все запросы на генерацию токенов проходят строгую проверку через `TokenGenerationRequest`
* Ответ: `TokenGenerationResponse` - `{ "token": "...", "role": "..." }`
* Инициализация первого администратора:
  ```bash
  docker-compose exec app python -m app.init_admin
  ```

---

## 5. Политика хранения и автоматическая очистка (retention)

* Глобальная настройка `RETENTION_DAYS` (по умолчанию 30).
* Механизм удаления: при каждой вставке (POST /logs) выполняется `DELETE FROM logs WHERE created_at < now() - interval 'RETENTION_DAYS days'`.
* Настройка через переменную окружения.

---

## 6. Визуализация и мониторинг (Grafana) ✅ **РЕАЛИЗОВАНО**

**Развёртывание:** на том же сервере/домене, базовый путь `/grafana`

**Функциональность:**

* **Дашборды** — создание пользовательских панелей мониторинга
* **Аналитика** — агрегация данных, графики, тренды
* **Фильтрация** — мощная система фильтров по всем полям логов
* **SQL-запросы** — прямой доступ к данным через PostgreSQL
* **Авторизация** — отдельная система аутентификации в Grafana

**Преимущества перед кастомной админкой:**
- Готовые визуализации и графики
- Продвинутая аналитика out-of-the-box
- Сохранение и шаринг дашбордов
- Оповещения и мониторинг в реальном времени
- Поддержка множества данных источников

---

## 7. Технологический стек

1. **FastAPI + PostgreSQL + Uvicorn** — асинхронное API
2. **Pydantic** — строгая валидация данных и типизация
3. **Docker Compose:** сервисы: app, postgres, caddy (https), grafana
4. **Grafana** — визуализация и мониторинг
5. **Caddy** — обратный прокси и HTTPS

---

## 8. Валидация данных (Pydantic)

### Реализованные схемы валидации:

#### `LogItem` - создание записи лога
```python
class LogItem(BaseModel):
    channel_id: Optional[str] = None
    user_social_id: Optional[str] = None
    user_message: Optional[str] = None
    bot_reply: Optional[str] = None
    channel_name: Optional[str] = None
    bot_id: Optional[str] = None
    llm: Optional[str] = None
    api_key: Optional[str] = None
    tokens_total: int
    tokens_in_source: int
    tokens_out_source: int
    function_error: Optional[str] = None
    function_call_params: Optional[str] = None
    server_name: Optional[str] = None
```

#### `LogCreateResponse` - ответ при создании лога
```python
class LogCreateResponse(BaseModel):
    id: int
    created_at: datetime
```

#### `LogResponse` - полная запись лога (наследует LogItem)
```python
class LogResponse(LogItem):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
```

#### `LogsListResponse` - список логов с пагинацией
```python
class LogsListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[LogResponse]
```

#### `TokenGenerationRequest` - запрос генерации токена
```python
class TokenGenerationRequest(BaseModel):
    role: str
    comment: Optional[str] = None
    expires_at: Optional[datetime] = None
```

#### `TokenGenerationResponse` - ответ с токеном
```python
class TokenGenerationResponse(BaseModel):
    token: str
    role: str
```

#### `HealthCheckResponse` - статус здоровья сервиса
```python
class HealthCheckResponse(BaseModel):
    status: str
    database: str
    error: Optional[str] = None
```

### Преимущества Pydantic валидации:
- **Автоматическая документация** — схемы интегрируются с Swagger UI
- **Безопасность типов** — предотвращение ошибок времени выполнения
- **Детализированные ошибки** — понятные сообщения при невалидных данных
- **Производительность** — быстрая валидация на основе моделей
- **Сериализация** — автоматическое преобразование типов при вводе/выводе
- **ORM-совместимость** — поддержка `orm_mode` для работы с БД

---

## 9. Таблицы (миграции)

1. **logs**

```sql
CREATE TABLE logs (
  id BIGSERIAL PRIMARY KEY,
  channel_id TEXT,
  user_social_id TEXT,
  user_message TEXT,
  bot_reply TEXT,
  channel_name TEXT,
  bot_id TEXT,
  llm TEXT,
  api_key TEXT,
  tokens_total BIGINT,
  tokens_in_source BIGINT,
  tokens_out_source BIGINT,
  function_error TEXT,
  function_call_params TEXT,
  server_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Базовые индексы
CREATE INDEX idx_logs_created_at ON logs (created_at DESC);
CREATE INDEX idx_logs_channel_id ON logs (channel_id);
CREATE INDEX idx_logs_channel_name ON logs (channel_name);
CREATE INDEX idx_logs_bot_id ON logs (bot_number);
CREATE INDEX idx_logs_server_name ON logs (server_name);

-- GIN-индексы для полнотекстового поиска
CREATE INDEX logs_channel_id_gin_idx ON logs USING gin (channel_id gin_trgm_ops);
CREATE INDEX logs_user_social_id_gin_idx ON logs USING gin (user_social_id gin_trgm_ops);
CREATE INDEX logs_user_message_gin_idx ON logs USING gin (user_message gin_trgm_ops);
CREATE INDEX logs_bot_reply_gin_idx ON logs USING gin (bot_reply gin_trgm_ops);
CREATE INDEX logs_channel_name_gin_idx ON logs USING gin (channel_name gin_trgm_ops);
CREATE INDEX logs_bot_id_gin_idx ON logs USING gin (bot_id gin_trgm_ops);
CREATE INDEX logs_llm_gin_idx ON logs USING gin (llm gin_trgm_ops);
CREATE INDEX logs_function_error_gin_idx ON logs USING gin (function_error gin_trgm_ops);
CREATE INDEX logs_server_name_gin_idx ON logs USING gin (server_name gin_trgm_ops);
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

---

## 10. Безопасность

* Токены: хранить в базе только хэш (SHA256 + PEPPER)
* HTTPS — Caddy в docker-compose
* SQL-инъекции: использование параметризованных запросов через asyncpg
* **Валидация Pydantic:** защита от невалидных данных и инъекций
* Переменные окружения для всех чувствительных данных
* Изолированная сеть Docker между сервисами

---

## 11. Тесты

* Unit tests для: парсинга POST, валидации, авторизации токенов, фильтров GET, retention-logic ❗**НЕ РЕАЛИЗОВАНО**
* Integration test: end-to-end с тестовой БД ❗**НЕ РЕАЛИЗОВАНО**

---

## 12. Docker Compose (схема)

* services:
  * app (Uvicorn + FastAPI + Pydantic)
  * postgres (volume)
  * caddy (https)
  * grafana (визуализация и мониторинг)
* Environment variables: DATABASE_URL, SECRET_KEY, RETENTION_DAYS, TOKEN_PEPPER, GRAFANA_ADMIN_PASSWORD

---

## 13. План работ

**Этап 1 (API) — РЕАЛИЗОВАНО:**

1. ✅ Создать проект, настройки Docker Compose
2. ✅ Модель `logs`, миграции
3. ✅ Реализовать `POST /api/v1/logs` (поддержка двух форматов)
4. ✅ Реализовать `GET /api/v1/logs` с фильтрами и пагинацией
5. ✅ Таблица `api_tokens`, генерация токенов, middleware авторизации
6. ✅ Healthcheck эндпоинт
7. ✅ GIN-индексы для полнотекстового поиска
8. ✅ Интеграция Grafana для визуализации и мониторинга
9. ✅ **Pydantic валидация** для всех входных данных и API-эндпоинтов

**Будущие улучшения:**

1. Эндпоинты управления токенами (GET/DELETE)
2. Unit и интеграционные тесты
3. Расширенная документация API
4. Мониторинг производительности и метрик

---

## 14. Архитектурные особенности реализации

### Реализованные улучшения:
- **Асинхронная архитектура** на FastAPI + asyncpg
- **Два формата ввода** (массив и объект)
- **Расширенный поиск** по всем текстовым полям через GIN-индексы
- **Healthcheck мониторинг**
- **Интеграция Grafana** для визуализации и аналитики
- **Автоматический реконнект** к БД
- **Строгая валидация Pydantic** для всех API-эндпоинтов

### Ключевые изменения архитектуры:
- **Замена кастомной админки на Grafana** - готовая система визуализации вместо разработки с нуля
- **FastAPI вместо Django** - более легковесное и асинхронное решение
- **Grafana для мониторинга** - профессиональные дашборды и аналитика out-of-the-box
- **Pydantic для валидации** - типобезопасность и автоматическая документация

---

## 15. Деплой и эксплуатация

### Первоначальная настройка:
```bash
# Запуск всех сервисов
docker-compose up --build -d

# Создание первого административного токена
docker-compose exec app python -m app.init_admin

# Проверка здоровья сервиса
curl http://localhost/healthcheck
```

### Ключевые эндпоинты:
- API: `https://domain.com/api/v1/...`
- Документация API: `https://domain.com/docs` (автогенерация через Pydantic + Swagger)
- Grafana: `https://grafana.domain.com/`
- Healthcheck: `https://domain.com/healthcheck`

### Мониторинг и визуализация:
- **Grafana дашборды** доступны по пути `/grafana`
- **Просмотр логов** через готовые панели Grafana
- **Аналитика и тренды** - встроенные инструменты Grafana
- **Метрики здоровья** через эндпоинт `/healthcheck`
- **Логи приложения** через Docker Compose
- **Валидация ошибок** - детализированные сообщения через Pydantic
```