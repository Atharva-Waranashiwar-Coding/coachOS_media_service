import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260710_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


outbox_status = postgresql.ENUM(
    "pending",
    "processing",
    "published",
    "failed",
    name="outbox_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    enum_to_create = postgresql.ENUM(
        "pending",
        "processing",
        "published",
        "failed",
        name="outbox_status",
    )
    enum_to_create.create(bind, checkfirst=True)

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "destination",
            sa.String(length=100),
            nullable=False,
            server_default="athlete-timeline",
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            outbox_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_outbox_events_status_available_at",
        "outbox_events",
        ["status", "available_at"],
    )

    op.create_index(
        "ix_outbox_events_aggregate",
        "outbox_events",
        ["aggregate_type", "aggregate_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_aggregate",
        table_name="outbox_events",
    )
    op.drop_index(
        "ix_outbox_events_status_available_at",
        table_name="outbox_events",
    )
    op.drop_table("outbox_events")

    outbox_status.drop(op.get_bind(), checkfirst=True)