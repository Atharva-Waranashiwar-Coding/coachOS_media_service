from datetime import datetime
from uuid import UUID, uuid4

from app.models.outbox import OutboxEvent


def timeline_outbox(
    *,
    athlete_id: UUID,
    event_type: str,
    category: str,
    title: str,
    aggregate_type: str,
    aggregate_id: UUID,
    actor_user_id: UUID | None,
    occurred_at: datetime,
    visibility: str = "athlete_visible",
    description: str | None = None,
    metadata: dict[str, object] | None = None,
) -> OutboxEvent:
    event_id = uuid4()
    payload = {
        "event_id": str(event_id),
        "athlete_id": str(athlete_id),
        "event_type": event_type,
        "event_category": category,
        "title": title,
        "description": description,
        "source_service": "media-service",
        "source_entity_type": aggregate_type,
        "source_entity_id": str(aggregate_id),
        "actor_user_id": str(actor_user_id) if actor_user_id else None,
        "occurred_at": occurred_at.isoformat(),
        "metadata": metadata or {},
        "schema_version": 1,
        "visibility": visibility,
    }
    return OutboxEvent(
        aggregate_type=aggregate_type, aggregate_id=str(aggregate_id), event_type=event_type, payload=payload
    )
