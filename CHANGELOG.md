# Changelog

## [0.4.0] - Hardening
- Deterministic root-cause evidence engine (stored on incidents, used as AI evidence and in reports, shown in the UI).
- Lexical embedder fixed (stopwords, stemming, phrase normalisation, 4096 dims) after simulation showed false matches and misses; incident similarity text de-noised.
- `scripts/doctor.py` and `scripts/smoke_test.py`; `make doctor`, `make smoke`.

## [0.3.0] - Phases 3-10
- ML: causal window features, baseline + Isolation Forest + LOF, model registry, severity rules, evaluation/experiment code and scripts.
- Incidents: grouping/de-duplication, lifecycle with audit, timeline, notes, per-user similarity index.
- AI: Gemini REST provider with typed failures, prompt-injection hygiene, validated evidence-grounded investigations.
- RAG: PDF/TXT/MD ingestion, chunking, per-user vector store, citations restricted to retrieved chunks.
- Reports (PDF/CSV/JSON), dashboard, system status; 15-page React UI; Vitest tests and a Playwright spec.
- Docker, Compose, CI workflows, Render blueprint, lightweight/full dependency split; full documentation set and audit report.
- Changed: `/logs/{id}/analyze` now runs anomaly detection; parse retry moved to `/logs/{id}/reprocess`.

## [0.2.0] - Phase 2 (log management)
- Upload validation and safe streaming storage; background parsing with status/progress and duplicate-run protection.
- Regex line parser (ISO, HDFS, syslog, bracketed, CSV, configurable custom patterns); Drain3 template mining with regex fallback.
- Models/migration `0002` (`log_uploads`, `log_templates`, `log_entries`); `/logs` API; frontend Logs list and detail pages.
- Synthetic sample logs and generator script.

## [0.1.0] - Phase 1 (project foundation)
- Backend: FastAPI app factory, validated settings, structured JSON logging, consistent error format.
- Auth: register, login, `/auth/me`, logout (audit-only), bcrypt hashing, JWT, in-memory rate limiting.
- Database: SQLAlchemy 2 models (`users`, `audit_logs`) and Alembic initial migration.
- Frontend: Vite + React + TypeScript + Tailwind; login, register, protected routes, auth context.
- Tests written (backend pytest, frontend Vitest). See README "Verification status".
