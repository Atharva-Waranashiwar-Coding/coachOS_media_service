"""Coach-authorized and internal media activity insight endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_bearer_token, require_coach
from app.dependencies.internal_auth import InternalServiceIdentity, require_insight_service
from app.integrations.athlete_service import AthleteServiceClient
from app.schemas.auth import CurrentUser
from app.schemas.insights import (
    AthleteMediaActivity,
    MediaActivityBatchRequest,
    MediaActivityBatchResponse,
)
from app.services.activity_insight_service import ActivityInsightService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/athletes/{athlete_id}/activity", response_model=AthleteMediaActivity)
def athlete_activity(
    athlete_id: UUID,
    start_date: datetime,
    end_date: datetime,
    comparison_start: datetime | None = None,
    comparison_end: datetime | None = None,
    user: CurrentUser = Depends(require_coach),
    bearer_token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> AthleteMediaActivity:
    AthleteServiceClient().verify_access(athlete_id, bearer_token)
    return (
        ActivityInsightService(db)
        .summarize(
            [athlete_id],
            user.id,
            start_date,
            end_date,
            comparison_start,
            comparison_end,
        )
        .items[0]
    )


@router.post("/athletes/activity-summary", response_model=MediaActivityBatchResponse)
def athlete_activity_batch(
    payload: MediaActivityBatchRequest,
    _: InternalServiceIdentity = Depends(require_insight_service),
    db: Session = Depends(get_db),
) -> MediaActivityBatchResponse:
    return ActivityInsightService(db).summarize(
        payload.athlete_ids,
        payload.coach_user_id,
        payload.start_date,
        payload.end_date,
        payload.comparison_start,
        payload.comparison_end,
    )
