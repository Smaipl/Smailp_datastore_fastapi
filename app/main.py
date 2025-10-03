from fastapi import FastAPI, Depends, HTTPException, Request
from datetime import datetime, timezone, timedelta
import secrets, os
from app.db import get_db
from app.auth import get_token_info
from app.utils import hash_token

app = FastAPI(title="Log Storage Service (FastAPI)")

RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))

POST_ORDER = [
    "unique_channel_number",
    "unique_client_number",
    "client_phrase",
    "bot_phrase",
    "channel_name",
    "bot_number",
    "llm",
    "api_key_masked",
    "tokens_spent_smaipl",
    "inbound_without_coefficient",
    "outbound_without_coefficient",
    "function_error",
    "function_call_and_params",
    "server_name",
]


@app.on_event("startup")
async def startup():
    await get_db()


@app.post("/api/v1/tokens/generate")
async def generate_token(request: Request, auth=Depends(get_token_info)):
    if auth["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    body = await request.json()
    role = body.get("role")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")
    raw_token = secrets.token_urlsafe(32)
    hashed = hash_token(raw_token)
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_tokens (token_hash, role, comment, expires_at, created_by) VALUES ($1,$2,$3,$4,$5)",
            hashed,
            role,
            body.get("comment"),
            body.get("expires_at"),
            "admin_api",
        )
    return {"token": raw_token, "role": role}


@app.post("/api/v1/logs")
async def create_log(request: Request, auth=Depends(get_token_info)):
    body = await request.json()
    if isinstance(body, list):
        if len(body) != 14:
            raise HTTPException(status_code=400, detail="Array must have 14 elements")
        payload = dict(zip(POST_ORDER, body))
    elif isinstance(body, dict):
        payload = {k: body.get(k) for k in POST_ORDER}
    else:
        raise HTTPException(status_code=400, detail="Invalid body format")

    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO logs (
                unique_channel_number, unique_client_number, client_phrase, bot_phrase,
                channel_name, bot_number, llm, api_key_masked, tokens_spent_smaipl,
                inbound_without_coefficient, outbound_without_coefficient,
                function_error, function_call_and_params, server_name
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14
            ) RETURNING id, created_at
            """,
            payload["unique_channel_number"],
            payload["unique_client_number"],
            payload["client_phrase"],
            payload["bot_phrase"],
            payload["channel_name"],
            payload["bot_number"],
            payload["llm"],
            payload["api_key_masked"],
            payload["tokens_spent_smaipl"],
            payload["inbound_without_coefficient"],
            payload["outbound_without_coefficient"],
            payload["function_error"],
            payload["function_call_and_params"],
            payload["server_name"],
        )
        await conn.execute(
            "DELETE FROM logs WHERE created_at < now() - ($1::int * INTERVAL '1 day')",
            RETENTION_DAYS,
        )
    return {"id": row["id"], "created_at": row["created_at"].isoformat()}
