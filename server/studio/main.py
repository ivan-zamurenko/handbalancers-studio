"""Application factory: assemble a fresh application without external I/O."""

from collections.abc import Mapping

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from studio.health import liveness
from studio.settings import Settings, load_settings
from studio.shared.http import RequestContextMiddleware, http_error, validation_error
from studio.shared.logging import configure_access_logging


def create_app(settings: Settings | Mapping[str, object] | None = None) -> FastAPI:
    validated = load_settings() if settings is None else Settings.model_validate(settings)
    app = FastAPI(title="Handbalancer's Studio")
    app.state.settings = validated
    configure_access_logging()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_api_route("/health/live", liveness, methods=["GET"])
    return app
