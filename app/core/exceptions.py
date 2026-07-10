import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code, code, message = 400, "bad_request", "Invalid request."


class UnauthorizedError(AppError):
    status_code, code, message = 401, "unauthorized", "Authentication is required."


class ForbiddenError(AppError):
    status_code, code, message = 403, "forbidden", "Permission denied."


class NotFoundError(AppError):
    status_code, code, message = 404, "not_found", "Resource not found."


class ConflictError(AppError):
    status_code, code, message = 409, "conflict", "Resource conflict."


class PayloadTooLargeError(AppError):
    status_code, code, message = 413, "payload_too_large", "File exceeds the configured size limit."


class UnsupportedMediaTypeError(AppError):
    status_code, code, message = 415, "unsupported_media_type", "Unsupported media type."


class UpstreamServiceError(AppError):
    status_code, code, message = 503, "upstream_unavailable", "A required service is unavailable."


class StorageServiceError(AppError):
    status_code, code, message = 503, "storage_unavailable", "Storage is unavailable."


def response(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message, "details": details or {}}}
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def known(_: Request, exc: AppError) -> JSONResponse:
        return response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": item.get("loc", []),
                "msg": item.get("msg", "Invalid value."),
                "type": item.get("type", "value_error"),
            }
            for item in exc.errors()
        ]
        return response(422, "validation_error", "One or more fields are invalid.", {"errors": errors})

    @app.exception_handler(IntegrityError)
    async def integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("database_integrity_error", extra={"operation_outcome": "conflict"})
        return response(409, "conflict", "Resource conflict.")

    @app.exception_handler(SQLAlchemyError)
    async def database(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("database_error", exc_info=exc)
        return response(500, "database_error", "A database error occurred.")

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", exc_info=exc)
        return response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred.")
