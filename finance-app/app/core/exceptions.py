from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logger import get_logger

logger = get_logger("app.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.warning("HTTP error", extra={"path": request.url.path, "status_code": exc.status_code})
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error"},
        )
