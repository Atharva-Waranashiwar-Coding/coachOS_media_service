import logging
from datetime import datetime
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TimelineClient:
    """Best-effort publisher for Athlete Service timeline events."""

    def publish_video_uploaded(
        self,
        *,
        athlete_id: UUID,
        video_id: UUID,
        session_id: UUID,
        content_type: str,
        file_size_bytes: int,
        occurred_at: datetime,
        session_title: str,
    ) -> None:
        if not settings.timeline_publishing_enabled:
            return
        if not settings.athlete_service_internal_url or not settings.internal_service_token:
            logger.warning("timeline_not_configured", extra={"video_id": str(video_id), "operation_outcome": "skipped"})
            return
        payload = {
            "event_type": "video_uploaded",
            "title": "Practice video uploaded",
            "description": f"Video uploaded for {session_title}",
            "source_service": "media-service",
            "source_entity_type": "video",
            "source_entity_id": str(video_id),
            "occurred_at": occurred_at.isoformat(),
            "metadata": {
                "practice_session_id": str(session_id),
                "content_type": content_type,
                "file_size_bytes": file_size_bytes,
            },
        }
        try:
            response = httpx.post(
                f"{settings.athlete_service_internal_url.rstrip('/')}/internal/api/v1/athletes/{athlete_id}/timeline-events",
                json=payload,
                headers={"Authorization": f"Bearer {settings.internal_service_token}"},
                timeout=settings.upstream_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception(
                "timeline_publish_failed",
                extra={
                    "video_id": str(video_id),
                    "practice_session_id": str(session_id),
                    "operation_outcome": "failure",
                },
            )
