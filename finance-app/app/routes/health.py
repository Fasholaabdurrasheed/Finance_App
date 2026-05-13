from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import text

from app.schemas.health import HealthResponse
from app.database.connection import engine

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Simple health check; returns API and DB status."""
    # Basic DB connectivity check; simple and non-blocking
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        detail={"db_connected": db_ok, "timestamp": datetime.now(timezone.utc).isoformat()},
        version="1.0.0",
    )
