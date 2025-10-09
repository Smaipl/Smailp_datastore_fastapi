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
    unique_channel_number: Optional[str] = None
    unique_client_number: Optional[str] = None
    client_phrase: Optional[str] = None
    bot_phrase: Optional[str] = None
    channel_name: Optional[str] = None
    bot_number: Optional[str] = None
    llm: Optional[str] = None
    api_key_masked: Optional[str] = None
    tokens_spent: int
    inbound_without_coefficient: int
    outbound_without_coefficient: int
    function_error: Optional[str] = None
    function_call_and_params: Optional[str] = None
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
