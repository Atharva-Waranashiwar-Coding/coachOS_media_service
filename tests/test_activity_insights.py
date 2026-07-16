"""Media activity aggregation tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.enums import SessionStatus, SessionType, UploadStatus
from app.models.media import PracticeSession, Video
from app.services.activity_insight_service import ActivityInsightService


def test_activity_summary_counts_current_and_previous_without_storage_fields(db):
    athlete_id, coach_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    current_session = PracticeSession(
        athlete_id=athlete_id,
        coach_user_id=coach_id,
        title="Current",
        session_date=now,
        session_type=SessionType.PRACTICE,
        status=SessionStatus.COMPLETED,
        created_at=now - timedelta(days=2),
        completed_at=now - timedelta(days=1),
    )
    previous_session = PracticeSession(
        athlete_id=athlete_id,
        coach_user_id=coach_id,
        title="Previous",
        session_date=now - timedelta(days=40),
        session_type=SessionType.PRACTICE,
        status=SessionStatus.COMPLETED,
        created_at=now - timedelta(days=40),
        completed_at=now - timedelta(days=35),
    )
    db.add_all([current_session, previous_session])
    db.flush()
    db.add_all(
        [
            Video(
                practice_session_id=current_session.id,
                athlete_id=athlete_id,
                uploaded_by_user_id=coach_id,
                original_filename="current.mp4",
                storage_provider="s3",
                storage_bucket="private",
                storage_key="secret/current",
                content_type="video/mp4",
                file_size_bytes=100,
                upload_status=UploadStatus.UPLOADED,
                uploaded_at=now - timedelta(hours=12),
            ),
            Video(
                practice_session_id=previous_session.id,
                athlete_id=athlete_id,
                uploaded_by_user_id=coach_id,
                original_filename="deleted.mp4",
                storage_provider="s3",
                storage_bucket="private",
                storage_key="secret/deleted",
                content_type="video/mp4",
                file_size_bytes=100,
                upload_status=UploadStatus.DELETED,
                uploaded_at=now - timedelta(days=35),
                deleted_at=now - timedelta(days=34),
            ),
        ]
    )
    db.commit()

    result = (
        ActivityInsightService(db)
        .summarize(
            [athlete_id],
            coach_id,
            now - timedelta(days=30),
            now,
            now - timedelta(days=60),
            now - timedelta(days=30),
        )
        .items[0]
    )

    assert result.current.sessions_created == 1
    assert result.current.sessions_completed == 1
    assert result.current.videos_uploaded == 1
    assert result.previous is not None
    assert result.previous.sessions_completed == 1
    assert result.previous.videos_uploaded == 0
    assert "storage" not in str(result.model_dump())
