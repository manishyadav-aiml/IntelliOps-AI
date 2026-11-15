from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from tests.conftest import VALID_USER

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


def login(client: TestClient, password: str = VALID_USER["password"]):
    return client.post(LOGIN, json={"email": VALID_USER["email"], "password": password})


def test_register_success_hides_password_hash(client: TestClient, db_session: Session) -> None:
    response = client.post(REGISTER, json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_USER["email"]
    assert "password" not in body and "hashed_password" not in body
    stored = db_session.scalar(select(User))
    assert stored is not None
    assert stored.hashed_password != VALID_USER["password"]
    assert stored.hashed_password.startswith("$2")


def test_register_normalises_email_case(client: TestClient) -> None:
    client.post(REGISTER, json={**VALID_USER, "email": "Ada@Example.com"})
    assert login(client).status_code == 200


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    assert client.post(REGISTER, json=VALID_USER).status_code == 201
    response = client.post(REGISTER, json={**VALID_USER, "email": "ADA@example.com"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(REGISTER, json={**VALID_USER, "email": "not-an-email"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_register_rejects_weak_passwords_without_echoing_them(client: TestClient) -> None:
    for weak in ["short1", "onlyletterslong", "123456789012"]:
        response = client.post(REGISTER, json={**VALID_USER, "password": weak})
        assert response.status_code == 422
        assert weak not in response.text


def test_login_success_returns_token_and_user(client: TestClient) -> None:
    client.post(REGISTER, json=VALID_USER)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == VALID_USER["email"]
    assert "hashed_password" not in body["user"]


def test_login_wrong_password_and_unknown_user_look_identical(client: TestClient) -> None:
    client.post(REGISTER, json=VALID_USER)
    wrong_pw = login(client, "Wr0ngPassword99")
    unknown = client.post(LOGIN, json={"email": "nobody@example.com", "password": "Wr0ngPassword99"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_me_requires_valid_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer garbage"}).status_code == 401
    ok = client.get(ME, headers=auth_headers)
    assert ok.status_code == 200
    assert ok.json()["email"] == VALID_USER["email"]


def test_token_of_deleted_or_inactive_user_rejected(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    user = db_session.scalar(select(User))
    user.is_active = False
    db_session.commit()
    assert client.get(ME, headers=auth_headers).status_code == 401


def test_inactive_user_cannot_login(client: TestClient, db_session: Session) -> None:
    client.post(REGISTER, json=VALID_USER)
    user = db_session.scalar(select(User))
    user.is_active = False
    db_session.commit()
    assert login(client).status_code == 401


def test_logout_requires_auth_and_writes_audit_entry(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    assert client.post(LOGOUT).status_code == 401
    assert client.post(LOGOUT, headers=auth_headers).status_code == 204
    actions = set(db_session.scalars(select(AuditLog.action)))
    assert {"user.registered", "auth.login.success", "auth.logout"} <= actions


def test_failed_login_is_audited_without_secrets(client: TestClient, db_session: Session) -> None:
    client.post(REGISTER, json=VALID_USER)
    login(client, "Wr0ngPassword99")
    entry = db_session.scalar(select(AuditLog).where(AuditLog.action == "auth.login.failed"))
    assert entry is not None
    assert "Wr0ngPassword99" not in str(entry.details)


def test_login_rate_limit_returns_429_with_retry_after(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        app_env="testing",
        jwt_secret="t" * 40,
        login_rate_limit_attempts=3,
    )
    statuses = [login(client, "Wr0ngPassword99") for _ in range(5)]
    assert [r.status_code for r in statuses[:3]] == [401, 401, 401]
    assert statuses[3].status_code == 429
    assert statuses[3].json()["error"]["code"] == "rate_limited"
    assert int(statuses[3].headers["Retry-After"]) >= 1
