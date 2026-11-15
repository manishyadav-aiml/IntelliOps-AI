"""anomaly detections, incidents, events, notes, log links, relationships

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _fk(column: str, target: str, table: str, ondelete: str | None = None) -> sa.ForeignKeyConstraint:
    ref_table = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=op.f(f"fk_{table}_{column}_{ref_table}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "anomaly_detections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("anomaly_detected", sa.Boolean(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("affected_service", sa.String(length=128), nullable=False),
        sa.Column("contributing_features", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("detection_timestamp", sa.DateTime(timezone=True), nullable=False),
        *_ts(),
        _fk("user_id", "users.id", "anomaly_detections", "CASCADE"),
        _fk("upload_id", "log_uploads.id", "anomaly_detections", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anomaly_detections")),
    )
    for col in ("user_id", "upload_id", "window_start", "anomaly_detected"):
        op.create_index(op.f(f"ix_anomaly_detections_{col}"), "anomaly_detections", [col])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("service", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("severity_reasons", sa.JSON(), nullable=False),
        sa.Column("services", sa.JSON(), nullable=False),
        sa.Column("templates", sa.JSON(), nullable=False),
        sa.Column("error_templates", sa.JSON(), nullable=False),
        sa.Column("anomaly_summary", sa.JSON(), nullable=True),
        sa.Column("detection_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_occurrence", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_occurrence", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.CheckConstraint("severity IN ('P1', 'P2', 'P3', 'P4')", name=op.f("ck_incidents_severity_valid")),
        sa.CheckConstraint(
            "status IN ('OPEN', 'INVESTIGATING', 'MITIGATED', 'RESOLVED')", name=op.f("ck_incidents_status_valid")
        ),
        _fk("user_id", "users.id", "incidents", "CASCADE"),
        _fk("upload_id", "log_uploads.id", "incidents", "SET NULL"),
        _fk("assigned_user_id", "users.id", "incidents", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("user_id", "fingerprint", name=op.f("uq_incidents_user_id")),
    )
    for col in ("user_id", "upload_id", "service", "severity", "status"):
        op.create_index(op.f(f"ix_incidents_{col}"), "incidents", [col])

    op.create_table(
        "incident_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        _fk("incident_id", "incidents.id", "incident_events", "CASCADE"),
        _fk("actor_user_id", "users.id", "incident_events", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_events")),
    )
    for col in ("incident_id", "event_type", "timestamp"):
        op.create_index(op.f(f"ix_incident_events_{col}"), "incident_events", [col])

    op.create_table(
        "incident_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        *_ts(),
        _fk("incident_id", "incidents.id", "incident_notes", "CASCADE"),
        _fk("author_id", "users.id", "incident_notes", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_notes")),
    )
    op.create_index(op.f("ix_incident_notes_incident_id"), "incident_notes", ["incident_id"])

    op.create_table(
        "incident_log_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("log_entry_id", sa.Integer(), nullable=False),
        _fk("incident_id", "incidents.id", "incident_log_links", "CASCADE"),
        _fk("log_entry_id", "log_entries.id", "incident_log_links", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_log_links")),
        sa.UniqueConstraint("incident_id", "log_entry_id", name=op.f("uq_incident_log_links_incident_id")),
    )
    op.create_index(op.f("ix_incident_log_links_incident_id"), "incident_log_links", ["incident_id"])

    op.create_table(
        "incident_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("related_incident_id", sa.Integer(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("shared", sa.JSON(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.id"], name=op.f("fk_incident_relationships_incident_id_incidents"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_incident_id"], ["incidents.id"],
            name=op.f("fk_incident_relationships_related_incident_id_incidents"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_relationships")),
        sa.UniqueConstraint("incident_id", "related_incident_id", name=op.f("uq_incident_relationships_incident_id")),
    )
    op.create_index(op.f("ix_incident_relationships_incident_id"), "incident_relationships", ["incident_id"])


def downgrade() -> None:
    for table in ("incident_relationships", "incident_log_links", "incident_notes", "incident_events", "incidents", "anomaly_detections"):
        op.drop_table(table)  # indexes are dropped with their tables
