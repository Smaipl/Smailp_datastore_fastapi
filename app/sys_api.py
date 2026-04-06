# API for system deeds
from fastapi import FastAPI, Depends, Body
from .auth import get_token_info
from .schemas import LogCreateResponse
from .log import inf, dbg
from .db import get_db
from fastapi import HTTPException
from datetime import datetime
from typing import Any
from asyncpg.pool import PoolConnectionProxy, Pool


# Log record:
#  {
# 'fields': {
# 'filename': 'utils.py',
# 'funcName': 'check_jwt',
# 'lineno': 52,
# 'message': 'No JWT found in payload'
# },
# 'name': 'log',
# 'tags': {
# 'host': 'bljmiixobp',
# 'level': 'WARNING',
# 'logger': 'smaipl.functions',
# 'path': '/opt/smaipl_functions/influx-logs/smaipl_functions.log'
# },
# 'timestamp': 1775496393
# }


def extract_log_measurements(metrics: list):
    for it in metrics:
        if it.get("name") != "log":
            continue
        fields = it.get("fields", {})
        tags = it.get("tags", {})
        yield {
            "timestamp": it.get("timestamp"),
            "name": it.get("name"),
            "filename": fields.get("filename"),
            "funcname": fields.get("funcName"),
            "lineno": fields.get("lineno"),
            "message": fields.get("message"),
            "host": tags.get("host"),
            "level": tags.get("level"),
            "logger": tags.get("logger"),
            "path": tags.get("path"),
        }


async def create_log(request: Any = Body(...), auth=Depends(get_token_info)):
    inf("Received log: %s", request)

    logs = list(extract_log_measurements(request.get("metrics", [])))
    if not logs:
        dbg("No log measurements found in the request")
        return

    dbg("Extracted %d log measurements", len(logs))
    values = [
        (
            log["timestamp"],
            log["host"],
            log["logger"],
            log["level"],
            log["filename"],
            log["funcname"],
            log["lineno"],
            log["message"],
            log["path"]
        )
        for log in logs
    ]

    pool = await get_db()

    conn: Pool
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO system_logs (
                timestamp, host, logger, level, filename, funcname, lineno, message, path
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9
            )
            """,
            values
        )
        dbg("Inserted %d log records into the database", len(values))


def register_sys_api(app: FastAPI):
    app.post("/api/v1/system/log")(create_log)