import argparse
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import OutboxStatus
from app.models.outbox import OutboxEvent
from app.services.outbox_publisher import OutboxPublisher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "retry-failed"])
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.action == "inspect":
            print(OutboxPublisher(db).counts())
            return
        events = list(db.scalars(select(OutboxEvent).where(OutboxEvent.status == OutboxStatus.FAILED)))
        for event in events:
            event.status = OutboxStatus.PENDING
            event.available_at = datetime.now(UTC)
            event.last_error = None
        db.commit()
        print({"retried": len(events)})


if __name__ == "__main__":
    main()
