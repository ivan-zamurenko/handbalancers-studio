"""Stable public errors contain translation keys, never exception messages."""

from starlette.responses import JSONResponse

HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    402: "payment_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "content_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(status: int, request_id: str, field_errors=None, headers=None) -> JSONResponse:
    code = HTTP_CODES.get(status, "http_error")
    key = {422: "errors.validation", 500: "errors.internal"}.get(status, f"errors.{code}")
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message_key": key,
                "field_errors": field_errors or [],
                "request_id": request_id,
            }
        },
        status_code=status,
        headers={**(headers or {}), "Cache-Control": "no-store"},
    )
