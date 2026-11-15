# Requirements overview

| Group | Packages | Notes |
|-------|----------|-------|
| Web/API/DB (pinned) | fastapi, uvicorn, pydantic, pydantic-settings, email-validator, sqlalchemy, alembic, psycopg, PyJWT, bcrypt, python-multipart | exact pins; never install-tested |
| Parsing | drain3 | optional at runtime (regex fallback) |
| Data/ML (ranges) | numpy, pandas, scikit-learn, joblib | tested on numpy 2.5.4 / pandas 3.0.6 / scikit-learn 1.9.1 / joblib 1.6.0 |
| Documents/Reports (ranges) | pypdf, reportlab | tested on pypdf 5.9.0 / reportlab 5.0.1 |
| Optional heavy (`requirements-full.txt`) | sentence-transformers, faiss-cpu | semantic embeddings + FAISS; lightweight fallbacks exist |
| Dev | pytest, httpx, ruff | |
| Frontend | react, react-dom, react-router-dom, axios, lucide-react, recharts, tailwindcss | dev: vite, typescript, vitest, Testing Library, eslint, @playwright/test |
| Not used | celery, redis | background work uses FastAPI BackgroundTasks |
