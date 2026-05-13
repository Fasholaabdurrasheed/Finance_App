from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.upload import Upload
from app.schemas.upload import (
    ExcelUploadPreview,
    ExcelUploadResponse,
    UploadMetadata,
    UploadListResponse,
    UploadStatusResponse,
)
from app.services.upload_service import ExcelUploadService
from app.services.import_job_service import ImportJobService
from app.utils.logger import get_logger
from app.utils.storage import save_file_local

logger = get_logger("app.routes.uploads")

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])

# Configuration constants
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".csv"}

BASE_UPLOADS_PATH = Path(__file__).resolve().parents[2] / "uploads"
BASE_UPLOADS_PATH.mkdir(exist_ok=True)


@router.post("/excel/preview", response_model=ExcelUploadPreview)
async def preview_excel_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExcelUploadPreview:
    """
    Preview Excel file before importing.
    
    - Requires: Bearer token from POST /api/v1/auth/login (Swagger Authorize)
    - Accepts: multipart/form-data with file field
    - Returns: validation summary, detected columns, error list
    - Does NOT import data, just validates structure
    
    Parameter order (critical for FastAPI multipart handling):
    1. file: UploadFile = File(...) — multipart form data
    2. current_user: User = Depends(get_current_user) — JWT dependency
    3. db: Session = Depends(get_db) — DB session dependency
    
    The Authorization header (Bearer token) is automatically extracted
    by OAuth2PasswordBearer in get_current_user dependency.
    """
    logger.info(f"Preview upload started: filename={file.filename}, user_id={current_user.id}")
    
    if not file.filename:
        logger.warning(f"Upload preview rejected: missing filename, user_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required"
        )
    
    # Validate file extension
    file_ext = "." + (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "")
    if file_ext.lower() not in ALLOWED_EXTENSIONS:
        logger.warning(
            f"Upload preview rejected: invalid extension={file_ext}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file_ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file into memory
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error(
            f"Failed to read file: {exc}, filename={file.filename}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file"
        ) from exc
    
    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        logger.warning(
            f"Upload preview rejected: file too large={len(file_bytes)} bytes, "
            f"max={MAX_FILE_SIZE_BYTES}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({len(file_bytes)} bytes) exceeds maximum ({MAX_FILE_SIZE_BYTES} bytes)"
        )
    
    logger.info(
        f"Preview upload processing: filename={file.filename}, "
        f"size={len(file_bytes)} bytes, user_id={current_user.id}"
    )
    try:
        result = ExcelUploadService(db).preview(file.filename, file_bytes)
        logger.info(
            f"Preview upload completed: total_rows={result.total_rows}, "
            f"valid_rows={result.valid_rows}, errors={len(result.validation_errors)}"
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Preview upload failed with exception: {exc}, user_id={current_user.id}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {str(exc)}"
        ) from exc


@router.get("/", response_model=UploadListResponse)
async def list_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadListResponse:
    uploads = db.query(Upload).filter(Upload.user_id == current_user.id).order_by(Upload.created_at.desc()).all()
    return UploadListResponse(uploads=uploads)


@router.get("/{upload_id}", response_model=UploadMetadata)
async def get_upload(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadMetadata:
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current_user.id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload


@router.get("/{upload_id}/download")
async def download_upload(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current_user.id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    if upload.status == "deleted":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Upload has been deleted")
    return FileResponse(path=upload.storage_path, filename=upload.original_filename)


@router.post("/{upload_id}/reprocess", response_model=ExcelUploadResponse)
async def reprocess_upload(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExcelUploadResponse:
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current_user.id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    if upload.status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload is already processing")

    try:
        # read file bytes
        with open(upload.storage_path, "rb") as f:
            file_bytes = f.read()

        upload.status = "processing"
        db.add(upload)
        db.commit()
        db.refresh(upload)

        result = ExcelUploadService(db).process(current_user, upload.original_filename, file_bytes, upload_id=upload.id)
        db.refresh(upload)
        return result
    except HTTPException:
        upload.status = "failed"
        db.add(upload)
        db.commit()
        raise
    except Exception as exc:
        upload.status = "failed"
        upload.error = str(exc)
        db.add(upload)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{upload_id}")
async def delete_upload(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current_user.id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    # Soft delete: mark status deleted; do NOT remove transactions automatically
    upload.status = "deleted"
    db.add(upload)
    db.commit()
    return {"message": "Upload marked deleted"}


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def upload_status(
    upload_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadStatusResponse:
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current_user.id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return UploadStatusResponse(
        id=upload.id,
        status=upload.status,
        processed_at=upload.processed_at,
        rows_total=upload.rows_total,
        rows_inserted=upload.rows_inserted,
        error=upload.error,
    )


@router.post("/excel", response_model=ExcelUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_excel_transactions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExcelUploadResponse:
    """
    Upload and import Excel file with transactions.
    
    - Requires: Bearer token from POST /api/v1/auth/login (Swagger Authorize)
    - Accepts: multipart/form-data with file field
    - Returns: import summary with row counts and category creation
    - Side effects: creates transactions, deduplicates, creates categories
    
    Parameter order (critical for FastAPI multipart handling):
    1. file: UploadFile = File(...) — multipart form data
    2. current_user: User = Depends(get_current_user) — JWT dependency  
    3. db: Session = Depends(get_db) — DB session dependency
    
    The Authorization header (Bearer token) is automatically extracted
    by OAuth2PasswordBearer in get_current_user dependency.
    """
    logger.info(f"Excel upload started: filename={file.filename}, user_id={current_user.id}")
    
    if not file.filename:
        logger.warning(f"Upload rejected: missing filename, user_id={current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required"
        )
    
    # Validate file extension
    file_ext = "." + (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "")
    if file_ext.lower() not in ALLOWED_EXTENSIONS:
        logger.warning(
            f"Upload rejected: invalid extension={file_ext}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file_ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file into memory
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error(
            f"Failed to read file: {exc}, filename={file.filename}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file"
        ) from exc
    
    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        logger.warning(
            f"Upload rejected: file too large={len(file_bytes)} bytes, "
            f"max={MAX_FILE_SIZE_BYTES}, user_id={current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({len(file_bytes)} bytes) exceeds maximum ({MAX_FILE_SIZE_BYTES} bytes)"
        )
    
    logger.info(
        f"Excel upload processing: filename={file.filename}, "
        f"size={len(file_bytes)} bytes, user_id={current_user.id}"
    )

    # Save file to storage and create Upload record
    try:
        storage_path, size, checksum = save_file_local(file.filename, file_bytes)
        upload = Upload(
            user_id=current_user.id,
            original_filename=file.filename,
            storage_path=storage_path,
            content_type=file.content_type,
            size=size,
            checksum=checksum,
            status="processing",
        )
        db.add(upload)
        db.flush()  # assign upload.id
        upload_id = upload.id
        # create import job for processing
        job = ImportJobService(db).create_job(upload_id=upload_id, message="Enqueued via API upload")
    except Exception as exc:
        logger.exception("Failed to persist uploaded file to storage or DB")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file"
        ) from exc

    try:
        # mark job running then process
        ImportJobService(db).mark_running(job, message="Starting processing")
        result = ExcelUploadService(db).process(current_user, file.filename, file_bytes, upload_id=upload_id)
        ImportJobService(db).mark_complete(job, message="Processing complete")
        logger.info(
            f"Excel upload completed: total_rows={result.total_rows}, "
            f"inserted_rows={result.inserted_rows}, duplicates={result.duplicate_rows}, "
            f"invalid_rows={result.invalid_rows}, created_categories={result.created_categories}"
        )

        # Refresh upload row info
        db.refresh(upload)
        return result
    except HTTPException:
        # mark upload as failed with provided details
        upload.status = "failed"
        try:
            ImportJobService(db).mark_failed(job, error=str(upload.status))
        except Exception:
            pass
        db.add(upload)
        db.commit()
        raise
    except Exception as exc:
        logger.error(
            f"Excel upload failed with exception: {exc}, user_id={current_user.id}",
            exc_info=True
        )
        upload.status = "failed"
        upload.error = str(exc)
        try:
            ImportJobService(db).mark_failed(job, error=str(exc))
        except Exception:
            pass
        db.add(upload)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File import failed: {str(exc)}"
        ) from exc