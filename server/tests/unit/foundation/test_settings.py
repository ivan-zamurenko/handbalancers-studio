"""Settings reject unsafe startup and keep synthetic secrets out of diagnostics."""

import importlib.util
import traceback

import pytest
from pydantic import ValidationError


def settings_type():
    assert importlib.util.find_spec("studio.settings") is not None, "Settings are not implemented"
    from studio.settings import Settings

    return Settings


@pytest.mark.parametrize("value", [None, "", "prodution", "dev", "PRODUCTION"])
def test_reject_unknown_environment(value):
    Settings = settings_type()
    with pytest.raises(ValidationError):
        Settings(**({} if value is None else {"app_env": value}))


@pytest.mark.parametrize(
    "origin,key",
    [
        (None, None),
        ("https://studio.example", None),
        ("https://studio.example", ""),
        ("https://studio.example", "   "),
        ("http://studio.example", "synthetic-key"),
        ("https://user:synthetic-password@studio.example", "synthetic-key"),
        ("https://studio.example/path", "synthetic-key"),
    ],
)
def test_production_requires_secrets(origin, key):
    Settings = settings_type()
    from studio.main import create_app

    config = {"app_env": "production", "public_origin": origin, "token_encryption_key": key}
    with pytest.raises(ValidationError):
        Settings(**config)
    with pytest.raises(ValidationError):
        create_app(config)


def test_valid_production_and_explicit_test_settings(monkeypatch):
    Settings = settings_type()
    from studio.main import create_app

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://invalid.example")
    production = Settings(
        app_env="production",
        public_origin="https://studio.example",
        token_encryption_key="synthetic-key-only",
    )
    assert create_app(production).state.settings.app_env == "production"
    assert create_app({"app_env": "test"}).state.settings.app_env == "test"
    with pytest.raises(ValidationError):
        create_app()


@pytest.mark.parametrize(
    "field",
    [
        "database_url",
        "auth_database_url",
        "worker_database_url",
        "oauth_client_secret",
        "stripe_secret_key",
        "stripe_webhook_secret",
        "token_encryption_key",
    ],
)
def test_redact_secret_values(field):
    Settings = settings_type()
    secret = "synthetic-sensitive-marker-only"
    good = Settings(app_env="test", **{field: secret})
    assert secret not in repr(good)
    assert secret not in str(good)
    assert secret not in good.model_dump_json()
    for values in (
        {"app_env": secret, field: secret},
        {"app_env": "production", field: secret},
        {"app_env": "test", field: {"password": secret}},
        {"app_env": "test", secret: secret},
    ):
        with pytest.raises(ValidationError) as failure:
            Settings(**values)
        error = failure.value
        rendered = [
            str(error),
            repr(error),
            str(error.errors()),
            error.json(),
            "".join(traceback.format_exception(error)),
        ]
        assert all(secret not in text for text in rendered)


def test_load_environment_is_explicit_and_no_dotenv(tmp_path, monkeypatch):
    Settings = settings_type()
    from studio.settings import load_settings

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APP_ENV=production\n")
    for name in ("APP_ENV", "PUBLIC_ORIGIN", "TOKEN_ENCRYPTION_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError):
        load_settings()
    monkeypatch.setenv("APP_ENV", "local-dev")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://127.0.0.1:8000")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "synthetic-env-secret")
    loaded = load_settings()
    assert isinstance(loaded, Settings)
    assert loaded.app_env == "local-dev"
    assert loaded.stripe_secret_key.get_secret_value() == "synthetic-env-secret"
    assert "synthetic-env-secret" not in repr(loaded)


def test_json_errors_and_immutable_assignment_redact_secrets():
    Settings = settings_type()
    secret = "synthetic-malformed-json-secret"
    with pytest.raises(ValidationError) as failure:
        Settings.model_validate_json('{"stripe_secret_key":"' + secret)
    error = failure.value
    assert secret not in str(error.errors())
    assert secret not in error.json()
    config = Settings(app_env="test")
    with pytest.raises(TypeError) as failure:
        config.token_encryption_key = secret
    assert secret not in str(failure.value)


def test_factory_revalidates_preconstructed_settings():
    Settings = settings_type()
    from studio.main import create_app

    invalid = Settings.model_construct(app_env="production", public_origin="http://invalid.example")
    with pytest.raises(ValidationError):
        create_app(invalid)
