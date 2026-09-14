"""Environment configuration. Secret values are never included in repr or API responses."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

SERVER_DIR = Path(__file__).resolve().parent.parent
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr = Field(repr=False)
    session_secret: SecretStr = Field(repr=False)
    app_env: Literal["development", "test", "production"] = "production"
    local_preview: bool = False
    base_url: str = "http://127.0.0.1:8000"
    google_client_id: str = ""
    google_client_secret: SecretStr = Field(default=SecretStr(""), repr=False)
    apple_client_id: str = ""
    apple_client_secret: SecretStr = Field(default=SecretStr(""), repr=False)
    stripe_secret_key: SecretStr = Field(default=SecretStr(""), repr=False)
    stripe_webhook_secret: SecretStr = Field(default=SecretStr(""), repr=False)
    stripe_price_essential: str = ""
    stripe_price_plus: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_plus: str = ""
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = Field(default=SecretStr(""), repr=False)
    smtp_from: str = ""

    @model_validator(mode="after")
    def safe_configuration(self):
        try:
            driver = make_url(self.database_url.get_secret_value()).drivername
        except Exception:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if driver != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        if len(self.session_secret.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET requires at least 32 characters")
        origin = urlsplit(self.base_url)
        if (
            origin.scheme not in {"https", "http"}
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.query
            or origin.fragment
            or origin.path not in {"", "/"}
        ):
            raise ValueError("BASE_URL must be an HTTP(S) origin without credentials or a path")
        self.base_url = self.base_url.rstrip("/")
        if self.app_env == "production":
            if origin.scheme != "https" or origin.hostname in LOOPBACK_HOSTS:
                raise ValueError("Production requires an HTTPS domain BASE_URL")
            if self.local_preview:
                raise ValueError("LOCAL_PREVIEW is forbidden in production")
        if self.local_preview and origin.hostname not in LOOPBACK_HOSTS:
            raise ValueError("LOCAL_PREVIEW requires a loopback BASE_URL")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.base_url.startswith("https://")

    @property
    def preview_enabled(self) -> bool:
        return self.local_preview and self.app_env == "development"

    @property
    def providers(self) -> dict[str, bool]:
        return {
            "google": bool(self.google_client_id and self.google_client_secret.get_secret_value()),
            "apple": bool(
                self.secure_cookies
                and self.apple_client_id
                and self.apple_client_secret.get_secret_value()
            ),
        }

    @property
    def stripe_prices(self) -> dict[str, str]:
        return {
            "essential": self.stripe_price_essential,
            "plus": self.stripe_price_plus,
            "pro": self.stripe_price_pro,
            "pro_plus": self.stripe_price_pro_plus,
        }

    @property
    def payments_enabled(self) -> bool:
        return bool(
            self.stripe_secret_key.get_secret_value()
            and self.stripe_webhook_secret.get_secret_value()
            and all(self.stripe_prices.values())
        )
