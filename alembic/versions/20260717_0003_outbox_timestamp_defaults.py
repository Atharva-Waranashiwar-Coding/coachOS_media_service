"""Add database defaults for outbox timestamps.

Revision ID: 20260717_0003
Revises: 20260710_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260717_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "outbox_events",
        "created_at",
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "outbox_events",
        "updated_at",
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column("outbox_events", "updated_at", server_default=None)
    op.alter_column("outbox_events", "created_at", server_default=None)
