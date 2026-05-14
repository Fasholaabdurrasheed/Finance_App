from sqlalchemy import inspect, text

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
        _ensure_upload_schema()
        logger.info("Database tables initialized successfully")
    except Exception as exc:
        logger.warning(
            "Failed to initialize database tables. "
            "Check DATABASE_URL and ensure the database server is running.",
            extra={"error": str(exc)},
        )


def _ensure_upload_schema() -> None:
    """Apply lightweight schema repairs for upload provenance tables.

    This is a pragmatic bootstrap for environments that still use create_all()
    or have an existing database without the new Alembic revision applied yet.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "uploads" not in existing_tables:
            connection.execute(text(
                """
                CREATE TABLE uploads (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    original_filename VARCHAR(255) NOT NULL,
                    storage_path VARCHAR(1024) NOT NULL,
                    content_type VARCHAR(100),
                    size BIGINT NOT NULL,
                    checksum VARCHAR(128) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    processed_at TIMESTAMPTZ,
                    rows_total INTEGER,
                    rows_inserted INTEGER
                )
                """
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_uploads_user_id ON uploads (user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_uploads_checksum ON uploads (checksum)"))

        if "transactions" in existing_tables:
            transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
            if "upload_id" not in transaction_columns:
                connection.execute(text("ALTER TABLE transactions ADD COLUMN upload_id INTEGER"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_upload_id ON transactions (upload_id)"))
                connection.execute(text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_transactions_upload_id_uploads'
                        ) THEN
                            ALTER TABLE transactions
                            ADD CONSTRAINT fk_transactions_upload_id_uploads
                            FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE SET NULL;
                        END IF;
                    END $$;
                    """
                ))

        if "categories" in existing_tables:
            category_columns = {column["name"] for column in inspector.get_columns("categories")}
            if "upload_id" not in category_columns:
                connection.execute(text("ALTER TABLE categories ADD COLUMN upload_id INTEGER"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_categories_upload_id ON categories (upload_id)"))
                connection.execute(text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_categories_upload_id_uploads'
                        ) THEN
                            ALTER TABLE categories
                            ADD CONSTRAINT fk_categories_upload_id_uploads
                            FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE SET NULL;
                        END IF;
                    END $$;
                    """
                ))

        if "import_jobs" not in existing_tables and "uploads" in existing_tables:
            connection.execute(text(
                """
                CREATE TABLE import_jobs (
                    id SERIAL PRIMARY KEY,
                    upload_id INTEGER NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    progress INTEGER NOT NULL DEFAULT 0,
                    logs TEXT,
                    error TEXT,
                    started_at TIMESTAMPTZ,
                    finished_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ
                )
                """
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_import_jobs_upload_id ON import_jobs (upload_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_import_jobs_status ON import_jobs (status)"))
