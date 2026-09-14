"""Verified email accounts with browser-bound codes and persistent abuse limits."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from studio.db import get_db
from studio.mailer import MailUnavailable, send_verification
from studio.models import AuthRateLimit, EmailVerification, User, utcnow
from studio.schemas import EmailLogin, EmailRegistration, ProfileInput, VerificationInput
from studio.security import BrowserContext, require_csrf, require_user, rotate_session

router = APIRouter(prefix="/api/auth")
profile_router = APIRouter(prefix="/api")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5).hex()
    return f"scrypt$16384$8$5${salt}${digest}"


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        algorithm, n, r, p, salt, expected = (encoded or "").split("$")
        if algorithm != "scrypt" or (n, r, p) != ("16384", "8", "5"):
            # Only explicitly supported profiles may allocate hashing resources.
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# Unknown accounts do the same costly password work as registered accounts.
DUMMY_PASSWORD = hash_password(secrets.token_urlsafe(32))


def keyed_hash(settings, value: str) -> str:
    return hmac.new(
        settings.session_secret.get_secret_value().encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def limit(db, settings, key: str, maximum: int, seconds: int = 900):
    """Atomic PostgreSQL counters prevent parallel requests bypassing the budget."""
    now = utcnow()
    key_hash = keyed_hash(settings, "rate:" + key)
    db.execute(
        insert(AuthRateLimit)
        .values(key_hash=key_hash, attempts=0, window_start=now)
        .on_conflict_do_nothing()
    )
    row = db.scalar(
        select(AuthRateLimit).where(AuthRateLimit.key_hash == key_hash).with_for_update()
    )
    if row.window_start + timedelta(seconds=seconds) <= now:
        row.attempts, row.window_start = 0, now
    row.attempts += 1
    blocked = row.attempts > maximum
    db.commit()
    if blocked:
        raise HTTPException(
            429, "Too many attempts. Try again later", headers={"Retry-After": str(seconds)}
        )


def request_limits(request, db, email: str, action: str):
    settings = request.app.state.settings
    # Never trust forwarding headers from a public client.
    peer = request.client.host if request.client else "unknown"
    limit(db, settings, f"{action}:ip:{peer}", 30)
    limit(db, settings, f"{action}:email:{email}", 5 if action == "register" else 10)


@router.post("/register")
def register(
    body: EmailRegistration,
    request: Request,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if context.user:
        raise HTTPException(409, "Already signed in")
    settings = request.app.state.settings
    request_limits(request, db, body.email, "register")
    encoded = hash_password(body.password)
    existing = db.scalar(
        select(User).where(func.lower(User.email) == body.email, User.is_demo.is_(False))
    )
    pending = db.get(EmailVerification, context.row.token_hash)
    if pending:
        db.delete(pending)
        db.flush()
    if existing:
        db.commit()
        # Same response for known addresses; never overwrite an existing account.
        return {"verification_required": True}
    code = f"{secrets.randbelow(1_000_000):06d}"
    pending = EmailVerification(
        session_hash=context.row.token_hash,
        email=body.email,
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        password_hash=encoded,
        code_hash=keyed_hash(settings, context.row.token_hash + ":" + code),
        expires_at=utcnow() + timedelta(minutes=10),
        attempts=0,
    )
    db.add(pending)
    try:
        send_verification(settings, body.email, code)
    except MailUnavailable:
        db.rollback()
        raise HTTPException(503, "Email delivery is unavailable. Please try again later") from None
    db.commit()
    return {"verification_required": True}


@router.post("/verify")
def verify(
    body: VerificationInput,
    request: Request,
    response: Response,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    settings = request.app.state.settings
    limit(db, settings, "verify:" + context.row.token_hash, 10)
    pending = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.session_hash == context.row.token_hash)
        .with_for_update()
    )
    if not pending or pending.expires_at <= utcnow() or pending.attempts >= 5:
        raise HTTPException(400, "Code expired or invalid. Request a new code")
    supplied = keyed_hash(settings, context.row.token_hash + ":" + body.code)
    if not hmac.compare_digest(supplied, pending.code_hash):
        pending.attempts += 1
        db.commit()
        raise HTTPException(400, "Code expired or invalid. Request a new code")
    user = User(
        name=f"{pending.first_name} {pending.last_name}",
        first_name=pending.first_name,
        last_name=pending.last_name,
        email=pending.email,
        password_hash=pending.password_hash,
        email_verified_at=utcnow(),
        is_demo=False,
    )
    db.add(user)
    url = "/checkout" if context.row.selected_plan else "/plans"
    try:
        db.flush()
        rotate_session(db, context.row, user, response, settings)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Unable to complete registration. Try signing in") from None
    return {"url": url}


@router.post("/login")
def login(
    body: EmailLogin,
    request: Request,
    response: Response,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    request_limits(request, db, body.email, "login")
    user = db.scalar(
        select(User).where(func.lower(User.email) == body.email, User.is_demo.is_(False))
    )
    valid = verify_password(
        body.password, user.password_hash if user and user.password_hash else DUMMY_PASSWORD
    )
    if not valid or not user or not user.password_hash or not user.email_verified_at:
        raise HTTPException(401, "Email or password is incorrect")
    url = "/dashboard"
    rotate_session(db, context.row, user, response, request.app.state.settings)
    return {"url": url}


@profile_router.patch("/profile")
def update_profile(
    body: ProfileInput,
    context: BrowserContext = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = context.user
    user.first_name, user.last_name = body.first_name, body.last_name
    user.name = f"{body.first_name} {body.last_name}"
    db.commit()
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "name": user.name,
        "email": user.email,
    }
