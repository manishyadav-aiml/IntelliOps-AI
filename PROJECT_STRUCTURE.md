# Project structure

```
IntelliOps-AI/
  backend/
    app/
      main.py                      app factory, middleware, error handlers
      core/                        config, security, exceptions, logging, rate_limit
      database/                    Base + naming convention, sessions
      models/                      user, audit_log, log, incident, document
      schemas/                     auth, log, incident, knowledge (Pydantic)
      repositories/                user, audit, log
      api/deps.py, api/v1/         router + endpoints (auth, health, logs, anomalies, incidents, documents, rag, reports, dashboard, system)
      parsers/                     regex_parser, drain_parser (Drain3 + fallback), log_parser (streaming reader)
      ml/                          preprocessing, feature_engineering, anomaly_detection, severity_classifier, evaluation, hdfs, experiments
      rag/                         document_loader, chunking, embeddings, vector_store, retrieval, generator
      ai/                          llm_provider, gemini_provider, prompts, investigation_agent
      services/                    auth, log (+upload, processing), anomaly, incident (+logic, similarity, similarity_index),
                                   knowledge (documents + RAG), document_upload, investigation, report (+builder), dashboard (+logic), llm_factory, embedder_cache
    alembic/versions/              0001 users+audit, 0002 logs, 0003 incidents+anomalies, 0004 ai+documents+reports
    tests/                         25 test modules (see docs/TESTING_STRATEGY.md)
    Dockerfile, requirements.txt, requirements-full.txt, requirements-dev.txt, pyproject.toml, .env.example
  frontend/
    src/{components,context,pages,routes,services,types,utils}   tests/ (Vitest)   e2e/ (Playwright)
    Dockerfile, nginx.conf, package.json, vite.config.ts, tailwind/postcss/eslint config
  data/sample_logs/ (synthetic)   data/sample_documents/ (demonstration runbooks)
  scripts/                         download_dataset, prepare_dataset, train_anomaly_model, evaluate_models, benchmark_log_parser, generate_sample_logs
  experiments/                     hdfs_experiment.json, results/synthetic.json
  docs/                            full documentation set + FINAL_AUDIT_REPORT.md
  .github/workflows/               backend, frontend, docker
  docker-compose.yml, render.yaml, Makefile, README.md, SECURITY.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE
```
Directories from the original plan that hold no files yet (`notebooks/`, `screenshots/`, `models/`) are not created to avoid empty placeholders.
