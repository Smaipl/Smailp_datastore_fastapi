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
    unique_channel_number: str
    unique_client_number: str
    client_phrase: str
    bot_phrase: str
    channel_name: str
    bot_number: str
    llm: str
    api_key_masked: str
    tokens_spent_smaipl: int
    inbound_without_coefficient: int
    outbound_without_coefficient: int
    function_error: Optional[str] = None
    function_call_and_params: str
    server_name: str


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
