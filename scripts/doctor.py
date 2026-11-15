"""Environment doctor: finds the usual first-run problems in seconds.   python scripts/doctor.py

Checks Python version, required/optional packages, configuration validity, writable data directories,
database connectivity and migration state, and the AI/embedding setup. Read-only (creates nothing).
Run it from the repo root (it loads backend/.env if present).
"""

import importlib.metadata as md
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
problems = warnings = 0


def line(kind: str, text: str) -> None:
    global problems, warnings
    problems += kind == "FAIL"
    warnings += kind == "WARN"
    print(f"[{kind}] {text}")


def version(pkg: str) -> str | None:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None


def main() -> int:
    py = sys.version_info
    line("OK" if py >= (3, 11) else "FAIL", f"Python {py.major}.{py.minor}.{py.micro} (3.11+ required)")

    required = ["fastapi", "uvicorn", "pydantic", "pydantic-settings", "email-validator", "sqlalchemy", "alembic", "psycopg",
                "PyJWT", "bcrypt", "python-multipart", "numpy", "pandas", "scikit-learn", "joblib", "pypdf", "reportlab"]
    for pkg in required:
        v = version(pkg)
        line("OK" if v else "FAIL", f"{pkg} {v or 'NOT INSTALLED  -> pip install -r backend/requirements-dev.txt'}")
    for pkg, why in (("drain3", "Drain3 template mining (regex fallback is used otherwise)"),
                     ("sentence-transformers", "semantic embeddings (lexical fallback otherwise)"),
                     ("faiss-cpu", "FAISS search (exact NumPy search otherwise)")):
        v = version(pkg)
        line("OK" if v else "WARN", f"{pkg} {v or 'not installed: ' + why}")

    try:
        from app.core.config import get_settings

        s = get_settings()
        line("OK", f"configuration valid (APP_ENV={s.app_env}, DEBUG={s.debug})")
    except Exception as exc:
        line("FAIL", f"configuration invalid: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}")
        return summary()

    if not (BACKEND / ".env").exists():
        line("WARN", "backend/.env not found (defaults are used). Copy backend/.env.example to backend/.env")
    for name in ("upload_dir", "models_dir", "index_dir", "reports_dir"):
        path = (BACKEND / getattr(s, name)).resolve()
        probe = path
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        line("OK" if os.access(probe, os.W_OK) else "FAIL", f"{name} -> {path} ({'writable' if os.access(probe, os.W_OK) else 'NOT writable'})")

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(s.database_url, connect_args={"connect_timeout": 5} if s.database_url.startswith("postgresql") else {})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            line("OK", f"database reachable ({engine.dialect.name})")
            try:
                current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                line("OK" if current == "0004" else "WARN", f"migration version {current} (latest is 0004; run: cd backend && alembic upgrade head)")
            except Exception:
                line("WARN", "no alembic_version table: run  cd backend && alembic upgrade head")
    except ImportError:
        line("FAIL", "sqlalchemy missing, database not checked")
    except Exception as exc:
        line("FAIL", f"database not reachable: {type(exc).__name__}. Is PostgreSQL running (docker compose up -d db) and DATABASE_URL correct?")

    from app.services.llm_factory import llm_configured

    line("OK" if llm_configured(s) else "WARN", "AI assistant " + ("configured" if llm_configured(s) else "not configured (no GEMINI_API_KEY): AI features return a clear 'not configured' message; everything else works"))
    try:
        from app.rag.embeddings import create_embedder

        e = create_embedder(s.embedding_model, s.embedding_fallback)
        line("OK" if not e.fallback_reason else "WARN", f"embedder: {e.name}" + (f" (fallback: {e.fallback_reason})" if e.fallback_reason else ""))
    except Exception as exc:
        line("FAIL", f"embedder unavailable: {exc}")
    return summary()


def summary() -> int:
    print(f"\n{problems} problem(s), {warnings} warning(s)." + ("  Fix the FAIL lines first." if problems else "  Ready to run."))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
