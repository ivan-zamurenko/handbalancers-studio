"""Run the public preview on this computer, without loading provider credentials.

Usage: uv run --locked python tools/serve_preview.py
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from studio.main import create_app


def create_preview_app(origin: str = "http://127.0.0.1:8000") -> FastAPI:
    """Explicit local tooling only; never read provider settings from the environment."""
    if origin not in {"http://127.0.0.1:8000", "http://127.0.0.1:8765"}:
        raise ValueError("Preview requires an owned local origin")
    app = create_app(
        {
            "app_env": "local-test" if origin.endswith(":8765") else "local-dev",
            "public_origin": origin,
        }
    )
    app.mount(
        "/_previews",
        StaticFiles(directory=Path(__file__).resolve().parent / "previews"),
        name="previews",
    )
    return app


if __name__ == "__main__":
    uvicorn.run(
        create_preview_app(),
        host="127.0.0.1",
        port=8000,
    )
