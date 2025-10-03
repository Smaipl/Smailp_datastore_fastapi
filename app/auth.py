from fastapi import Depends, HTTPException, Header
from datetime import datetime, timezone
from .db import get_db
from .utils import hash_token


async def get_token_info(authorization: str = Header(...)):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Authorization must be Bearer token"
        )
    raw_token = authorization.split(None, 1)[1]
    hashed = hash_token(raw_token)

    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, role, expires_at FROM api_tokens WHERE token_hash=$1", hashed
        )
        if not row:
            raise HTTPException(status_code=403, detail="Invalid token")
        if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Token expired")
        return {"id": row["id"], "role": row["role"]}
