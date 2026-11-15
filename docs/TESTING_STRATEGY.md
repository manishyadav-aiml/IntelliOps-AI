# Testing strategy

**Layers:** (1) pure-module unit tests (no DB/HTTP), (2) API tests with `TestClient`, in-memory SQLite and a fake LLM (`use_llm` fixture; `GEMINI_API_KEY` is always empty in tests), (3) Vitest + React Testing Library with mocked services, (4) a Playwright end-to-end test of the whole workflow with the LLM boundary mocked via `page.route`. Nothing requires a paid API.

## What has actually been executed (authoring environment, no network)
Environment: Python 3.12, numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, joblib 1.6.0, reportlab 5.0.1, pypdf 5.9.0, Node 22 with TypeScript 6.0.3. **pytest, FastAPI, SQLAlchemy, pydantic, bcrypt, Vitest, Playwright browsers were not available**, so a ~40-line pytest stand-in (supports `raises`, `approx`, `parametrize`, `tmp_path`, `importorskip`) ran the pure modules.

| Test module | Cases | Result |
|-------------|-------|--------|
| regex_parser, template_extraction, log_parser, log_upload | 16 + 4 (+1 skipped: needs `drain3`) + 7 + 21 | all passed |
| feature_engineering, anomaly_detection, severity, evaluation_and_hdfs | 8 + 13 + 7 + 7 | all passed |
| embeddings_and_store, incident_logic | 13 + 17 | all passed |
| ai (Gemini client, prompts, agent), rag (real PDFs via reportlab/pypdf, default-setting retrieval checks), document_upload | 29 + 24 + 6 | all passed |
| reports_and_dashboard (PDF text read back with pypdf) | 10 | all passed |
| root_cause (deterministic evidence engine) | 8 | all passed |
| smoke_script (the smoke-test script's own mechanics, against a stub server) | 2 | all passed |
| **Total executed** | **192 passed, 0 failed, 1 skipped** (16 modules) | |

Also executed: the synthetic experiment, the parser benchmark and the end-to-end parse -> features -> detection run on the synthetic sample logs (the baseline flags the payment-failure episode and nothing in normal traffic); a TypeScript type check of all 60 frontend source/test/e2e files against *stub* declarations for third-party packages (0 errors; this checks internal consistency, not the real library types); YAML syntax of compose, render and the workflows; static checks (no unused imports, no builtin-shadowing methods, and a model-vs-migration column cross-check: all 15 tables match; indexes/constraints not compared).

### Bugs found by simulating the unrun API tests with the real pure functions
Before packaging, the retrieval and similarity expectations of the unrun API tests were simulated with the real embedder and sample documents. This exposed and fixed: (1) unrelated incidents scoring 0.72 similarity because severity boilerplate dominated the incident text; (2) the demo question "what should I check when payments time out?" returning nothing (no stemming, "time out" vs "timeout"); (3) off-topic questions ("capital of France") returning chunks because stopwords dominated and then because of hash collisions in a 1024-dimension space. Each now has a regression test.

## Written but NOT executed (need the real dependencies)
Backend: `test_security` (8), `test_config` (5), `test_rate_limiter` (2), `test_health` (2), `test_auth_api` (13), `test_logs_api` (18), `test_incidents_api` (12), `test_ai_rag_reports_api` (18) = 78 test functions covering registration/login/JWT, user isolation on every resource, upload validation (incl. 413, traversal, empty/binary), parsing, background processing and retry, anomaly -> incident flow and idempotence, status/severity rules and audit entries, AI failure handling (503 codes), RAG upload/query/delete, reports in all formats, dashboard values and empty states.
Frontend: 10 test files (36 cases) (auth pages, protected routes, logs page, upload dropzone, pagination, components, incidents page, dashboard, assistant) and the Playwright spec `e2e/full-workflow.spec.ts` (register -> upload -> detect -> incident -> mocked AI -> RAG -> PDF report -> resolve -> logout).

**Do not treat these as passing.** Run them (commands in the README) and fix what fails; the first real run of the HTTP/DB layer is likely to surface bugs.
