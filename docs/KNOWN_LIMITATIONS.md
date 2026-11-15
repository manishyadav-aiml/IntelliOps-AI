# Known limitations (honest list)

## Verification
- The HTTP, database, migration, frontend-build, Docker and CI layers were **never executed** in the authoring environment (no network, no FastAPI/SQLAlchemy/Node packages). Expect first-run bugs. See TESTING_STRATEGY.md for exactly what ran.
- Hand-written Alembic migrations and exact dependency pins are untested; Drain3 and FAISS code paths were not executed (packages unavailable). PostgreSQL-specific behaviour is untested (tests use SQLite).
- No screenshots exist (nothing could be run in a browser). Deployment was not attempted.

## Machine learning
- **No evaluation on LogHub was run.** The only reported metrics are synthetic-pipeline checks.
- Isolation Forest does not extrapolate beyond its training range (mitigated by the labelled baseline safeguard). Baseline needs >= 5 prior windows. Windows are fixed grids; very wide time ranges are rejected (>200k windows).
- Severity is rule-based (thresholds are judgement calls, not learned). Anomaly scores are uncalibrated.
- Entries without timestamps are excluded from detection. Naive timestamps are assumed UTC. Syslog levels are keyword-inferred.
- BGL/OpenStack/Apache experiments are not implemented.

## AI / RAG
- The Gemini model id (`GEMINI_MODEL`) and REST contract were written from documentation knowledge and never called; verify before relying on it.
- Prompt-injection defences reduce risk but do not eliminate it; the structure validation is the real safeguard and only checks evidence ids and certain claim types, not factual correctness.
- The lexical fallback embedder is keyword matching with light stemming: it still misses synonyms and word-family differences (e.g. 'respond' vs 'response'). Chunking is character-based, not token-based. The default similarity threshold is tuned to nothing in particular; tune it for your embedder.
- No reranking, no multi-turn memory in the Assistant, no OCR for scanned PDFs.

## Product / security
- Single-user data model: no teams, no sharing, assignment only to yourself; roles exist but `admin` has no extra powers.
- JWT logout does not revoke tokens; token stored in `localStorage`; no refresh tokens, email verification, password reset or account lockout; registration reveals existing emails.
- Rate limiter is in-memory per process (use a single instance or add Redis).
- Background work uses in-process `BackgroundTasks`: a crash can leave `PROCESSING` rows stuck; no Celery/Redis (spec marked it optional).
- Analysis runs synchronously inside the request (fine for thousands of windows, not millions); dashboard trend queries cap at 200k rows; incident log links cap at 50 entries.
- Files live on local disk; they are not encrypted at rest and not virus-scanned.
- Dashboard "services monitored" counts distinct service names across all of a user's entries.
- `frontend/tsconfig` excludes `e2e/`; `npm install` is used in CI because no lockfile has been generated.
