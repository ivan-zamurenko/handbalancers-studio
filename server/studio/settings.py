"""Explicit configuration with secret-safe validation diagnostics."""

import os
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, model_validator


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
    return Settings(**values)
