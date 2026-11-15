# Security

Status: **Phase 1 only** (authentication foundation). Later phases extend this document.

## Implemented (Phase 1)
- Passwords hashed with bcrypt; never stored or returned in plaintext; hashes never appear in API responses.
- Password policy: 8+ characters, at least one letter and one digit, max 72 bytes (bcrypt limit).
- JWT access tokens (HS256) with `sub`, `iat`, `exp`, `jti`; `exp`/`iat`/`sub` are required on decode; `alg=none` tokens are rejected.
- Login does not reveal whether an email exists (same error and a dummy bcrypt check for timing).
- Rate limiting on login and registration (in-memory, per IP, per process).
- Consistent error format; validation errors never echo submitted values; unhandled errors return a generic message and log details server-side only.
- Secrets come from environment variables. In production the app refuses to start with `DEBUG=true`, a short/missing `JWT_SECRET`, a non-PostgreSQL database, or wildcard CORS.
- Audit log entries for registration, login success/failure and logout.
- Swagger/OpenAPI endpoints are disabled when `DEBUG=false`.

## Implemented (Phase 2: uploads)
- Extension allow-list plus content checks (NUL bytes, executable/archive magic bytes, UTF-8 validity, control-character ratio); the extension alone is never trusted.
- Streaming write with a size limit; stored under a server-generated `<user_id>/<uuid>.<ext>` path. The user-supplied name is only a sanitized display label, so path traversal is not possible.
- Uploaded files are only read as text, never executed. Rejected uploads leave no file behind.
- Every log query is scoped to the authenticated user; other users' resources return 404.
- Upload rate limiting; LIKE wildcards in search are escaped; message content is stored and returned as data (the React UI renders it as text, not HTML).

## Known limitations (Phase 2)
- A worker crash can leave an upload in `PROCESSING` indefinitely (no heartbeat/stale-job recovery yet; delete is blocked while PROCESSING).
- Background processing uses FastAPI `BackgroundTasks` (in-process). Celery/Redis is a later, optional step.
- Content checks use the first 64 KB; later bytes are decoded with replacement characters (counted in parse stats).

## Known limitations (Phase 1)
- **Logout does not revoke the token server-side.** JWTs are stateless; a stolen token stays valid until it expires (default 60 minutes). Mitigation planned: shorter expiry and/or a revocation list.
- The frontend stores the token in `localStorage`, which is readable by any script on the page if an XSS bug exists. Alternative: httpOnly cookies (needs CSRF handling).
- The rate limiter is per process and keyed on the direct peer IP; behind a proxy all users may share one IP unless forwarded-IP handling is configured. Use Redis for multi-instance deployments.
- Registration reveals whether an email is already registered (409). This is a deliberate usability trade-off.
- No email verification, password reset or account lockout yet.

## Implemented (Phases 3-8)
- Incident, anomaly, document, chunk, report and AI-investigation data are always queried by the authenticated user id; vector stores are per user and also filter on `owner_id`.
- LLM key stays server-side; logs/notes/documents are sanitised and wrapped as untrusted data; AI output is validated and never executed; AI failures return typed 503s.
- Reports escape PDF text and neutralise CSV formula injection; report downloads are served from server-held paths with sanitised names.
- Severity/status/assignment changes and AI runs are audit-logged.

## Known limitations (Phases 3-8)
- Prompt-injection defence is mitigation only. Documents/logs may still influence model wording; the validation layer limits claims to known evidence and strips execution claims.
- joblib model files are pickles: load models only from a directory you control.
- Uploaded files and reports are stored unencrypted on local disk and are not virus-scanned.
- None of the HTTP-layer security controls have been exercised by a running test yet (see docs/TESTING_STRATEGY.md).

## Reporting a vulnerability
Open a private security advisory on the repository or contact the maintainer listed in the README. Do not post secrets or exploits in public issues.
