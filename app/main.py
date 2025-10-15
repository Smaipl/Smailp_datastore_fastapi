from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Request, Query, Body
from app.schemas import (
    TokenGenerationRequest,
    TokenGenerationResponse,
    LogItem,
    LogCreateResponse,
    LogsListResponse,
    HealthCheckResponse,
)
import json

"""
Модуль main: Основное FastAPI приложение для хранения логов и управления токенами

Основные компоненты:
  - app: Экземпляр FastAPI приложения
  - Эндпоинты:
    * POST /api/v1/tokens/generate - Генерация API токенов
    * POST /api/v1/logs - Создание записей логов
    * GET /api/v1/logs - Получение записей логов с фильтрацией и пагинацией

Дополнительно:
  - Переменная RETENTION_DAYS: Период хранения логов (дни)
  - Список POST_ORDER: Порядок полей для вставки логов
"""
from datetime import datetime, timezone, timedelta
import secrets, os
from app.db import get_db
from app.auth import get_token_info
from app.utils import hash_token, fix_plus_sign

app = FastAPI(title="Log Storage Service (FastAPI)")

RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))

POST_ORDER = [
    "channel_id",
    "user_social_id",
    "user_message",
    "bot_reply",
    "channel_name",
    "bot_id",
    "llm",
    "api_key",
    "tokens_total",
    "tokens_in_source",
    "tokens_out_source",
    "function_error",
    "function_call_params",
    "server_name",
    "tokens_user",
]


@app.get("/healthcheck", include_in_schema=False, response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint to verify service and database connectivity
    Returns:
        HealthCheckResponse: Status and database connection status
    """
    try:
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return HealthCheckResponse(status="ok", database="connected")
    except Exception as e:
        return HealthCheckResponse(
            status="error", database="disconnected", error=str(e)
        )


@app.on_event("startup")
async def startup():
    """
    Инициализация приложения при запуске

    Действия:
      - Устанавливает подключение к базе данных
    """
    await get_db()


@app.post("/api/v1/tokens/generate", response_model=TokenGenerationResponse)
async def generate_token(request: TokenGenerationRequest, auth=Depends(get_token_info)):
    """
    Генерация нового API токена (доступно только администраторам)

    Параметры запроса:
      - role: Роль токена (admin/user)
      - comment: Комментарий к токену (опционально)
      - expires_at: Дата истечения срока действия (опционально)

    Возвращает:
      - token: Сгенерированный сырой токен
      - role: Роль токена

    Ошибки:
      - 403: Для не-администраторов
      - 400: При указании недопустимой роли
    """
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    if request.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")

    raw_token = secrets.token_urlsafe(32)
    hashed = hash_token(raw_token)
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_tokens (token_hash, role, comment, expires_at, created_by) VALUES ($1,$2,$3,$4,$5)",
            hashed,
            request.role,
            request.comment,
            request.expires_at,
            "admin_api",
        )
    return TokenGenerationResponse(token=raw_token, role=request.role)


@app.post("/api/v1/logs", response_model=LogCreateResponse)
async def create_log(request: Any = Body(...), auth=Depends(get_token_info)):
    """
    Создание новой записи лога (доступно всем авторизованным пользователям)

    Возвращает:
      - id: Идентификатор созданной записи
      - created_at: Время создания записи

    Дополнительно:
      - Автоматически удаляет записи старше RETENTION_DAYS дней
    """
    # Обработка массива (устаревший формат)
    if isinstance(request, list):
        if len(request) != len(POST_ORDER):
            raise HTTPException(
                status_code=400,
                detail=f"Ожидается {len(POST_ORDER)} элементов, получено {len(request)}",
            )

        # Преобразуем массив в словарь используя POST_ORDER
        request = dict(zip(POST_ORDER, request))

    # Проверяем и конвертируем в LogItem
    log_item = LogItem(**request)

    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO logs (
                channel_id, user_social_id, user_message, bot_reply,
                channel_name, bot_id, llm, api_key, tokens_total,
                tokens_in_source, tokens_out_source,
                function_error, function_call_params, server_name, tokens_user
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15
            ) RETURNING id, created_at
            """,
            log_item.channel_id,
            log_item.user_social_id,
            log_item.user_message,
            log_item.bot_reply,
            log_item.channel_name,
            log_item.bot_id,
            log_item.llm,
            log_item.api_key,
            log_item.tokens_total,
            log_item.tokens_in_source,
            log_item.tokens_out_source,
            log_item.function_error,
            log_item.function_call_params,
            log_item.server_name,
            log_item.tokens_user,
        )
        await conn.execute(
            "DELETE FROM logs WHERE created_at < now() - ($1::int * INTERVAL '1 day')",
            RETENTION_DAYS,
        )
    return LogCreateResponse(id=row["id"], created_at=row["created_at"])


