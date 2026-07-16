"""Efficient grouped practice-session and upload activity calculations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.enums import SessionStatus, UploadStatus
from app.models.media import PracticeSession, Video
from app.schemas.insights import (
    AthleteMediaActivity,
    MediaActivityBatchResponse,
    MediaActivityPeriod,
)


class ActivityInsightService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summarize(
        self,
        athlete_ids: list[UUID],
        coach_user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        comparison_start: datetime | None = None,
        comparison_end: datetime | None = None,
    ) -> MediaActivityBatchResponse:
        current = self._period(athlete_ids, coach_user_id, start_date, end_date)
        previous = (
            self._period(athlete_ids, coach_user_id, comparison_start, comparison_end)
            if comparison_start is not None and comparison_end is not None
            else {}
        )
        return MediaActivityBatchResponse(
            items=[
                AthleteMediaActivity(
                    athlete_id=athlete_id,
                    current=current.get(athlete_id, MediaActivityPeriod()),
                    previous=previous.get(athlete_id, MediaActivityPeriod()) if previous else None,
                )
                for athlete_id in athlete_ids
            ]
        )

    def _period(
        self,
        athlete_ids: list[UUID],
        coach_user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[UUID, MediaActivityPeriod]:
        session_rows = self.db.execute(
            select(
                PracticeSession.athlete_id,
                func.sum(
                    case(
                        (
                            (PracticeSession.created_at >= start_date) & (PracticeSession.created_at < end_date),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            (PracticeSession.status == SessionStatus.COMPLETED)
                            & (PracticeSession.completed_at >= start_date)
                            & (PracticeSession.completed_at < end_date),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.max(
                    case(
                        (
                            (PracticeSession.completed_at >= start_date) & (PracticeSession.completed_at < end_date),
                            PracticeSession.completed_at,
                        ),
                        (
                            (PracticeSession.created_at >= start_date) & (PracticeSession.created_at < end_date),
                            PracticeSession.created_at,
                        ),
                    )
                ),
            )
            .where(
                PracticeSession.athlete_id.in_(athlete_ids),
                PracticeSession.coach_user_id == coach_user_id,
            )
            .group_by(PracticeSession.athlete_id)
        ).all()
        video_rows = self.db.execute(
            select(Video.athlete_id, func.count(Video.id))
            .join(PracticeSession, PracticeSession.id == Video.practice_session_id)
            .where(
                Video.athlete_id.in_(athlete_ids),
                PracticeSession.coach_user_id == coach_user_id,
                Video.upload_status == UploadStatus.UPLOADED,
                Video.deleted_at.is_(None),
                Video.uploaded_at >= start_date,
                Video.uploaded_at < end_date,
            )
            .group_by(Video.athlete_id)
        ).all()
        video_counts = {athlete_id: int(count) for athlete_id, count in video_rows}
        result = {
            athlete_id: MediaActivityPeriod(
                sessions_created=int(created or 0),
                sessions_completed=int(completed or 0),
                videos_uploaded=video_counts.get(athlete_id, 0),
                latest_session_at=latest,
            )
            for athlete_id, created, completed, latest in session_rows
        }
        for athlete_id, count in video_counts.items():
            result.setdefault(athlete_id, MediaActivityPeriod()).videos_uploaded = count
        return result
