import os
import tempfile

# Must be set before the app (and its cached settings) is imported.
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-" + "x" * 32
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="intelliops-test-uploads-")
os.environ["LOG_TEMPLATE_MINER"] = "regex"  # deterministic, no optional dependency needed
os.environ["LOG_BATCH_SIZE"] = "10"  # exercise multi-batch inserts with small files
os.environ["MODELS_DIR"] = tempfile.mkdtemp(prefix="intelliops-test-models-")
os.environ["INDEX_DIR"] = tempfile.mkdtemp(prefix="intelliops-test-indexes-")
os.environ["REPORTS_DIR"] = tempfile.mkdtemp(prefix="intelliops-test-reports-")
os.environ["EMBEDDING_MODEL"] = "hashing"  # deterministic lexical embedder; no model download
os.environ["GEMINI_API_KEY"] = ""  # tests must never reach a real LLM
os.environ["RATE_LIMIT_ENABLED"] = "true"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.api.deps import get_llm_provider, get_processing_session_factory  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

VALID_USER = {"email": "ada@example.com", "full_name": "Ada Lovelace", "password": "Str0ngPassw0rd"}
OTHER_USER = {"email": "bob@example.com", "full_name": "Bob Builder", "password": "An0therPassw0rd"}


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)  # isolated tests only; production uses Alembic
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    limiter.reset()

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:  # a fresh session per request, like production
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_processing_session_factory] = lambda: session_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()


def _login_headers(client: TestClient, user: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=user)
    token = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    return _login_headers(client, VALID_USER)


@pytest.fixture()
def other_auth_headers(client: TestClient) -> dict[str, str]:
    return _login_headers(client, OTHER_USER)


class FakeLLM:
    """Stand-in LLM provider. Records calls; returns a canned payload or raises a canned error."""

    name = "fake"

    def __init__(self, payload=None, error=None) -> None:
        self.payload, self.error, self.calls = payload, error, 0

    def generate_json(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture()
def use_llm(client: TestClient):
    """Install a fake LLM for the test: use_llm(payload=...) or use_llm(error=...)."""

    def install(payload=None, error=None) -> FakeLLM:
        fake = FakeLLM(payload, error)
        app.dependency_overrides[get_llm_provider] = lambda: fake
        return fake

    return install
