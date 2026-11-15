# Final project audit report

Scope: the whole master-prompt specification (Phases 1-10). Written by the author of the code; every claim below is limited to what was actually done or run.
**Verdict: the project is NOT complete by its own acceptance criteria.** The core logic is implemented and unit-tested; the HTTP/database/frontend/infrastructure layers are written but unexecuted.

## Environment used
No network access. Python 3.12 with numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, joblib 1.6.0, reportlab 5.0.1, pypdf 5.9.0; Node 22, TypeScript 6.0.3, esbuild. Not available: pytest (a small stand-in ran the pure tests), FastAPI, SQLAlchemy, pydantic, bcrypt, Alembic, PostgreSQL, Docker, drain3, faiss, sentence-transformers, Vitest, React Router, axios, Recharts, Playwright browsers, ruff/mypy/eslint.

## Implemented features
| Feature | Status | Evidence |
|---------|--------|----------|
| Log parsing (ISO/HDFS/syslog/bracketed/CSV/custom patterns), unknown-format handling, template masking, parameter extraction | **Implemented + tested (executed)** | 48 cases |
| Upload validation (extension, content, size, traversal, empty/binary) | **Implemented + tested (executed)** for the validation/storage functions | 27 cases |
| Feature engineering (causal), baseline detector, Isolation Forest, LOF, model save/load/versioning, severity rules, evaluation metrics, block-id splitting | **Implemented + tested (executed)** | 35 cases |
| Embeddings (lexical fallback with stopwords, stemming and phrase normalisation), vector store (numpy; persistence, rebuild, owner isolation), similar-incident logic, incident grouping/dedup/status rules | **Implemented + tested (executed)** | 30 cases |
| Gemini client (typed failures), prompt-injection hygiene, evidence-grounded investigation validation | **Implemented + tested (executed) against a fake transport; never called a real LLM** | 29 cases |
| Document extraction (real PDFs), chunking, retrieval, grounded answers with verified citations | **Implemented + tested (executed)** | 30 cases |
| PDF/CSV/JSON report builders (AI vs human separation, root-cause section), dashboard aggregation | **Implemented + tested (executed)** | 10 cases |
| Deterministic root-cause evidence engine (earliest-failing service, new error templates, rate shifts, vanished templates; JSON-safe; feeds incidents, AI evidence and reports) | **Implemented + tested (executed)**; its integration into the DB service layer was not executed | 8 cases |
| `scripts/smoke_test.py` (30-step end-to-end check of a running server) and `scripts/doctor.py` (environment check) | Smoke-script mechanics **executed against a stub server**; never run against the real API. The doctor was executed here and correctly reported the missing packages | 2 cases |
| Auth (register/login/me/logout), health, config validation, rate limiting | Written; **not executed** | 31 test functions written |
| REST API, SQLAlchemy models, Alembic 0001-0004, background processing, incident/anomaly/document/report/dashboard services | Written; **not executed** | 48 API test functions written |
| React app: 13 pages (14 routes), reusable components, charts (Recharts), toasts | Written; type-checked against stubs only; **not built, not run** | 10 test files + Playwright spec written |
| Docker, Compose, GitHub Actions, Render blueprint | Written; YAML parses; **never run** | |
| Documentation set | Written | this folder |

## Improvements made after the first audit draft (all found by running code)
- Lexical embedder: stopwords, light stemming, "time out" normalisation and 4096 dimensions (hash collisions made unrelated text match); incident similarity text no longer includes severity boilerplate.
- Deterministic root-cause evidence engine added (temporal evidence, with a mandatory not-causation disclaimer).
- `scripts/smoke_test.py` and `scripts/doctor.py` added so the unexecuted layers can be verified quickly on a machine with network access.

