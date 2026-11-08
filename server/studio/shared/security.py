"""Bound request parsing before JSON allocation, retaining the public error envelope."""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from studio.shared.errors import error_response

MAX_BODY_BYTES = 64 * 1024
SECURITY_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"referrer-policy": b"no-referrer",
    b"content-security-policy": (
        b"default-src 'self'; script-src 'self'; style-src 'self'; "
        b"img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        b"base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
}


class RequestBodyLimitMiddleware:
    """Count actual chunks; Content-Length is only an early rejection hint.

    Kept local so both early and streamed failures use our JSON error contract.
    No buffering, request body logging or draining of an oversized upload.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                if not value.isdigit() or len(value) > 20:
                    await error_response(400, scope["state"]["request_id"])(scope, receive, send)
                    return
                if int(value) > MAX_BODY_BYTES:
                    await error_response(413, scope["state"]["request_id"])(scope, receive, send)
                    return
        size = 0

        async def bounded_receive() -> Message:
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > MAX_BODY_BYTES:
                    # FastAPI/Starlette's inner exception handler serializes this.
                    raise HTTPException(413)
            return message

        await self.app(scope, bounded_receive, send)
