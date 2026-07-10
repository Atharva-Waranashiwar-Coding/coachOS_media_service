"""create media domain

Revision ID: 20260710_0001
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None
session_type = postgresql.ENUM(
    "practice",
    "game",
    "bullpen",
    "batting",
    "fielding",
    "strength",
    "assessment",
    "other",
    name="session_type",
    create_type=False,
)
session_status = postgresql.ENUM("draft", "active", "completed", "cancelled", name="session_status", create_type=False)
upload_status = postgresql.ENUM(
    "pending", "uploading", "uploaded", "failed", "expired", "deleted", name="upload_status", create_type=False
)
processing_status = postgresql.ENUM(
    "not_started", "queued", "processing", "completed", "failed", name="processing_status", create_type=False
)


def upgrade():
    bind = op.get_bind()
    for enum in (session_type, session_status, upload_status, processing_status):
        enum.create(bind, checkfirst=True)
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("coach_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(200)),
        sa.Column("session_type", session_type, nullable=False),
        sa.Column("status", session_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    for col in ("athlete_id", "coach_user_id", "session_date", "status"):
        op.create_index(f"ix_practice_sessions_{col}", "practice_sessions", [col])
    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "practice_session_id", sa.Uuid(), sa.ForeignKey("practice_sessions.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_provider", sa.String(50), nullable=False),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(12, 3)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("frame_rate", sa.Numeric(8, 3)),
        sa.Column("checksum", sa.String(255)),
        sa.Column("etag", sa.String(255)),
        sa.Column("upload_status", upload_status, nullable=False, server_default="pending"),
        sa.Column("processing_status", processing_status, nullable=False, server_default="not_started"),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("upload_url_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("storage_key", name="uq_videos_storage_key"),
    )
    for col in ("practice_session_id", "athlete_id", "upload_status", "processing_status", "created_at"):
        op.create_index(f"ix_videos_{col}", "videos", [col])


def downgrade():
    op.drop_table("videos")
    op.drop_table("practice_sessions")
    bind = op.get_bind()
    for enum in (processing_status, upload_status, session_status, session_type):
        enum.drop(bind, checkfirst=True)
