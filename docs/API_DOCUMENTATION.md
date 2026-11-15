# API documentation

Base path `/api/v1`. Interactive OpenAPI docs are served at `/docs` only when `DEBUG=true`. All endpoints except register, login
and health require `Authorization: Bearer <token>`. Errors always look like
`{"error": {"code": "...", "message": "...", "details": [...]}}` (validation errors list only field names and messages, never submitted values).
List endpoints return `{"items": [...], "total", "page", "page_size"}`. Other users' resources behave as non-existent (404).

| Method & path | Purpose | Notes |
|---------------|---------|-------|
| `GET /health` | liveness + DB check | 503 with `status: degraded` if the DB is down |
| `POST /auth/register` | create account | 201; 409 duplicate; 422 weak password; rate limited |
| `POST /auth/login` | JSON `{email, password}` -> `{access_token, expires_in, user}` | 401 identical for wrong password/unknown user; rate limited |
| `GET /auth/me` / `POST /auth/logout` | current user / audit-only logout | logout does not revoke the JWT |
| `POST /logs/upload` | multipart `file` | 202 + status `PENDING`; 413/422 on validation failure |
| `GET /logs` | list uploads | `status`, `q`, `sort_by`, `order`, `page`, `page_size` |
| `GET /logs/{id}` | upload detail + `parse_stats` | poll for `COMPLETED` |
| `GET /logs/{id}/entries` | parsed lines | `level`, `service`, `template_id`, `q`, `start`, `end`, sorting, pagination |
| `GET /logs/{id}/entries/{entry_id}` · `/templates` · `/facets` | entry detail, top templates, filter values | |
| `POST /logs/{id}/reprocess` | retry parsing of a `FAILED` upload | 409 otherwise |
| `POST /logs/{id}/analyze?window_seconds=` | anomaly detection + incident creation | 409 unless `COMPLETED`; idempotent |
| `GET /anomalies`, `GET /anomalies/{id}` | scored windows | `upload_id`, `detected_only`, `sort_by` |
| `GET /incidents`, `POST /incidents` | list (filters: `status`, `severity`, `service`, `q`, sorting) / manual create | |
| `GET /incidents/{id}` | detail incl. notes, related incidents, latest AI investigation, `anomaly_summary.rca` (deterministic root-cause evidence) | |
| `PATCH /incidents/{id}` | title, description, severity, status, assignment (self only), resolution notes | status graph enforced (409); severity changes audited |
| `GET /incidents/{id}/timeline` | events, filter `event_type`, `start`, `end` | |
| `GET /incidents/{id}/similar` | similar incidents of the same user | similarity is not a root-cause proof |
| `POST /incidents/{id}/notes` | add human note | |
| `POST /incidents/{id}/investigate` | AI investigation `{question?}` | 503 with `llm_*` code if AI unavailable; rate limited |
| `POST /documents/upload`, `GET /documents`, `GET/DELETE /documents/{id}`, `POST /documents/{id}/index` | documentation library | PDF/TXT/MD; indexing in background |
| `POST /rag/query` | `{question, document_ids?}` -> `{answer, sufficient, llm_used, citations[], notice}` | works without an LLM (excerpts only) |
| `GET /reports`, `POST /reports/generate`, `GET /reports/{id}/download` | reports | `{incident_id, format: pdf|csv|json}` |
| `GET /dashboard/summary` · `/trends` · `/services` | dashboard data | filters `start`, `end`, `service`, `bucket` |
| `GET /system/status` | non-secret runtime info for Settings | never returns keys |

Error codes you may see: `validation_error`, `authentication_failed`, `not_found`, `conflict`, `invalid_state`, `invalid_file`,
`invalid_document`, `file_too_large`, `rate_limited`, `llm_not_configured`, `llm_invalid_key`, `llm_timeout`, `llm_rate_limited`,
`llm_provider_error`, `llm_malformed_response`, `internal_error`.
