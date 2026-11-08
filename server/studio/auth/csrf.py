"""Strict browser-origin and session-bound CSRF checks for unsafe HTTP routes."""

import re
import secrets

from fastapi import HTTPException, Request


def same_origin(request: Request) -> None:
    expected = request.app.state.settings.public_origin
    # Reject ambiguous duplicates instead of trusting whichever value is first.
    if not expected or request.headers.getlist("origin") != [expected.rstrip("/")]:
        raise HTTPException(403)


def require_csrf(request: Request, expected: str) -> None:
    values = request.headers.getlist("x-csrf-token")
    if (
        len(values) != 1
        or re.fullmatch(r"[0-9a-f]{64}", values[0]) is None
        or not secrets.compare_digest(expected, values[0])
    ):
        raise HTTPException(403)
