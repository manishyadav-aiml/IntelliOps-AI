from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["P1", "P2", "P3", "P4"]
Status = Literal["OPEN", "INVESTIGATING", "MITIGATED", "RESOLVED"]
SCORE_NOTE = "anomaly_score is model-specific and is not a probability."


class AnomalyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_id: int
    window_start: datetime
    window_end: datetime
    anomaly_detected: bool
    anomaly_score: float
    threshold: float
    method: str
    model_version: str
    affected_service: str
    contributing_features: list[Any]
    features: dict[str, Any]
    detection_timestamp: datetime
    note: str = SCORE_NOTE


class AnalysisResult(BaseModel):
    upload_id: int
    method: str
    window_seconds: int
    windows_analyzed: int
    anomalous_windows: int
    entries_without_timestamp: int
    incidents_created: int
    incidents_updated: int
    incident_ids: list[int]
    note: str = SCORE_NOTE


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    service: str = Field(default="unknown", min_length=1, max_length=128)
    severity: Severity = "P3"
    upload_id: int | None = None
    first_occurrence: datetime | None = None
    last_occurrence: datetime | None = None

    @field_validator("title", "service")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class IncidentUpdate(BaseModel):
    """Only fields present in the request are changed (assigned_user_id may be set to null to unassign)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    severity: Severity | None = None
    status: Status | None = None
    assigned_user_id: int | None = None
    resolution_notes: str | None = Field(default=None, max_length=10000)


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int | None
    author_name: str | None = None
    content: str
    created_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    timestamp: datetime
    description: str
    actor_user_id: int | None
    details: dict[str, Any] | None


class SimilarRead(BaseModel):
    incident_id: str
    similar_incident_id: str
    similar_incident_pk: int | None = None
    title: str | None = None
    similarity_score: float
    shared_services: list[str]
    shared_templates: list[str]
    shared_error_patterns: list[str]
    note: str


class InvestigateRequest(BaseModel):
    question: str | None = Field(default=None, max_length=500)


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    question: str
    status: str
    provider: str
    result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class IncidentRead(BaseModel):
    id: int
    public_id: str
    title: str
    description: str
    service: str
    severity: Severity
    severity_label: str
    severity_reasons: list[str]
    status: Status
    services: list[str]
    upload_id: int | None
    detection_time: datetime
    first_occurrence: datetime | None
    last_occurrence: datetime | None
    assigned_user_id: int | None
    assigned_to: str | None
    resolution_notes: str | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    anomaly_summary: dict[str, Any] | None


class IncidentDetail(IncidentRead):
    templates: list[str]
    notes: list[NoteRead]
    related: list[SimilarRead]
    latest_investigation: InvestigationRead | None
    linked_log_count: int
