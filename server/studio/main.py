"""Application factory: assemble a fresh application without external I/O."""

import base64
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from studio.accounts.onboarding_routes import router as onboarding_router
from studio.accounts.routes import router as accounts_router
from studio.auth.oauth_routes import router as oauth_router
from studio.auth.recovery_routes import router as recovery_router
from studio.auth.routes import router as auth_router
from studio.auth.runtime import build_oauth
from studio.auth.token_store import TokenCipher
from studio.auth.verification_routes import router as verification_router
from studio.billing.routes import router as billing_router
from studio.billing.runtime import build_checkout
from studio.billing.webhooks import WebhookInbox
from studio.billing.webhooks import router as webhook_router
from studio.db import web_transaction_factory
from studio.health import liveness
from studio.public.routes import router as public_router
from studio.settings import Settings, load_settings
from studio.shared.http import RequestContextMiddleware, http_error, validation_error
from studio.shared.logging import configure_access_logging
from studio.shared.security import RequestBodyLimitMiddleware


def create_app(settings: Settings | Mapping[str, object] | None = None) -> FastAPI:
    validated = load_settings() if settings is None else Settings.model_validate(settings)
    deployed = validated.app_env in {"production", "staging"}
    # CDN/inline Swagger and ReDoc conflict with the product's strict CSP.
    # Keep /openapi.json for local API tools only.
    app = FastAPI(
        title="Handbalancer's Studio",
        docs_url=None,
        redoc_url=None,
        openapi_url=None if deployed else "/openapi.json",
    )
    app.state.settings = validated
    app.state.oauth_service = build_oauth(validated)
    app.state.verification_service = (
        app.state.oauth_service if validated.auth_email_enabled else None
    )
    if validated.auth_email_enabled and app.state.oauth_service is not None:
        app.state.auth_gateway = app.state.oauth_service.gateway
    app.state.web_transaction = web_transaction_factory(validated)
    app.state.checkout_service = build_checkout(validated, app.state.web_transaction)
    if app.state.checkout_service is not None:
        assert validated.stripe_webhook_secret and validated.token_encryption_key
        cipher = TokenCipher(
            "billing-v1",
            {
                "billing-v1": base64.b64decode(
                    validated.token_encryption_key.get_secret_value(), validate=True
                )
            },
        )
        app.state.webhook_inbox = WebhookInbox(
            app.state.checkout_service.transaction, validated.stripe_webhook_secret, cipher
        )
    configure_access_logging()
    if deployed:
        assert validated.public_origin
        hostname = urlsplit(validated.public_origin).hostname
        assert hostname
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[hostname],
            www_redirect=False,
        )
    app.add_middleware(RequestBodyLimitMiddleware)
    app.add_middleware(
        RequestContextMiddleware,
        hsts=deployed,
    )
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_api_route("/health/live", liveness, methods=["GET"])
    app.include_router(auth_router)
    app.include_router(verification_router)
    app.include_router(recovery_router)
    app.include_router(oauth_router)
    app.include_router(webhook_router)
    app.include_router(billing_router)
    app.include_router(accounts_router)
    app.include_router(onboarding_router)
    app.include_router(public_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"),
        name="static",
    )
    return app
