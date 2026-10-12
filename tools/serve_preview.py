"""Run the public preview on this computer, without loading provider credentials.

Usage: uv run --locked python tools/serve_preview.py
"""

import uvicorn
from studio.main import create_app

if __name__ == "__main__":
    uvicorn.run(
        create_app({"app_env": "local-dev", "public_origin": "http://127.0.0.1:8000"}),
        host="127.0.0.1",
        port=8000,
    )
