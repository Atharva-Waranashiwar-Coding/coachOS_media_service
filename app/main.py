from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.observability import register_observability
from app.db.session import SessionLocal
from app.storage.s3 import S3StorageProvider

configure_logging()
app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/docs", openapi_url="/openapi.json")
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
register_observability(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable.") from exc
    if not S3StorageProvider().bucket_accessible():
        raise HTTPException(status_code=503, detail="Storage is unavailable.")
    return {"status": "ready", "database": "ok", "storage": "ok"}
