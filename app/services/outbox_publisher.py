import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import OutboxStatus
from app.models.outbox import OutboxEvent

logger = logging.getLogger(__name__)


class OutboxPublisher:
    """Claim and deliver timeline outbox rows with bounded retries."""

    def __init__(self, db: Session, client: httpx.Client | None = None) -> None:
        self.db, self.client = db, client or httpx.Client(timeout=settings.upstream_timeout_seconds)

    def claim(self) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(
                or_(OutboxEvent.status == OutboxStatus.PENDING, OutboxEvent.status == OutboxStatus.PROCESSING),
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.created_at)
            .limit(settings.outbox_batch_size)
            .with_for_update(skip_locked=True)
        )
        events = list(self.db.scalars(stmt))
        for event in events:
            event.status = OutboxStatus.PROCESSING
            event.available_at = now + timedelta(seconds=max(settings.outbox_poll_interval_seconds * 5, 30))
        self.db.commit()
        return events

    def publish_batch(self) -> int:
        published = 0
        for event in self.claim():
            athlete_id = event.payload["athlete_id"]
            try:
                response = self.client.post(
                    f"{settings.athlete_service_internal_url.rstrip('/')}/internal/v1/athletes/{athlete_id}/timeline-events",
                    json=event.payload,
                    headers={
                        "X-Service-Name": settings.internal_service_name,
                        "X-Service-Token": settings.internal_service_token or "",
                        "X-Request-ID": str(event.id),
                    },
                )
                if response.status_code in {200, 201}:
                    event.status, event.published_at, event.last_error = OutboxStatus.PUBLISHED, datetime.now(UTC), None
                    published += 1
                elif response.status_code in {400, 401, 403, 409, 422}:
                    self._fail(event, f"permanent HTTP {response.status_code}", permanent=True)
                else:
                    self._fail(event, f"retryable HTTP {response.status_code}")
            except httpx.HTTPError as exc:
                self._fail(event, type(exc).__name__)
            self.db.commit()
        return published

    def _fail(self, event: OutboxEvent, message: str, permanent: bool = False) -> None:
        event.attempt_count += 1
        event.last_error = message[:500]
        exhausted = permanent or event.attempt_count >= settings.outbox_max_attempts
        event.status = OutboxStatus.FAILED if exhausted else OutboxStatus.PENDING
        event.available_at = datetime.now(UTC) + timedelta(
            seconds=min(settings.outbox_base_retry_seconds * (2 ** max(event.attempt_count - 1, 0)), 3600)
        )

    def counts(self) -> dict[str, int]:
        rows = self.db.execute(select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)).all()
        return {status.value: count for status, count in rows}
