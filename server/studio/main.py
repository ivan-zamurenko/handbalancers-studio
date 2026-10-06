"""Application factory: assemble a fresh application without external I/O."""

from collections.abc import Mapping
from copy import deepcopy

from fastapi import FastAPI

from studio.health import liveness


def create_app(settings: Mapping[str, object] | None = None) -> FastAPI:
    app = FastAPI(title="Handbalancer's Studio")
    # Typed environment validation is introduced in S00-04.
    app.state.settings = deepcopy(dict(settings)) if settings is not None else {}
    app.add_api_route("/health/live", liveness, methods=["GET"])
    return app
