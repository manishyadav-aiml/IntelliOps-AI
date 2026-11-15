from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    extension: str
    size_bytes: int
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
    page_count: int
    chunk_count: int
    embedder_name: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class RagQuery(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    document_ids: list[int] | None = Field(default=None, max_length=50)


class CitationRead(BaseModel):
    label: str
    document_id: int
    document_name: str
    page_number: int | None
    chunk_id: str
    snippet: str
    score: float


class RagResponse(BaseModel):
    answer: str
    sufficient: bool
    llm_used: bool
    citations: list[CitationRead]
    notice: str | None = None


class ReportGenerate(BaseModel):
    incident_id: int
    format: Literal["pdf", "csv", "json"]


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    format: str
    filename: str
    size_bytes: int
    created_at: datetime


class DashboardSummary(BaseModel):
    total_logs_processed: int
    uploads_total: int
    active_incidents: int
    critical_incidents: int
    anomalies_detected: int
    services_monitored: int
    resolved_incidents: int
    avg_time_to_acknowledge_seconds: float | None
    avg_time_to_resolve_seconds: float | None
    note: str = "Averages are null when the required timestamps do not exist yet."


class Bucket(BaseModel):
    bucket: str
    count: int


class NamedCount(BaseModel):
    name: str
    count: int


class DashboardTrends(BaseModel):
    bucket: Literal["hour", "day"]
    error_frequency: list[Bucket]
    anomaly_trend: list[Bucket]
    resolution_trend: list[Bucket]
    severity_distribution: list[NamedCount]
    top_templates: list[NamedCount]
    truncated: bool = False


class SystemStatus(BaseModel):
    version: str
    environment: str
    llm_provider: str
    llm_configured: bool
    embedder: str
    embedder_fallback_reason: str | None
    vector_backend: str
    template_miner: str
    trained_model: str | None
