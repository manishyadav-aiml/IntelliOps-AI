from fastapi import APIRouter

from app.api.v1.endpoints import (
    anomalies,
    auth,
    dashboard,
    documents,
    health,
    incidents,
    logs,
    rag,
    reports,
    system,
)

api_router = APIRouter()
for module in (health, auth, logs, anomalies, incidents, documents, rag, reports, dashboard, system):
    api_router.include_router(module.router)
