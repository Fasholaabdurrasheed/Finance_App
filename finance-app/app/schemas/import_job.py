from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobMetadata(BaseModel):
    id: int
    upload_id: int
    status: str
    progress: int
    logs: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportJobListResponse(BaseModel):
    jobs: list[ImportJobMetadata]

    model_config = ConfigDict(from_attributes=True)
