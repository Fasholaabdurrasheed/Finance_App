from datetime import datetime

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ExcelUploadResponse(BaseModel):
    success: bool = True
    message: str
    total_rows: int
    inserted_rows: int
    duplicate_rows: int
    invalid_rows: int
    created_categories: int
    file_name: str | None = None


class UploadValidationError(BaseModel):
    row_number: int
    message: str


class ExcelUploadPreview(BaseModel):
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    detected_columns: list[str]
    validation_errors: list[UploadValidationError]


class UploadJobMetadata(BaseModel):
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


class UploadMetadata(BaseModel):
    id: int
    user_id: int
    original_filename: str
    storage_path: str
    content_type: str | None
    size: int
    checksum: str
    status: str
    error: str | None = None
    created_at: datetime | None = None
    processed_at: datetime | None = None
    rows_total: int | None = None
    rows_inserted: int | None = None

    jobs: list[UploadJobMetadata] = []

    model_config = ConfigDict(from_attributes=True)


class UploadListResponse(BaseModel):
    uploads: list[UploadMetadata]

    model_config = ConfigDict(from_attributes=True)


class UploadStatusResponse(BaseModel):
    id: int
    status: str
    job: UploadJobMetadata | None = None
    processed_at: datetime | None = None
    rows_total: int | None = None
    rows_inserted: int | None = None
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)
