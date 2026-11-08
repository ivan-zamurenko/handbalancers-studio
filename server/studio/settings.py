"""Explicit configuration with secret-safe validation diagnostics."""

import base64
import os
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always", hide_input_in_errors=True
    )

    app_env: Literal["local-dev", "local-test", "test", "staging", "production"]
    public_origin: str | None = None
    token_encryption_key: SecretStr | None = None
    database_url: SecretStr | None = None
    auth_database_url: SecretStr | None = None
    worker_database_url: SecretStr | None = None
    oauth_client_secret: SecretStr | None = None
    supabase_url: str | None = None
    supabase_publishable_key: SecretStr | None = None
    auth_email_enabled: bool = False
    auth_client_attempts_per_minute: int = Field(default=10, ge=1, le=10)
    auth_account_attempts_per_minute: int = Field(default=10, ge=1, le=10)
    oauth_google_enabled: bool = False
    oauth_apple_enabled: bool = False
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None

    @model_validator(mode="wrap")
    @classmethod
    def validate_safely(cls, data, handler) -> Self:
        try:
            settings = handler(data)
            if settings.public_origin is not None:
                origin = urlsplit(settings.public_origin)
                if (
                    origin.scheme not in {"http", "https"}
                    or not origin.hostname
                    or origin.username is not None
                    or origin.password is not None
                    or origin.path not in {"", "/"}
                    or origin.query
                    or origin.fragment
                    or any(char.isspace() for char in settings.public_origin)
                ):
                    raise ValueError("Invalid origin")
                # Accessing port also checks that it is numeric and in range.
                _ = origin.port
            if settings.app_env in {"staging", "production"} and (
                settings.public_origin is None
                or urlsplit(settings.public_origin).scheme != "https"
                or settings.token_encryption_key is None
                or not settings.token_encryption_key.get_secret_value().strip()
            ):
                raise ValueError("Deployment requires HTTPS origin and encryption key")
            if (
                settings.auth_email_enabled
                or settings.oauth_google_enabled
                or settings.oauth_apple_enabled
            ):
                if not all(
                    (
                        settings.public_origin,
                        settings.supabase_url,
                        settings.supabase_publishable_key,
                        settings.auth_database_url,
                        settings.token_encryption_key,
                    )
                ):
                    raise ValueError("OAuth configuration incomplete")
                provider = urlsplit(settings.supabase_url)
                if (
                    provider.scheme not in {"https", "http"}
                    or not provider.hostname
                    or provider.username
                    or provider.password
                    or provider.query
                    or provider.fragment
                    or provider.path not in {"", "/"}
                    or (
                        provider.scheme == "http"
                        and (
                            settings.app_env in {"staging", "production"}
                            or provider.hostname not in {"127.0.0.1", "localhost"}
                        )
                    )
                ):
                    raise ValueError("Invalid provider origin")
                from sqlalchemy.engine import make_url
                from sqlalchemy.exc import ArgumentError

                try:
                    database = make_url(settings.auth_database_url.get_secret_value())
                    if database.drivername != "postgresql+psycopg" or not database.database:
                        raise ValueError("Invalid auth database")
                    if (
                        settings.app_env in {"staging", "production"}
                        and database.query.get("sslmode") != "verify-full"
                    ):
                        raise ValueError("Deployment requires verified database TLS")
                except ArgumentError:
                    raise ValueError("Invalid auth database") from None
                key = base64.b64decode(
                    settings.token_encryption_key.get_secret_value(), validate=True
                )
                if len(key) != 32:
                    raise ValueError("Invalid encryption key")
            return settings
        except (ValidationError, ValueError):
            # hide_input_in_errors alone does not protect errors()/json(). Rebuild
            # the error without raw inputs, unknown field names or exception context.
            raise _safe_validation_error() from None

    @classmethod
    def model_validate_json(cls, json_data, **kwargs) -> Self:
        # Invalid JSON fails before model validators and can include the full input.
        try:
            return super().model_validate_json(json_data, **kwargs)
        except ValidationError:
            raise _safe_validation_error() from None

    def __setattr__(self, name: str, value: object) -> None:
        # Pydantic's default frozen-instance error includes the attempted raw value.
        raise TypeError("Settings are immutable; construct a validated replacement")


def _safe_validation_error() -> ValidationError:
    return ValidationError.from_exception_data(
        "Settings",
        [
            {
                "type": "value_error",
                "loc": (),
                "input": "[redacted]",
                "ctx": {
                    "error": ValueError(
                        "Invalid settings: check APP_ENV, PUBLIC_ORIGIN and secret fields"
                    )
                },
            }
        ],
        hide_input=True,
    )


def load_settings() -> Settings:
    """Read only declared environment names; never implicitly read a .env file."""
    values = {
        name: os.environ[name.upper()]
        for name in Settings.model_fields
        if name.upper() in os.environ
    }
    # Empty optional env-example fields mean unset, not a usable credential.
    values = {name: value for name, value in values.items() if value != "" or name == "app_env"}
    return Settings.model_validate(values)