## Partially implemented
- Drain3 integration (code present, never executed; regex fallback is tested).
- FAISS backend (code present, never executed; NumPy backend tested).
- Gemini provider (REST client tested only with a fake transport).
- Background processing via `BackgroundTasks` (spec's Celery/Redis variant not built).
- LogHub experiments: scripts and configuration exist, **no LogHub data run**.

## Not implemented
Celery + Redis; supervised severity classifier; BGL/OpenStack/Apache pipelines; token revocation, refresh tokens, email verification, password reset; multi-user collaboration/permissions; screenshots; live deployment; ESLint/ruff-strict/mypy runs.

## Tests executed
Pure-module suites: **192 passed, 0 failed, 1 skipped** (16 modules; the skip needs `drain3`). Plus: synthetic experiment, parser benchmark, sample-log detection run, 60-file TypeScript stub check (0 errors), YAML parsing, static checks (including a model-vs-migration column cross-check: all 15 tables match; indexes and constraints were not compared).

## Tests not executed
78 backend test functions (security, config, rate limiter, health, auth API, logs API, incidents API, AI/RAG/report/dashboard API) and all 10 frontend test files and the Playwright e2e spec. Status: **unknown**, neither passed nor failed.

## Tests failed
None of the executed tests failed in their final state. During development real defects were found and fixed by running tests: a wrong test expectation for `error_change`, and a genuine Isolation Forest limitation (now documented, regression-tested and mitigated). Not-yet-run tests may reveal more.

## Known bugs / risks (unverified, likely places to look first)
Pydantic/SQLAlchemy/FastAPI interactions in the untested layers (e.g. generic `Page[T]` response models, `Query` aliases, background-task sessions on SQLite `StaticPool`); migration/model drift; PostgreSQL-specific behaviour; npm dependency compatibility (React 18 pins; Recharts 2.x); `PROCESSING` rows stuck after a crash; the pinned Gemini model id.

## Security limitations
Token not revoked on logout; token in `localStorage`; in-memory per-process rate limiting; no lockout, email verification or password reset; files unencrypted/unscanned on disk; prompt-injection defence is mitigation, not a guarantee; no external review or dependency audit. See SECURITY.md.

## ML evaluation results
LogHub: **not run**. Synthetic pipeline check only (seed 42, block-id split, 600 test blocks): Isolation Forest P 0.759 / R 0.846 / F1 0.800 / PR-AUC 0.823 / FPR 0.012; LOF P 0.486 / R 0.692 / F1 0.571 / PR-AUC 0.730 / FPR 0.033. These describe generated data, not real logs.

## Deployment readiness
Not ready: nothing deployed, images and compose never built, migrations never run, free-tier memory limits require the lightweight embedder mode.

## Acceptance criteria (spec section 36)
Met and verified: Drain3 *fallback* works; ML anomaly detection works (library level); severity classification works; citations refer to real chunks (unit-level); PDF and CSV report generation works (library level); no fake metrics presented; `.env` is git-ignored.
Written but unverified: backend/frontend start, migrations, registration/login/auth, user isolation at the API, log upload at the API, incident create/update, similar-incident search at the API, AI investigation handling at the API, document upload/indexing at the API, timeline, dashboard from backend data, responsiveness, Docker setup, GitHub Actions.
Not met: backend/frontend/e2e tests *passing* (not run), ML evaluation reproducible *on LogHub* (not run), deployment docs verified, screenshots.

## Exact commands to run the application and verify this audit
```bash
# database
docker compose up -d db
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # add -r requirements-full.txt for semantic search + FAISS
cp .env.example .env && alembic upgrade head
pytest -v                                    # FIRST REAL RUN of 78 untested + all other backend tests
uvicorn app.main:app --reload --port 8000
# frontend (new terminal)
cd frontend && cp .env.example .env && npm install
npm run lint && npm test && npm run build && npm run dev
# end-to-end (backend deps + `npx playwright install` first)
npm run e2e
# everything in containers
docker compose up --build
```
Send the first failures (if any) so they can be fixed; do not edit this report to say "passed" until they have.
