# Security design

**Authentication:** bcrypt password hashing (max 72 bytes, 8+ chars with letter and digit); HS256 JWT with `sub/iat/exp/jti`, required claims, `alg=none` rejected; constant-effort login (dummy hash) with one error for unknown user or bad password; per-IP rate limits (login, register, uploads, AI calls).

**Authorization and isolation:** every query filters by the authenticated `user_id`; foreign ids return 404. Vector stores are per user and also filter on `owner_id`. Uploaded-file ids, incident ids, document ids, report ids and anomaly ids are all covered by cross-user tests (written; see TESTING_STRATEGY for what has run).

**Files:** extension allow-list + content checks, streamed size limit, server-generated storage names under `<user_id>/`, never executed, removed on failed validation; downloads served from server-held paths with a sanitised filename.

**LLM safety:** the API key is read server-side only and sent in a header (never logged, never returned; `/system/status` exposes only a boolean). Logs, templates, notes and documents are sanitised and delimited as untrusted data; model output is validated (known evidence ids only, unsupported claims dropped, "executed an action" statements removed, "confirmed" causes downgraded, confidence capped on thin evidence); nothing the model suggests is ever executed. All AI failures map to typed 503 errors and never affect non-AI features.

**Other:** CORS allow-list, safe generic 500s (details only in server logs), JSON structured logs without bodies/tokens/passwords, CSV formula-injection guard in reports, PDF text escaped, OpenAPI hidden unless `DEBUG`, production config validation (refuses `DEBUG=true`, short `JWT_SECRET`, non-PostgreSQL, wildcard CORS), audit log for auth, uploads, incident changes, AI runs, reports and RAG queries.

Known gaps are listed in [../SECURITY.md](../SECURITY.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md). No external security review or dependency audit has been done.
