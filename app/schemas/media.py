from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProcessingStatus, SessionStatus, SessionType, UploadStatus
from app.schemas.common import PaginatedResponse


class PracticeSessionCreate(BaseModel):
    athlete_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    session_date: datetime
    location: str | None = Field(default=None, max_length=200)
    session_type: SessionType

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("title cannot be blank")
        return value

    @field_validator("session_date")
    @classmethod
    def normalize_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("session_date must include a timezone")
        return value.astimezone(UTC)


class PracticeSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    session_date: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    session_type: SessionType | None = None
    status: SessionStatus | None = None

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is not None and not (value := value.strip()):
            raise ValueError("title cannot be blank")
        return value

    @field_validator("session_date")
    @classmethod
    def normalize_date(cls, value: datetime | None) -> datetime | None:
        if value and value.tzinfo is None:
            raise ValueError("session_date must include a timezone")
        return value.astimezone(UTC) if value else None


class PracticeSessionResponse(BaseModel):
    id: UUID
    athlete_id: UUID
    coach_user_id: UUID
    title: str
    description: str | None
    session_date: datetime
    location: str | None
    session_type: SessionType
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class PracticeSessionListResponse(PaginatedResponse[PracticeSessionResponse]):
    pass


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    file_size_bytes: int = Field(gt=0)


class UploadUrlResponse(BaseModel):
    video_id: UUID
    upload_url: str
    storage_key: str
    expires_at: datetime
    required_headers: dict[str, str]


class UploadCompletionRequest(BaseModel):
    etag: str | None = Field(default=None, max_length=255)
    checksum: str | None = Field(default=None, max_length=255)


class VideoSummary(BaseModel):
    id: UUID
    practice_session_id: UUID
    athlete_id: UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    duration_seconds: Decimal | None
    width: int | None
    height: int | None
    upload_status: UploadStatus
    processing_status: ProcessingStatus
    created_at: datetime
    uploaded_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class VideoResponse(VideoSummary):
    uploaded_by_user_id: UUID
    storage_provider: str
    checksum: str | None
    etag: str | None
    frame_rate: Decimal | None
    failure_reason: str | None
    upload_url_expires_at: datetime | None
    updated_at: datetime
    deleted_at: datetime | None


class VideoListResponse(PaginatedResponse[VideoSummary]):
    pass
