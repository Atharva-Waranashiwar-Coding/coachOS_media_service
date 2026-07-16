from fastapi import APIRouter

from app.api.v1.endpoints.insights import router as insight_router
from app.api.v1.endpoints.media import router as media_router

api_router = APIRouter()
api_router.include_router(media_router)
api_router.include_router(insight_router)
