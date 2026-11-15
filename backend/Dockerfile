# Build context: ./backend   (docker build -t intelliops-backend ./backend)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# INSTALL_FULL=true adds sentence-transformers + faiss-cpu (large). Default is the lightweight demo mode.
ARG INSTALL_FULL=false
COPY requirements.txt requirements-full.txt ./
RUN pip install -r requirements.txt \
    && if [ "$INSTALL_FULL" = "true" ]; then pip install -r requirements-full.txt; fi

COPY . .

# Non-root runtime user; /data holds uploads, models, indexes and reports (mount a volume here).
RUN useradd --create-home --uid 10001 appuser && mkdir -p /data && chown -R appuser /data /app
USER appuser

ENV UPLOAD_DIR=/data/uploads MODELS_DIR=/data/models INDEX_DIR=/data/models/indexes REPORTS_DIR=/data/reports
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:%s/api/v1/health' % os.environ.get('PORT','8000')).status == 200 else 1)"

# Migrations run before the server starts (the app never creates tables on its own).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
