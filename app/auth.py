from fastapi import Depends, HTTPException, Header
from datetime import datetime, timezone
from typing import Dict
from app.db import get_db
from app.utils import hash_token
import asyncpg

"""
Модуль auth: Аутентификация и авторизация
Компоненты:
  - get_token_info: Получение информации о токене
"""


async def get_token_info(authorization: str = Header(...)) -> Dict[str, str]:
    """
    Проверяет Bearer токен и возвращает информацию о нём

    Args:
        authorization: Заголовок Authorization в формате "Bearer <token>"

    Returns:
        dict: Словарь с информацией о токене (id, role)

    Вызывает:
        HTTPException 401: Неправильный формат токена
        HTTPException 403: Неверный или просроченный токен
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Authorization must be Bearer token"
        )
    raw_token = authorization.split(None, 1)[1]
    hashed = hash_token(raw_token)

    pool = await get_db()
    async with pool.acquire() as conn:
        row: asyncpg.Record = await conn.fetchrow(
            "SELECT id, role, expires_at FROM api_tokens WHERE token_hash=$1", hashed
        )
        if not row:
            raise HTTPException(status_code=403, detail="Invalid token")
        if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Token expired")
        return {"id": str(row["id"]), "role": row["role"]}
