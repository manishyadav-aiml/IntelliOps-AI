"""log management: log_uploads, log_templates, log_entries

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "log_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("extension", sa.String(length=8), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("total_lines", sa.Integer(), nullable=False),
        sa.Column("processed_lines", sa.Integer(), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parse_stats", sa.JSON(), nullable=True),
        sa.Column("parser_used", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_log_uploads_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_log_uploads_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_log_uploads")),
    )
    op.create_index(op.f("ix_log_uploads_user_id"), "log_uploads", ["user_id"])
    op.create_index(op.f("ix_log_uploads_status"), "log_uploads", ["status"])

    op.create_table(
        "log_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_hash", sa.String(length=16), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_log_templates_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_log_templates")),
        sa.UniqueConstraint("user_id", "template_hash", name=op.f("uq_log_templates_user_id")),
    )

    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("service", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("original_message", sa.Text(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["upload_id"], ["log_uploads.id"], name=op.f("fk_log_entries_upload_id_log_uploads"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_log_entries_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["log_templates.id"], name=op.f("fk_log_entries_template_id_log_templates"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_log_entries")),
        sa.UniqueConstraint("upload_id", "line_number", name=op.f("uq_log_entries_upload_id")),
    )
    op.create_index(op.f("ix_log_entries_user_id"), "log_entries", ["user_id"])
    op.create_index(op.f("ix_log_entries_timestamp"), "log_entries", ["timestamp"])
    op.create_index(op.f("ix_log_entries_level"), "log_entries", ["level"])
    op.create_index(op.f("ix_log_entries_service"), "log_entries", ["service"])
    op.create_index(op.f("ix_log_entries_template_id"), "log_entries", ["template_id"])


def downgrade() -> None:
    for name in ("template_id", "service", "level", "timestamp", "user_id"):
        op.drop_index(op.f(f"ix_log_entries_{name}"), table_name="log_entries")
    op.drop_table("log_entries")
    op.drop_table("log_templates")
    op.drop_index(op.f("ix_log_uploads_status"), table_name="log_uploads")
    op.drop_index(op.f("ix_log_uploads_user_id"), table_name="log_uploads")
    op.drop_table("log_uploads")
