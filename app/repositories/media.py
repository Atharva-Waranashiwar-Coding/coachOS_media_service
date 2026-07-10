from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import ProcessingStatus, SessionStatus, SessionType, UploadStatus
from app.models.media import PracticeSession, Video


@dataclass
class SessionFilters:
    coach_id: UUID
    page: int
    page_size: int
    athlete_id: UUID | None = None
    status: SessionStatus | None = None
    session_type: SessionType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    sort_order: str = "desc"


@dataclass
class VideoFilters:
    coach_id: UUID
    page: int
    page_size: int
    athlete_id: UUID | None = None
    session_id: UUID | None = None
    upload_status: UploadStatus | None = None
    processing_status: ProcessingStatus | None = None
    content_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class MediaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_session(self, item: PracticeSession) -> PracticeSession:
        self.db.add(item)
        return item

    def owned_session(self, item_id: UUID, coach_id: UUID) -> PracticeSession | None:
        return self.db.scalar(
            select(PracticeSession).where(PracticeSession.id == item_id, PracticeSession.coach_user_id == coach_id)
        )

    def list_sessions(self, f: SessionFilters) -> tuple[list[PracticeSession], int]:
        stmt = select(PracticeSession).where(PracticeSession.coach_user_id == f.coach_id)
        if f.athlete_id:
            stmt = stmt.where(PracticeSession.athlete_id == f.athlete_id)
        if f.status:
            stmt = stmt.where(PracticeSession.status == f.status)
        if f.session_type:
            stmt = stmt.where(PracticeSession.session_type == f.session_type)
        if f.start_date:
            stmt = stmt.where(PracticeSession.session_date >= f.start_date)
        if f.end_date:
            stmt = stmt.where(PracticeSession.session_date <= f.end_date)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        order = PracticeSession.session_date.asc() if f.sort_order == "asc" else PracticeSession.session_date.desc()
        return list(self.db.scalars(stmt.order_by(order).offset((f.page - 1) * f.page_size).limit(f.page_size))), total

    def add_video(self, item: Video) -> Video:
        self.db.add(item)
        return item

    def owned_video(self, item_id: UUID, coach_id: UUID) -> Video | None:
        return self.db.scalar(
            select(Video)
            .options(joinedload(Video.practice_session))
            .join(PracticeSession)
            .where(Video.id == item_id, PracticeSession.coach_user_id == coach_id)
        )

    def list_videos(self, f: VideoFilters) -> tuple[list[Video], int]:
        stmt = (
            select(Video)
            .join(PracticeSession)
            .where(PracticeSession.coach_user_id == f.coach_id, Video.upload_status != UploadStatus.DELETED)
        )
        if f.athlete_id:
            stmt = stmt.where(Video.athlete_id == f.athlete_id)
        if f.session_id:
            stmt = stmt.where(Video.practice_session_id == f.session_id)
        if f.upload_status:
            stmt = stmt.where(Video.upload_status == f.upload_status)
        if f.processing_status:
            stmt = stmt.where(Video.processing_status == f.processing_status)
        if f.content_type:
            stmt = stmt.where(Video.content_type == f.content_type)
        if f.start_date:
            stmt = stmt.where(Video.created_at >= f.start_date)
        if f.end_date:
            stmt = stmt.where(Video.created_at <= f.end_date)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        return (
            list(
                self.db.scalars(
                    stmt.order_by(Video.created_at.desc()).offset((f.page - 1) * f.page_size).limit(f.page_size)
                )
            ),
            total,
        )
