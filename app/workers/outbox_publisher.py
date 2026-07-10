import logging
import signal
import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.outbox_publisher import OutboxPublisher

running = True


def stop(*_: object) -> None:
    global running
    running = False


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    logger = logging.getLogger(__name__)
    while running:
        with SessionLocal() as db:
            publisher = OutboxPublisher(db)
            published = publisher.publish_batch()
            logger.info("outbox_cycle", extra={"published": published, **publisher.counts()})
        time.sleep(settings.outbox_poll_interval_seconds)


if __name__ == "__main__":
    main()
