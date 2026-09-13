"""Opaque, revocable sessions and same-origin CSRF protection."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from studio.db import get_db
from studio.models import BrowserSession, OnboardingProfile, User, utcnow
from studio.schemas import onboarding_view
from studio.settings import LOOPBACK_HOSTS, Settings

SESSION_COOKIE = "studio_session"
OAUTH_COOKIE = "studio_oauth"
SESSION_SECONDS = 7 * 24 * 60 * 60


def token_hash(value: str) -> str:
    # A 256-bit random token has sufficient entropy for an unkeyed one-way digest.
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_token(raw: str, settings: Settings) -> str:
    return hmac.new(
        settings.session_secret.get_secret_value().encode(),
        ("csrf:" + raw).encode(),
        hashlib.sha256,
    ).hexdigest()


@dataclass
class BrowserContext:
    raw: str
    row: BrowserSession
    user: User | None


def set_session_cookie(response: Response, raw: str, settings: Settings):
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def get_browser(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    raw = request.cookies.get(SESSION_COOKIE, "")
    row = db.get(BrowserSession, token_hash(raw)) if 32 <= len(raw) <= 128 else None
    if row is not None and row.expires_at <= utcnow():
        db.delete(row)
        db.commit()
        row = None
    if row is None:
        if request.method != "GET":
            raise HTTPException(403, "Refresh the page before trying again")
        raw = secrets.token_urlsafe(32)
        row = BrowserSession(
            token_hash=token_hash(raw), expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS)
        )
        db.add(row)
        db.commit()
        set_session_cookie(response, raw, settings)
    user = db.get(User, row.user_id) if row.user_id else None
    if user and user.is_demo and not settings.preview_enabled:
        raise HTTPException(401, "This local demo account is unavailable in this environment")
    return BrowserContext(raw=raw, row=row, user=user)


def require_csrf(request: Request, context: BrowserContext = Depends(get_browser)):
    expected_origin = request.app.state.settings.base_url
    if request.headers.get("origin") != expected_origin:
        raise HTTPException(403, "Request origin is not allowed")
    supplied = request.headers.get("x-csrf-token", "")
    expected = csrf_token(context.raw, request.app.state.settings)
    if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("ascii")):
        raise HTTPException(403, "Refresh the page before trying again")
    return context


def require_user(context: BrowserContext = Depends(require_csrf)):
    if context.user is None:
        raise HTTPException(401, "Sign in to continue")
    return context


def require_local_preview(request: Request):
    settings = request.app.state.settings
    peer = request.client.host if request.client else ""
    host = urlsplit(str(request.url)).hostname
    if not settings.preview_enabled or peer not in LOOPBACK_HOSTS or host not in LOOPBACK_HOSTS:
        raise HTTPException(404, "Not found")


def rotate_session(
    db: Session, old: BrowserSession, user: User, response: Response, settings: Settings
):
    """Merge only the browser-bound draft, then invalidate the pre-login session."""
    if old.draft:
        profile = db.get(OnboardingProfile, user.id)
        if profile:
            profile.answers = old.draft
            profile.schema_version = 2 if "minutes_plus" in old.draft else 1
            profile.updated_at = utcnow()
        else:
            db.add(
                OnboardingProfile(
                    user_id=user.id,
                    answers=old.draft,
                    schema_version=2 if "minutes_plus" in old.draft else 1,
                )
            )
    raw = secrets.token_urlsafe(32)
    db.add(
        BrowserSession(
            token_hash=token_hash(raw),
            user_id=user.id,
            expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS),
        )
    )
    db.execute(delete(BrowserSession).where(BrowserSession.token_hash == old.token_hash))
    db.commit()
    set_session_cookie(response, raw, settings)


def onboarding_for(db: Session, context: BrowserContext):
    if context.user:
        profile = db.scalar(
            select(OnboardingProfile).where(OnboardingProfile.user_id == context.user.id)
        )
        return onboarding_view(profile.answers) if profile else None
    return onboarding_view(context.row.draft)
