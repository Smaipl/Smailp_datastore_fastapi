# API for system deeds
from fastapi import FastAPI, Depends, Body
from .auth import get_token_info
from .schemas import LogCreateResponse
from .log import inf, dbg
from datetime import datetime


async def create_log(request: Any = Body(...), auth=Depends(get_token_info)):
    inf("Received log: %s", request)
    return LogCreateResponse(
        id=0,
        created_at=datetime.now().isoformat()
    )


def register_sys_api(app: FastAPI):
    app.post("/api/v1/system/log", response_model=LogCreateResponse)(create_log)