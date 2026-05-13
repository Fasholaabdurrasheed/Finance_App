from pydantic import BaseModel


class HealthDetail(BaseModel):
    db_connected: bool
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    detail: HealthDetail
    version: str