@app.get("/api/v1/logs")
async def get_logs(
    request: Request,
    auth=Depends(get_token_info),
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to"),
    channel_id: str = Query(None),
    user_social_id: str = Query(None),
    user_message: str = Query(None),
    bot_reply: str = Query(None),
    channel_name: str = Query(None),
    bot_id: str = Query(None),
    llm: str = Query(None),
    function_error: str = Query(None),
    server_name: str = Query(None),
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    """
    Получение логов с фильтрацией и пагинацией

    Параметры запроса:
      - from: Начало диапазона времени (ISO формат)
      - to: Конец диапазона времени (ISO формат)
      - channel_id: Номер канала
      - channel_name: Название канала
      - bot_id: Номер бота
      - server_name: Имя сервера
      - page: Номер страницы (начиная с 1)
      - page_size: Размер страницы (1-100)
      - sort_by: Поле для сортировки
      - order: Порядок сортировки (asc/desc)

    Правила доступа:
      - user: Только при наличии хотя бы одного фильтра
      - admin: Без ограничений

    Возвращает:
      - page: Текущая страница
      - page_size: Размер страницы
      - total: Общее количество записей
      - items: Список записей логов
    """
    # Validate order parameter
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400, detail="Invalid order, use 'asc' or 'desc'"
        )

    # Validate sort_by parameter
    valid_columns = [
        "id",
        "channel_id",
        "user_social_id",
        "user_message",
        "bot_reply",
        "channel_name",
        "bot_id",
        "llm",
        "api_key",
        "tokens_total",
        "tokens_in_source",
        "tokens_out_source",
        "tokens_user",
        "function_error",
        "function_call_params",
        "server_name",
        "created_at",
    ]
    if sort_by not in valid_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by, allowed: {', '.join(valid_columns)}",
        )

    # Validate filter parameters
    allowed_params = {
        "from",
        "to",
        "channel_id",
        "user_social_id",
        "user_message",
        "bot_reply",
        "channel_name",
        "bot_id",
        "llm",
        "function_error",
        "server_name",
        "page",
        "page_size",
        "sort_by",
        "order",
    }

    query_params = set(request.query_params.keys())
    invalid_params = query_params - allowed_params

    if invalid_params:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемые параметры фильтрации: {', '.join(invalid_params)}",
        )

    # Handle user role restrictions
    if auth["role"] == "user" and not any(
        [
            from_date,
            to_date,
            channel_id,
            user_social_id,
            user_message,
            bot_reply,
            channel_name,
            bot_id,
            llm,
            function_error,
            server_name,
        ]
    ):
        return {"page": page, "page_size": page_size, "total": 0, "items": []}

    # Build SQL query with filters
    conditions = []
    params = []

    if from_date:
        conditions.append("created_at >= $%d" % (len(params) + 1))
        params.append(datetime.fromisoformat(from_date))
    if to_date:
        conditions.append("created_at <= $%d" % (len(params) + 1))
        params.append(datetime.fromisoformat(to_date))

    # Handle + sign in query parameters and enable partial matching
    # (function fix_plus_sign now imported from utils)

    if channel_id:
        channel_id = fix_plus_sign(channel_id)
        conditions.append("channel_id ILIKE $%d" % (len(params) + 1))
        params.append(f"%{channel_id}%")
    if channel_name:
        channel_name = fix_plus_sign(channel_name)
        conditions.append("channel_name ILIKE $%d" % (len(params) + 1))
        params.append(f"%{channel_name}%")
    if bot_id:
        bot_id = fix_plus_sign(bot_id)
        conditions.append("bot_id ILIKE $%d" % (len(params) + 1))
        params.append(f"%{bot_id}%")
    if server_name:
        server_name = fix_plus_sign(server_name)
        conditions.append("server_name ILIKE $%d" % (len(params) + 1))
        params.append(f"%{server_name}%")
    # Add additional filters for other fields
    if user_social_id:
        user_social_id = fix_plus_sign(user_social_id)
        conditions.append("user_social_id ILIKE $%d" % (len(params) + 1))
        params.append(f"%{user_social_id}%")
    if user_message:
        user_message = fix_plus_sign(user_message)
        conditions.append("user_message ILIKE $%d" % (len(params) + 1))
        params.append(f"%{user_message}%")
    if bot_reply:
        bot_reply = fix_plus_sign(bot_reply)
        conditions.append("bot_reply ILIKE $%d" % (len(params) + 1))
        params.append(f"%{bot_reply}%")
    if llm:
        llm = fix_plus_sign(llm)
        conditions.append("llm ILIKE $%d" % (len(params) + 1))
        params.append(f"%{llm}%")
    if function_error:
        function_error = fix_plus_sign(function_error)
        conditions.append("function_error ILIKE $%d" % (len(params) + 1))
        params.append(f"%{function_error}%")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Build pagination
    offset = (page - 1) * page_size

    # Get total count
    pool = await get_db()
    async with pool.acquire() as conn:
        count_query = "SELECT COUNT(*) FROM logs" + where_clause
        total = await conn.fetchval(count_query, *params)

        # Build main query
        query = f"""
            SELECT 
                id, created_at, channel_id, user_social_id, user_message, bot_reply,
                channel_name, bot_id, llm, api_key, tokens_total, tokens_in_source,
                tokens_out_source, function_error, function_call_params, server_name,
                COALESCE(tokens_user, 0) AS tokens_user
            FROM logs
            {where_clause}
            ORDER BY {sort_by} {order}
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([page_size, offset])

        records = await conn.fetch(query, *params)

    # Convert records to dict and format datetime
    items = []
    for r in records:
        item = dict(r)
        item["created_at"] = item["created_at"].isoformat()
        items.append(item)

    return LogsListResponse(page=page, page_size=page_size, total=total, items=items)
