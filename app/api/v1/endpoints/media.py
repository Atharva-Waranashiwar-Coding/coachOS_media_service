from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.core.config import settings
from app.dependencies.auth import get_bearer_token, require_coach
from app.dependencies.services import get_athlete_client, get_session_service, get_video_service
from app.integrations.athlete_service import AthleteServiceClient
from app.models.enums import ProcessingStatus, SessionStatus, SessionType, UploadStatus
from app.repositories.media import SessionFilters, VideoFilters
from app.schemas.auth import CurrentUser
from app.schemas.media import (
    PracticeSessionCreate,
    PracticeSessionListResponse,
    PracticeSessionResponse,
    PracticeSessionUpdate,
    UploadCompletionRequest,
    UploadUrlRequest,
    UploadUrlResponse,
    VideoListResponse,
    VideoResponse,
)
from app.services.media import PracticeSessionService, VideoService

router = APIRouter()


@router.post("/practice-sessions", response_model=PracticeSessionResponse, status_code=201)
def create_session(
    payload: PracticeSessionCreate,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
) -> PracticeSessionResponse:
    return service.create(payload, user.id, token)


@router.get("/practice-sessions", response_model=PracticeSessionListResponse)
def list_sessions(
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
    athlete_id: UUID | None = None,
    status_filter: SessionStatus | None = Query(default=None, alias="status"),
    session_type: SessionType | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> PracticeSessionListResponse:
    return service.list(
        SessionFilters(
            user.id, page, page_size, athlete_id, status_filter, session_type, start_date, end_date, sort_order
        ),
        token,
    )


@router.get("/practice-sessions/{session_id}", response_model=PracticeSessionResponse)
def get_session(
    session_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
) -> PracticeSessionResponse:
    return service.get(session_id, user.id, token)


@router.patch("/practice-sessions/{session_id}", response_model=PracticeSessionResponse)
def update_session(
    session_id: UUID,
    payload: PracticeSessionUpdate,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
) -> PracticeSessionResponse:
    return service.update(session_id, payload, user.id, token)


@router.post("/practice-sessions/{session_id}/complete", response_model=PracticeSessionResponse)
def complete_session(
    session_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
) -> PracticeSessionResponse:
    return service.transition(session_id, SessionStatus.COMPLETED, user.id, token)


@router.post("/practice-sessions/{session_id}/cancel", response_model=PracticeSessionResponse)
def cancel_session(
    session_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: PracticeSessionService = Depends(get_session_service),
) -> PracticeSessionResponse:
    return service.transition(session_id, SessionStatus.CANCELLED, user.id, token)


@router.post("/practice-sessions/{session_id}/videos/upload-url", response_model=UploadUrlResponse, status_code=201)
def upload_url(
    session_id: UUID,
    payload: UploadUrlRequest,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    sessions: PracticeSessionService = Depends(get_session_service),
    videos: VideoService = Depends(get_video_service),
) -> UploadUrlResponse:
    return videos.request_upload(sessions.get_model(session_id, user.id, token), payload)


@router.post("/videos/{video_id}/complete-upload", response_model=VideoResponse)
def complete_upload(
    video_id: UUID,
    payload: UploadCompletionRequest,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: VideoService = Depends(get_video_service),
) -> VideoResponse:
    return service.complete(video_id, payload, user.id, token)


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: VideoService = Depends(get_video_service),
) -> VideoResponse:
    return service.get(video_id, user.id, token)


@router.delete("/videos/{video_id}", status_code=204)
def delete_video(
    video_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: VideoService = Depends(get_video_service),
) -> Response:
    service.delete(video_id, user.id, token)
    return Response(status_code=204)


@router.get("/athletes/{athlete_id}/videos", response_model=VideoListResponse)
def athlete_videos(
    athlete_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    service: VideoService = Depends(get_video_service),
    athletes: AthleteServiceClient = Depends(get_athlete_client),
    practice_session_id: UUID | None = None,
    upload_status: UploadStatus | None = None,
    processing_status: ProcessingStatus | None = None,
    content_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
) -> VideoListResponse:
    athletes.verify_access(athlete_id, token)
    return service.list(
        VideoFilters(
            user.id,
            page,
            page_size,
            athlete_id,
            practice_session_id,
            upload_status,
            processing_status,
            content_type,
            start_date,
            end_date,
        )
    )


@router.get("/practice-sessions/{session_id}/videos", response_model=VideoListResponse)
def session_videos(
    session_id: UUID,
    user: CurrentUser = Depends(require_coach),
    token: str = Depends(get_bearer_token),
    sessions: PracticeSessionService = Depends(get_session_service),
    videos: VideoService = Depends(get_video_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
) -> VideoListResponse:
    sessions.get_model(session_id, user.id, token)
    return videos.list(VideoFilters(user.id, page, page_size, session_id=session_id))
