"""Provider identities use verified issuer + subject, never automatic email linking."""

import hmac
import secrets
from datetime import timedelta
from typing import Literal

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebToken
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse

from studio.db import get_db
from studio.models import BrowserSession, Identity, OAuthAttempt, User, utcnow
from studio.security import (
    OAUTH_COOKIE,
    BrowserContext,
    get_browser,
    rotate_session,
    token_hash,
)
from studio.settings import Settings

router = APIRouter(prefix="/auth")
Provider = Literal["google", "apple"]
PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "jwks": "https://www.googleapis.com/oauth2/v3/certs",
        "issuers": ["https://accounts.google.com", "accounts.google.com"],
        "scope": "openid email profile",
    },
    "apple": {
        "authorize": "https://appleid.apple.com/auth/authorize",
        "token": "https://appleid.apple.com/auth/token",
        "jwks": "https://appleid.apple.com/auth/keys",
        "issuers": ["https://appleid.apple.com"],
        "scope": "openid email name",
    },
}


def oauth_client(settings: Settings, provider: str):
    return AsyncOAuth2Client(
        client_id=getattr(settings, f"{provider}_client_id"),
        client_secret=getattr(settings, f"{provider}_client_secret").get_secret_value(),
        redirect_uri=f"{settings.base_url}/auth/{provider}/callback",
        scope=PROVIDERS[provider]["scope"],
        token_endpoint_auth_method="client_secret_post",
        code_challenge_method="S256" if provider == "google" else None,
        timeout=15,
        follow_redirects=False,
    )


@router.get("/{provider}/login")
def login(
    provider: Provider,
    request: Request,
    response: Response,
    context: BrowserContext = Depends(get_browser),
    db: Session = Depends(get_db),
):
    settings = request.app.state.settings
    if not settings.providers[provider]:
        return RedirectResponse("/register?auth_error=unavailable", status_code=303)
    if context.user:
        return RedirectResponse("/dashboard", status_code=303)
    state, browser, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
    attempt = OAuthAttempt(
        state_hash=token_hash(state),
        session_hash=context.row.token_hash,
        browser_hash=token_hash(browser),
        provider=provider,
        nonce=nonce,
        code_verifier=verifier,
        expires_at=utcnow() + timedelta(minutes=10),
    )
    db.add(attempt)
    db.commit()
    # URL construction is local; no token, secret or user data is sent before navigation.
    client = oauth_client(settings, provider)
    extra = {"response_mode": "form_post"} if provider == "apple" else {}
    url, _ = client.create_authorization_url(
        PROVIDERS[provider]["authorize"], state=state, nonce=nonce, code_verifier=verifier, **extra
    )
    redirect = RedirectResponse(url, status_code=303)
    # Apple returns a cross-site POST, so its short-lived correlation cookie needs SameSite=None.
    redirect.set_cookie(
        OAUTH_COOKIE,
        browser,
        httponly=True,
        max_age=600,
        path="/auth",
        secure=settings.secure_cookies,
        samesite="none" if provider == "apple" else "lax",
    )
    for cookie in response.raw_headers:
        if cookie[0].lower() == b"set-cookie":
            redirect.raw_headers.append(cookie)
    return redirect


def consume_attempt(factory, provider: str, state: str, browser: str):
    if not 32 <= len(state) <= 128 or not 32 <= len(browser) <= 128:
        raise ValueError("Invalid OAuth correlation")
    with factory() as db:
        attempt = db.get(OAuthAttempt, token_hash(state), with_for_update=True)
        if (
            not attempt
            or attempt.provider != provider
            or attempt.consumed_at
            or attempt.expires_at <= utcnow()
            or not hmac.compare_digest(attempt.browser_hash, token_hash(browser))
        ):
            raise ValueError("Invalid OAuth correlation")
        attempt.consumed_at = utcnow()
        db.commit()
        return {
            "session_hash": attempt.session_hash,
            "nonce": attempt.nonce,
            "code_verifier": attempt.code_verifier,
        }


