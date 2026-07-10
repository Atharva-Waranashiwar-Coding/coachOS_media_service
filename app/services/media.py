import logging
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from app.integrations.athlete_service import AthleteServiceClient
from app.integrations.timeline_client import TimelineClient
from app.models.enums import ProcessingStatus, SessionStatus, UploadStatus
from app.models.media import PracticeSession, Video
from app.repositories.media import MediaRepository, SessionFilters, VideoFilters
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
from app.storage.base import StorageProvider
from app.utils.files import sanitize_filename

logger = logging.getLogger(__name__)


class PracticeSessionService:
    """Practice-session lifecycle and ownership use cases."""

    def __init__(self, db: Session, athletes: AthleteServiceClient) -> None:
        self.db, self.repo, self.athletes = db, MediaRepository(db), athletes

    def create(self, payload: PracticeSessionCreate, coach_id: UUID, token: str) -> PracticeSessionResponse:
        self.athletes.verify_access(payload.athlete_id, token)
        item = PracticeSession(**payload.model_dump(), coach_user_id=coach_id)
        try:
            self.repo.add_session(item)
            self.db.commit()
            self.db.refresh(item)
        except Exception:
            self.db.rollback()
            raise
        return PracticeSessionResponse.model_validate(item)

    def list(self, filters: SessionFilters, token: str) -> PracticeSessionListResponse:
        if filters.athlete_id:
            self.athletes.verify_access(filters.athlete_id, token)
        items, total = self.repo.list_sessions(filters)
        return PracticeSessionListResponse(
            items=items,
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=ceil(total / filters.page_size) if total else 0,
        )

    def get_model(self, item_id: UUID, coach_id: UUID, token: str) -> PracticeSession:
        item = self.repo.owned_session(item_id, coach_id)
        if not item:
            raise NotFoundError("Practice session not found.")
        self.athletes.verify_access(item.athlete_id, token)
        return item

    def get(self, item_id: UUID, coach_id: UUID, token: str) -> PracticeSessionResponse:
        return PracticeSessionResponse.model_validate(self.get_model(item_id, coach_id, token))

    def update(
        self, item_id: UUID, payload: PracticeSessionUpdate, coach_id: UUID, token: str
    ) -> PracticeSessionResponse:
        item = self.get_model(item_id, coach_id, token)
        if item.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise BadRequestError("Terminal sessions cannot be edited.")
        data = payload.model_dump(exclude_unset=True)
        if data.get("status") in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise BadRequestError("Use the complete or cancel action.")
        for key, value in data.items():
            setattr(item, key, value)
        try:
            self.db.commit()
            self.db.refresh(item)
        except Exception:
            self.db.rollback()
            raise
        return PracticeSessionResponse.model_validate(item)

    def transition(self, item_id: UUID, target: SessionStatus, coach_id: UUID, token: str) -> PracticeSessionResponse:
        item = self.get_model(item_id, coach_id, token)
        if item.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise BadRequestError("Terminal session status cannot be changed.")
        item.status = target
        item.completed_at = datetime.now(UTC) if target == SessionStatus.COMPLETED else None
        try:
            self.db.commit()
            self.db.refresh(item)
        except Exception:
            self.db.rollback()
            raise
        return PracticeSessionResponse.model_validate(item)


