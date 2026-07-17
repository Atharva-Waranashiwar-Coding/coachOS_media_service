import os

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select, text, update

from app.models.enums import OutboxStatus
from app.models.outbox import OutboxEvent


def _postgres_engine():
    url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is required for PostgreSQL enum integration tests")
    return create_engine(url)


def test_outbox_statuses_round_trip_as_lowercase_postgres_values():
    engine = _postgres_engine()
    metadata = MetaData()
    outbox = Table(
        "test_media_outbox_enum_mapping",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("status", OutboxEvent.__table__.c.status.type, nullable=False),
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TEMP TABLE test_media_outbox_enum_mapping "
                "(id integer PRIMARY KEY, status outbox_status NOT NULL)"
            )
        )
        connection.execute(outbox.insert().values(id=1, status=OutboxStatus.PENDING))
        assert (
            connection.scalar(select(outbox.c.status).where(outbox.c.status == OutboxStatus.PENDING))
            is OutboxStatus.PENDING
        )
        assert (
            connection.scalar(text("SELECT status::text FROM test_media_outbox_enum_mapping WHERE id = 1")) == "pending"
        )
        connection.execute(update(outbox).where(outbox.c.id == 1).values(status=OutboxStatus.PROCESSING))
        assert (
            connection.scalar(text("SELECT status::text FROM test_media_outbox_enum_mapping WHERE id = 1"))
            == "processing"
        )

    engine.dispose()
