# Developer guide

## Setup
See the README. Backend: Python 3.11+, `pip install -r requirements-dev.txt`, `pytest`. Frontend: Node 20+, `npm install`, `npm test`.

## Where things live
`backend/app/{parsers,ml,rag,ai}` pure algorithms (unit-test these first), `services/` use cases, `api/v1/endpoints/` thin HTTP layer, `models/` + `alembic/versions/` schema.
Frontend: `src/services` (one module per backend area), `src/pages`, `src/components/{common,layout,logs,incidents}`.

## Common extensions
* **New log format:** add a regex to `BUILTIN_PATTERNS` in `parsers/regex_parser.py` (named groups `timestamp, level, service, hostname, message`) or set `LOG_PARSER_EXTRA_PATTERNS`; add a test line to `test_regex_parser.py`.
* **New detector:** implement `detect(feats) -> list[AnomalyResult]`, wire it in `ml/anomaly_detection.detect_anomalies`, add tests incl. a causality check.
* **New LLM provider:** implement `LLMProvider.generate_json` (raise the typed errors in `ai/llm_provider.py`), return it from `services/llm_factory.create_provider`, add a `LLM_PROVIDER` value.
* **New incident event / status rule:** `services/incident_logic.py` (pure) then `incident_service.py`.
* **Schema change:** edit the model, `alembic revision --autogenerate -m "..."`, review, test `upgrade`/`downgrade`.

## Verifying a deployment
`python scripts/doctor.py` (environment) then `python scripts/smoke_test.py http://localhost:8000` (about 30 end-to-end checks; `--llm` when an AI key is set). The smoke script uses only the synthetic data in `data/`.

## Rules this code base follows
User-scoped queries everywhere (404 for foreign ids); never show invented data; AI output is validated and labelled; optional dependencies degrade, never crash; update docs with behaviour changes; do not report test results or metrics you did not produce.

## Train a model
`python scripts/train_anomaly_model.py --logs <files> --window 60 --quantile 0.97` (writes `models/anomaly_<version>.joblib` + `latest.json`; the API uses it automatically when the window matches). Include some past incidents in the training logs.