class VideoService:
    """Signed upload, storage verification, listing, and deletion use cases."""

    def __init__(
        self, db: Session, storage: StorageProvider, athletes: AthleteServiceClient, timeline: TimelineClient
    ) -> None:
        self.db, self.repo, self.storage, self.athletes, self.timeline = (
            db,
            MediaRepository(db),
            storage,
            athletes,
            timeline,
        )

    def request_upload(self, session: PracticeSession, payload: UploadUrlRequest) -> UploadUrlResponse:
        if session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise BadRequestError("Uploads are closed for this session.")
        content_type = payload.content_type.lower()
        if content_type not in settings.allowed_video_content_types:
            raise UnsupportedMediaTypeError()
        if payload.file_size_bytes > settings.max_video_size_bytes:
            raise PayloadTooLargeError()
        filename, video_id = sanitize_filename(payload.filename), uuid4()
        key = f"athletes/{session.athlete_id}/sessions/{session.id}/videos/{video_id}/{filename}"
        expires = datetime.now(UTC) + timedelta(seconds=settings.s3_presigned_url_expiration_seconds)
        video = Video(
            id=video_id,
            practice_session_id=session.id,
            athlete_id=session.athlete_id,
            uploaded_by_user_id=session.coach_user_id,
            original_filename=filename,
            storage_provider="s3",
            storage_bucket=settings.s3_bucket_name,
            storage_key=key,
            content_type=content_type,
            file_size_bytes=payload.file_size_bytes,
            upload_url_expires_at=expires,
            upload_status=UploadStatus.PENDING,
            processing_status=ProcessingStatus.NOT_STARTED,
        )
        try:
            self.repo.add_video(video)
            self.db.flush()
            url = self.storage.generate_upload_url(key, content_type, settings.s3_presigned_url_expiration_seconds)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return UploadUrlResponse(
            video_id=video_id,
            upload_url=url,
            storage_key=key,
            expires_at=expires,
            required_headers={"Content-Type": content_type},
        )

    def get_model(self, video_id: UUID, coach_id: UUID, token: str) -> Video:
        video = self.repo.owned_video(video_id, coach_id)
        if not video:
            raise NotFoundError("Video not found.")
        self.athletes.verify_access(video.athlete_id, token)
        return video

    def complete(self, video_id: UUID, payload: UploadCompletionRequest, coach_id: UUID, token: str) -> VideoResponse:
        video = self.get_model(video_id, coach_id, token)
        if video.upload_status == UploadStatus.DELETED:
            raise NotFoundError("Video not found.")
        if video.upload_status == UploadStatus.UPLOADED:
            return VideoResponse.model_validate(video)
        metadata = self.storage.head_object(video.storage_key)
        if not metadata.exists:
            expires_at = video.upload_url_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at and datetime.now(UTC) > expires_at:
                video.upload_status = UploadStatus.EXPIRED
                self.db.commit()
                raise ConflictError("Upload URL expired before an object was stored.")
            raise ConflictError("Uploaded object was not found.")
        if metadata.content_length is not None and metadata.content_length != video.file_size_bytes:
            video.upload_status, video.failure_reason = UploadStatus.FAILED, "Object size mismatch"
            self.db.commit()
            raise ConflictError("Uploaded object size does not match the request.")
        if not metadata.content_type or metadata.content_type.lower() not in settings.allowed_video_content_types:
            video.upload_status, video.failure_reason = UploadStatus.FAILED, "Unsupported stored content type"
            self.db.commit()
            raise UnsupportedMediaTypeError("Stored object has an unsupported content type.")
        video.upload_status, video.uploaded_at = UploadStatus.UPLOADED, datetime.now(UTC)
        video.etag, video.checksum, video.failure_reason = metadata.etag or payload.etag, payload.checksum, None
        try:
            self.db.commit()
            self.db.refresh(video)
        except Exception:
            self.db.rollback()
            raise
        try:
            self.timeline.publish_video_uploaded(
                athlete_id=video.athlete_id,
                video_id=video.id,
                session_id=video.practice_session_id,
                content_type=video.content_type,
                file_size_bytes=video.file_size_bytes,
                occurred_at=video.uploaded_at,
                session_title=video.practice_session.title,
            )
        except Exception:
            logger.exception(
                "timeline_publish_failed", extra={"video_id": str(video.id), "operation_outcome": "failure"}
            )
        return VideoResponse.model_validate(video)

    def get(self, video_id: UUID, coach_id: UUID, token: str) -> VideoResponse:
        return VideoResponse.model_validate(self.get_model(video_id, coach_id, token))

    def list(self, filters: VideoFilters) -> VideoListResponse:
        items, total = self.repo.list_videos(filters)
        return VideoListResponse(
            items=items,
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=ceil(total / filters.page_size) if total else 0,
        )

    def delete(self, video_id: UUID, coach_id: UUID, token: str) -> None:
        video = self.get_model(video_id, coach_id, token)
        if video.upload_status == UploadStatus.DELETED:
            return
        if settings.delete_storage_objects:
            self.storage.delete_object(video.storage_key)
        video.upload_status, video.deleted_at = UploadStatus.DELETED, datetime.now(UTC)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
