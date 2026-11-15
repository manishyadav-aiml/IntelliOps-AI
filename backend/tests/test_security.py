from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "unit-test-secret-" + "y" * 32


def test_password_is_hashed_and_verifiable() -> None:
    hashed = hash_password("Str0ngPassw0rd")
    assert hashed != "Str0ngPassw0rd"
    assert hashed.startswith("$2")
    assert verify_password("Str0ngPassw0rd", hashed)
    assert not verify_password("wrong-password1", hashed)


def test_same_password_gets_different_salts() -> None:
    assert hash_password("Str0ngPassw0rd") != hash_password("Str0ngPassw0rd")


def test_verify_password_handles_garbage_hash() -> None:
    assert verify_password("anything1", "not-a-bcrypt-hash") is False


def test_token_round_trip() -> None:
    token, expires_at = create_access_token("42", SECRET, "HS256", 5)
    payload = decode_access_token(token, SECRET, "HS256")
    assert payload["sub"] == "42"
    assert expires_at > datetime.now(UTC)


def test_expired_token_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "1", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET, "HS256")


def test_wrong_secret_and_tampering_rejected() -> None:
    token, _ = create_access_token("1", SECRET, "HS256", 5)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, "another-secret-" + "z" * 32, "HS256")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token[:-2] + "xx", SECRET, "HS256")


def test_token_without_required_claims_rejected() -> None:
    token = jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET, "HS256")


def test_unsigned_alg_none_token_rejected() -> None:
    token = jwt.encode({"sub": "1"}, key=None, algorithm="none")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET, "HS256")
