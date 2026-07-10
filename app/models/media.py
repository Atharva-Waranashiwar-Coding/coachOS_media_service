from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import ProcessingStatus, SessionStatus, SessionType, UploadStatus


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (
        Index("ix_practice_sessions_athlete_id", "athlete_id"),
        Index("ix_practice_sessions_coach_user_id", "coach_user_id"),
        Index("ix_practice_sessions_session_date", "session_date"),
        Index("ix_practice_sessions_status", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    athlete_id: Mapped[UUID]
    coach_user_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    session_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(200))
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType, name="session_type"))
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    videos: Mapped[list["Video"]] = relationship(back_populates="practice_session")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_videos_storage_key"),
        Index("ix_videos_practice_session_id", "practice_session_id"),
        Index("ix_videos_athlete_id", "athlete_id"),
        Index("ix_videos_upload_status", "upload_status"),
        Index("ix_videos_processing_status", "processing_status"),
        Index("ix_videos_created_at", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    practice_session_id: Mapped[UUID] = mapped_column(ForeignKey("practice_sessions.id", ondelete="RESTRICT"))
    athlete_id: Mapped[UUID]
    uploaded_by_user_id: Mapped[UUID]
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_provider: Mapped[str] = mapped_column(String(50))
    storage_bucket: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    checksum: Mapped[str | None] = mapped_column(String(255))
    etag: Mapped[str | None] = mapped_column(String(255))
    upload_status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status"), default=UploadStatus.PENDING
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"), default=ProcessingStatus.NOT_STARTED
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    upload_url_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    practice_session: Mapped[PracticeSession] = relationship(back_populates="videos")
