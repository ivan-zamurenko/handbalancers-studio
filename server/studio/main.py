"""Application factory: assemble a fresh application without external I/O."""

from collections.abc import Mapping

from fastapi import FastAPI

from studio.health import liveness
from studio.settings import Settings, load_settings


def create_app(settings: Settings | Mapping[str, object] | None = None) -> FastAPI:
    validated = load_settings() if settings is None else Settings.model_validate(settings)
    app = FastAPI(title="Handbalancer's Studio")
    app.state.settings = validated
    app.add_api_route("/health/live", liveness, methods=["GET"])
    return app
