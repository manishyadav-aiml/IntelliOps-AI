# Database schema

PostgreSQL in production, SQLite only for isolated tests. Schema is managed by Alembic (`0001`-`0004`); the application never
creates tables itself. All tables except `audit_logs.user_id` cascade on user deletion; `created_at`/`updated_at` are present
unless noted. Naming conventions (pk/fk/uq/ck/ix) are defined in `app/database/base.py`.

| Table | Purpose | Key columns / notes |
|-------|---------|---------------------|
| `users` | accounts | unique `email`, `hashed_password` (bcrypt), `role` (engineer/admin), `is_active` |
| `audit_logs` | security/audit trail | `user_id` (SET NULL), `action`, `resource_*`, `ip_address`, JSON `details` |
| `log_uploads` | uploaded files | `status` (PENDING/PROCESSING/COMPLETED/FAILED), line counters, JSON `parse_stats`, server-generated `stored_path` |
| `log_templates` | mined templates | unique (`user_id`, `template_hash`), `template_text` |
| `log_entries` | parsed lines | `upload_id`, `line_number` (unique pair), `timestamp` (nullable), `level`, `service`, `hostname`, `message`, `original_message`, `template_id`, JSON `parameters`; no `updated_at` |
| `anomaly_detections` | one scored window per row | `window_start/end`, `anomaly_detected`, `anomaly_score` (not a probability), `threshold`, `method`, `model_version`, JSON `contributing_features`/`features` |
| `incidents` | incidents | `severity` P1-P4, `status`, `fingerprint` (unique per user, NULL for manual), `severity_reasons`, `services`, `templates`, `error_templates`, `anomaly_summary`, occurrence/ack/resolve timestamps, `assigned_user_id` |
| `incident_events` | timeline | `event_type`, real `timestamp`, `actor_user_id`, JSON `details`; created-at only |
| `incident_notes` | human notes | `author_id`, `content` |
| `incident_log_links` | associated logs | unique (`incident_id`, `log_entry_id`); capped at 50 error entries per incident |
| `incident_relationships` | similarity links | `similarity_score`, JSON `shared` (services/templates/error patterns) |
| `ai_investigations` | AI runs | `status` COMPLETED/FAILED, `provider`, JSON `result`, `error_code` |
| `documents` | documentation library | `status`, `page_count`, `chunk_count`, `embedder_name` |
| `document_chunks` | chunk text + page | unique (`document_id`, `chunk_id`), `page_number` (nullable); created-at not tracked |
| `reports` | generated reports | `format` pdf/csv/json, `stored_path`, `size_bytes` |

Vectors are **not** stored in PostgreSQL. They live in per-user files (`INDEX_DIR/user_<id>/{incidents,documents}/vectors.npy` +
`metadata.json`) and can always be rebuilt from `incidents` / `document_chunks`.

**Migrations:** `cd backend && alembic upgrade head`. The migrations were hand-written and have **not been run** against
PostgreSQL yet; run them on an empty database and compare with `alembic revision --autogenerate` (it should find no differences).
