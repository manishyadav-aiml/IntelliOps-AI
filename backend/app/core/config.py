"""Centralised, validated application settings (loaded from environment / .env)."""

import json
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.parsers.regex_parser import compile_custom_patterns

_DEV_DATABASE_URL = "postgresql+psycopg://intelliops:intelliops@localhost:5432/intelliops"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "IntelliOps AI"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    secret_key: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(60, ge=1, le=1440)

    database_url: str = _DEV_DATABASE_URL
    cors_origins: str = "http://localhost:5173"

    rate_limit_enabled: bool = True
    login_rate_limit_attempts: int = Field(10, ge=1)
    login_rate_limit_window_seconds: int = Field(300, ge=1)
    register_rate_limit_attempts: int = Field(10, ge=1)
    register_rate_limit_window_seconds: int = Field(3600, ge=1)

    # Log management (Phase 2)
    upload_dir: str = "data/uploads"
    upload_rate_limit_attempts: int = Field(30, ge=1)
    upload_rate_limit_window_seconds: int = Field(3600, ge=1)
    log_max_line_length: int = Field(10_000, ge=100)
    log_batch_size: int = Field(1000, ge=10)
    log_template_miner: Literal["drain", "regex"] = "drain"
    # JSON list of regex strings with named groups (must include "message"); tried before built-ins.
    log_parser_extra_patterns: str = ""

    # Machine learning / incidents (Phase 3-4)
    models_dir: str = "models"
    index_dir: str = "models/indexes"
    anomaly_window_seconds: int = Field(60, ge=10, le=3600)
    # Optional override of the trained model's own threshold (unset = use the model's threshold).
    anomaly_threshold: float | None = None
    similarity_min_score: float = Field(0.3, ge=0.0, le=1.0)
    embedding_fallback: bool = True  # fall back to the lexical hashing embedder if the model is unavailable

    # Generative AI (Phase 5)
    gemini_model: str = "gemini-2.0-flash"  # verify against Google's current model list before deploying
    llm_timeout_seconds: float = Field(30.0, gt=0)

    ai_rate_limit_attempts: int = Field(60, ge=1)
    ai_rate_limit_window_seconds: int = Field(3600, ge=1)

    # RAG (Phase 6)
    rag_chunk_size: int = Field(800, ge=100)
    rag_chunk_overlap: int = Field(100, ge=0)
    rag_top_k: int = Field(4, ge=1, le=20)
    rag_similarity_threshold: float = Field(0.15, ge=0.0, le=1.0)

    # Reports (Phase 8)
    reports_dir: str = "data/reports"

    # Reserved for later phases; declared now so .env.example and validation stay in one place.
    gemini_api_key: str = ""
    llm_provider: str = "gemini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    matcher: str = "faiss"
    redis_url: str = ""
    max_upload_size_mb: int = Field(50, ge=1)

    @property
    def log_extra_patterns_list(self) -> list[str]:
        return json.loads(self.log_parser_extra_patterns) if self.log_parser_extra_patterns else []

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _validate_environment(self) -> "Settings":
        # Managed hosts often hand out "postgres://" or "postgresql://" URLs; SQLAlchemy needs the psycopg driver.
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(prefix):]
        if not self.jwt_secret and not self.is_production:
            # Development/testing convenience: ephemeral key, tokens become invalid on restart.
            self.jwt_secret = secrets.token_urlsafe(48)
        if self.log_parser_extra_patterns:
            try:
                patterns = json.loads(self.log_parser_extra_patterns)
                if not isinstance(patterns, list) or not all(isinstance(x, str) for x in patterns):
                    raise ValueError("LOG_PARSER_EXTRA_PATTERNS must be a JSON list of strings")
                compile_custom_patterns(patterns)
            except json.JSONDecodeError as exc:
                raise ValueError("LOG_PARSER_EXTRA_PATTERNS is not valid JSON") from exc
        if self.is_production:
            problems: list[str] = []
            if self.debug:
                problems.append("DEBUG must be false in production")
            if len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET must be set and at least 32 characters in production")
            if not self.database_url.startswith("postgresql"):
                problems.append("DATABASE_URL must be a PostgreSQL URL in production")
            if "*" in self.cors_origins_list:
                problems.append("CORS_ORIGINS must not contain '*' in production")
            if problems:
                raise ValueError("; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
