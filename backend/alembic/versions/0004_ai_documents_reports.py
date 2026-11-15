"""ai_investigations, documents, document_chunks, reports

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _fk(column: str, target: str, table: str, ondelete: str | None = None) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [target], name=op.f(f"fk_{table}_{column}_{target.split('.')[0]}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "ai_investigations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_ts(),
        _fk("incident_id", "incidents.id", "ai_investigations", "CASCADE"),
        _fk("user_id", "users.id", "ai_investigations", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_investigations")),
    )
    op.create_index(op.f("ix_ai_investigations_incident_id"), "ai_investigations", ["incident_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("extension", sa.String(length=10), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("embedder_name", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')", name=op.f("ck_documents_status_valid")
        ),
        _fk("user_id", "users.id", "documents", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.String(length=16), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        _fk("document_id", "documents.id", "document_chunks", "CASCADE"),
        _fk("user_id", "users.id", "document_chunks", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("document_id", "chunk_id", name=op.f("uq_document_chunks_document_id")),
    )
    op.create_index(op.f("ix_document_chunks_user_id"), "document_chunks", ["user_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        *_ts(),
        sa.CheckConstraint("format IN ('pdf', 'csv', 'json')", name=op.f("ck_reports_format_valid")),
        _fk("user_id", "users.id", "reports", "CASCADE"),
        _fk("incident_id", "incidents.id", "reports", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )
    op.create_index(op.f("ix_reports_user_id"), "reports", ["user_id"])
    op.create_index(op.f("ix_reports_incident_id"), "reports", ["incident_id"])


def downgrade() -> None:
    for table in ("reports", "document_chunks", "documents", "ai_investigations"):
        op.drop_table(table)