async def verified_claims(settings: Settings, provider: str, code: str, attempt: dict):
    async with oauth_client(settings, provider) as client:
        extra = {"code_verifier": attempt["code_verifier"]} if provider == "google" else {}
        token = await client.fetch_token(
            PROVIDERS[provider]["token"], code=code, grant_type="authorization_code", **extra
        )
    # Keys are fetched only from a hardcoded provider endpoint, never from token header URLs.
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        response = await client.get(PROVIDERS[provider]["jwks"])
        response.raise_for_status()
        keys = response.json()
    return validate_id_token(token["id_token"], keys, settings, provider, attempt["nonce"])


def validate_id_token(encoded, keys, settings, provider, nonce):
    client_id = getattr(settings, f"{provider}_client_id")
    claims = JsonWebToken(["RS256"]).decode(
        encoded,
        keys,
        claims_options={
            "iss": {"essential": True, "values": PROVIDERS[provider]["issuers"]},
            "aud": {"essential": True, "value": client_id},
            "sub": {"essential": True},
            "exp": {"essential": True},
            "iat": {"essential": True},
            "nonce": {"essential": True, "value": nonce},
        },
    )
    claims.validate(leeway=60)
    if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and not claims.get("azp"):
        raise ValueError("Missing authorized party")
    if claims.get("azp") and claims["azp"] != client_id:
        raise ValueError("Invalid authorized party")
    if not isinstance(claims["sub"], str) or not 1 <= len(claims["sub"]) <= 255:
        raise ValueError("Invalid provider subject")
    return dict(claims)


def finish_login(factory, settings, provider, attempt, claims, response):
    with factory() as db:
        old = db.get(BrowserSession, attempt["session_hash"], with_for_update=True)
        if not old or old.expires_at <= utcnow() or old.user_id:
            raise ValueError("Expired or already used login session")
        identity = db.scalar(
            select(Identity).where(Identity.provider == provider, Identity.subject == claims["sub"])
        )
        if identity:
            user = db.get(User, identity.user_id)
        else:
            email = claims.get("email") if claims.get("email_verified") in {True, "true"} else None
            if not isinstance(email, str) or len(email) > 320:
                email = None
            # Display name is never used as an authorization or account-linking identifier.
            name = str(claims.get("name") or "Handbalancer")[:100]
            user = User(name=name, email=email, is_demo=False)
            db.add(user)
            db.flush()
            db.add(Identity(user_id=user.id, provider=provider, subject=claims["sub"]))
            db.flush()
        rotate_session(db, old, user, response, settings)


@router.api_route("/{provider}/callback", methods=["GET", "POST"])
async def callback(provider: Provider, request: Request):
    settings = request.app.state.settings
    response = RedirectResponse("/plans", status_code=303)
    response.delete_cookie(OAUTH_COOKIE, path="/auth", secure=settings.secure_cookies)
    if not settings.providers[provider]:
        return RedirectResponse("/register?auth_error=unavailable", status_code=303)
    try:
        params = await request.form() if request.method == "POST" else request.query_params
        state, code = str(params.get("state", "")), str(params.get("code", ""))
        if not code or len(code) > 4096 or params.get("error"):
            raise ValueError("Provider did not return an authorization code")
        attempt = await run_in_threadpool(
            consume_attempt,
            request.app.state.session_factory,
            provider,
            state,
            request.cookies.get(OAUTH_COOKIE, ""),
        )
        claims = await verified_claims(settings, provider, code, attempt)
        await run_in_threadpool(
            finish_login,
            request.app.state.session_factory,
            settings,
            provider,
            attempt,
            claims,
            response,
        )
    except (ValueError, KeyError, httpx.HTTPError, IntegrityError):
        return RedirectResponse("/register?auth_error=failed", status_code=303)
    except Exception:
        # OAuth libraries can include returned tokens in exception messages: never expose them.
        return RedirectResponse("/register?auth_error=failed", status_code=303)
    return response
