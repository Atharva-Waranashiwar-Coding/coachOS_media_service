"""Storage-free practice and upload activity insight contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.config import settings


class MediaActivityPeriod(BaseModel):
    sessions_created: int = 0
    sessions_completed: int = 0
    videos_uploaded: int = 0
    latest_session_at: datetime | None = None


class AthleteMediaActivity(BaseModel):
    athlete_id: UUID
    current: MediaActivityPeriod
    previous: MediaActivityPeriod | None = None


class MediaActivityBatchRequest(BaseModel):
    athlete_ids: list[UUID] = Field(min_length=1)
    coach_user_id: UUID
    start_date: datetime
    end_date: datetime
    comparison_start: datetime | None = None
    comparison_end: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> "MediaActivityBatchRequest":
        if len(set(self.athlete_ids)) != len(self.athlete_ids):
            raise ValueError("athlete_ids must not contain duplicates")
        if len(self.athlete_ids) > settings.insight_max_batch_athletes:
            raise ValueError("athlete_ids exceeds the configured batch limit")
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if (self.comparison_start is None) != (self.comparison_end is None):
            raise ValueError("comparison_start and comparison_end must be provided together")
        if self.comparison_start and self.comparison_end and self.comparison_start >= self.comparison_end:
            raise ValueError("comparison_start must be before comparison_end")
        return self


class MediaActivityBatchResponse(BaseModel):
    items: list[AthleteMediaActivity]
