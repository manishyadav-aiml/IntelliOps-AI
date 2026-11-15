import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD_PROD = {
    "app_env": "production",
    "debug": False,
    "jwt_secret": "p" * 40,
    "database_url": "postgresql+psycopg://u:p@db:5432/x",
    "cors_origins": "https://app.example.com",
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**GOOD_PROD, **overrides})  # type: ignore[arg-type]


def test_valid_production_settings_accepted() -> None:
    assert make().is_production


@pytest.mark.parametrize(
    "override",
    [
        {"debug": True},
        {"jwt_secret": ""},
        {"jwt_secret": "short"},
        {"database_url": "sqlite:///x.db"},
        {"cors_origins": "*"},
    ],
)
def test_insecure_production_settings_rejected(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        make(**override)


def test_development_generates_ephemeral_secret() -> None:
    settings = Settings(_env_file=None, app_env="development", jwt_secret="")
    assert len(settings.jwt_secret) >= 32


def test_cors_origins_are_split() -> None:
    settings = Settings(_env_file=None, app_env="development", cors_origins="http://a.com, http://b.com")
    assert settings.cors_origins_list == ["http://a.com", "http://b.com"]


def test_managed_postgres_urls_are_normalised_to_the_psycopg_driver() -> None:
    for raw in ("postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"):
        assert make(database_url=raw).database_url == "postgresql+psycopg://u:p@host:5432/db"
