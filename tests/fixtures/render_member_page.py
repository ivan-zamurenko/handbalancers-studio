"""Render real cabinet templates for browser layout tests; no fake auth in runtime."""

import sys

from starlette.requests import Request
from studio.main import create_app
from studio.public.routes import render

path, language = sys.argv[1:]
assert path in {"/dashboard", "/progress", "/profile"} and language in {"uk", "en"}
app = create_app({"app_env": "test", "public_origin": "http://127.0.0.1:8765"})
request = Request(
    {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": f"lang={language}".encode(),
        "headers": [],
        "scheme": "http",
        "server": ("127.0.0.1", 8765),
        "app": app,
    }
)
print(render(request, f"member/{path[1:]}.html").body.decode())
