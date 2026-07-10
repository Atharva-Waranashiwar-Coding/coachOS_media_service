from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.athlete_service import AthleteServiceClient
from app.integrations.timeline_client import TimelineClient
from app.services.media import PracticeSessionService, VideoService
from app.storage.base import StorageProvider
from app.storage.s3 import S3StorageProvider


def get_athlete_client() -> AthleteServiceClient:
    return AthleteServiceClient()


def get_storage() -> StorageProvider:
    return S3StorageProvider()


def get_timeline_client() -> TimelineClient:
    return TimelineClient()


def get_session_service(
    db: Session = Depends(get_db), athletes: AthleteServiceClient = Depends(get_athlete_client)
) -> PracticeSessionService:
    return PracticeSessionService(db, athletes)


def get_video_service(
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage),
    athletes: AthleteServiceClient = Depends(get_athlete_client),
    timeline: TimelineClient = Depends(get_timeline_client),
) -> VideoService:
    return VideoService(db, storage, athletes, timeline)
