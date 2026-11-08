"""HTTP correlation and safe exception translation, independent per request."""

from uuid import uuid4

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from studio.shared.errors import error_response
from studio.shared.logging import record_access
from studio.shared.security import SECURITY_HEADERS


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only fixed input sections are exposed. Dynamic keys/indices and validator
    # messages can contain submitted values, so they never enter the response.
    sections = set()
    for error in exc.errors():
        location = error.get("loc", ())
        section = location[0] if location else None
        sections.add(
            section if section in {"body", "query", "path", "header", "cookie"} else "request"
        )
    fields = [
        {"field": section, "message_key": "errors.invalid_input"} for section in sorted(sections)
    ]
    return error_response(422, request.state.request_id, fields)


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    headers = {
        name: value
        for name, value in (exc.headers or {}).items()
        if name.lower() in {"allow", "retry-after", "www-authenticate"}
    }
    return error_response(exc.status_code, request.state.request_id, headers=headers)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool = False):
        self.app = app
        self.security_headers = dict(SECURITY_HEADERS)
        if hsts:
            self.security_headers[b"strict-transport-security"] = b"max-age=31536000"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        status = 500
        started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                status = message["status"]
                started = True
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id" and key.lower() not in self.security_headers
                ]
                headers.extend(self.security_headers.items())
                if scope.get("path", "").startswith("/api/auth/") or scope.get("path") in {
                    "/api/session",
                    "/auth/callback",
                }:
                    headers = [
                        (key, value) for key, value in headers if key.lower() != b"cache-control"
                    ]
                    headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": [*headers, (b"x-request-id", request_id.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:  # noqa: BLE001 -- HTTP boundary must redact all unexpected failures.
            if started:
                # An already-started response cannot be replaced by a 500 envelope.
                # Do not let a server print the original exception/SQL/secret text.
                raise RuntimeError("HTTP response interrupted") from None
            await error_response(500, request_id)(scope, receive, send_with_id)
        finally:
            record_access(request_id, status)
