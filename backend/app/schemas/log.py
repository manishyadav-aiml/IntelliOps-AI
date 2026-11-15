from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

UploadStatus = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class LogUploadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    extension: str
    size_bytes: int
    status: UploadStatus
    total_lines: int
    processed_lines: int
    entry_count: int
    error_message: str | None
    parse_stats: dict[str, Any] | None
    parser_used: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class LogEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_id: int
    line_number: int
    timestamp: datetime | None
    level: str
    service: str
    hostname: str
    message: str
    original_message: str
    template_id: int | None
    template_text: str | None = None
    parameters: list[str] | None
    truncated: bool
    source_file: str | None = None


class TemplateSummary(BaseModel):
    template_id: int
    template_hash: str
    template_text: str
    occurrences: int


class FacetsRead(BaseModel):
    """Distinct values available for filtering the entries of one upload."""

    levels: list[str]
    services: list[str]
