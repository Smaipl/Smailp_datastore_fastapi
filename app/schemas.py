from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class TokenGenerationRequest(BaseModel):
    role: str
    comment: Optional[str] = None
    expires_at: Optional[datetime] = None


class TokenGenerationResponse(BaseModel):
    token: str
    role: str


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


class LogCreateResponse(BaseModel):
    id: int
    created_at: datetime


class LogResponse(LogItem):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class LogsListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[LogResponse]


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    error: Optional[str] = None
