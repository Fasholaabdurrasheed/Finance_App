from app.database.connection import engine
from app.models import Base
from app.utils.logger import get_logger

logger = get_logger("app.database.init_db")


def init_db() -> None:
    """Create database tables if they don't exist.
    
    For MVP bootstrap. In production, prefer Alembic migrations.
    Catches connection errors gracefully so app can still start.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as exc:
        logger.warning(
            "Failed to initialize database tables. "
            "Check DATABASE_URL and ensure the database server is running.",
            extra={"error": str(exc)},
        )
