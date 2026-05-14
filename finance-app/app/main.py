from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.init_db import init_db
from app.middleware.request_context import RequestContextMiddleware
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.categories import router as categories_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.notifications import router as notifications_router
from app.routes.uploads import router as uploads_router
from app.routes.transactions import router as transactions_router
from app.utils.logger import get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    if settings.AUTO_CREATE_TABLES:
        init_db()
    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(categories_router)
    app.include_router(transactions_router)
    app.include_router(dashboard_router)
    app.include_router(uploads_router)
    app.include_router(analytics_router)
    app.include_router(notifications_router)

    register_exception_handlers(app)

    return app


app = create_app()
