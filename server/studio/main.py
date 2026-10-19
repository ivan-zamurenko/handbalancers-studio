"""Application factory: assemble a fresh application without external I/O."""

from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from studio.auth.oauth_routes import router as oauth_router
from studio.auth.routes import router as auth_router
from studio.auth.runtime import build_oauth
from studio.health import liveness
from studio.public.routes import router as public_router
from studio.settings import Settings, load_settings
from studio.shared.http import RequestContextMiddleware, http_error, validation_error
from studio.shared.logging import configure_access_logging


def create_app(settings: Settings | Mapping[str, object] | None = None) -> FastAPI:
    validated = load_settings() if settings is None else Settings.model_validate(settings)
    app = FastAPI(title="Handbalancer's Studio")
    app.state.settings = validated
    app.state.oauth_service = build_oauth(validated)
    configure_access_logging()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_api_route("/health/live", liveness, methods=["GET"])
    app.include_router(auth_router)
    app.include_router(oauth_router)
    app.include_router(public_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"),
        name="static",
    )
    return app
