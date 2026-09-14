"""HTTP contracts; database writes remain scoped to the browser's authenticated owner."""

import math
from datetime import timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import Field, StrictInt
from sqlalchemy import delete
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from studio.billing import (
    BillingUnavailable,
    StripeGateway,
    active_subscription,
    apply_webhook,
    begin_checkout,
    demo_payment,
)
from studio.db import get_db
from studio.models import (
    BrowserSession,
    EmailVerification,
    OnboardingProfile,
    Subscription,
    TrainingSession,
    User,
    utcnow,
)
from studio.plans import public_plans
from studio.progress import dashboard_progress
from studio.schemas import CheckoutInput, Goal, OnboardingInput, PreviewRegistration, StrictBody
from studio.security import (
    SESSION_COOKIE,
    BrowserContext,
    csrf_token,
    get_browser,
    onboarding_for,
    require_csrf,
    require_local_preview,
    require_user,
    rotate_session,
)

router = APIRouter(prefix="/api")


@router.get("/session")
def session_state(
    request: Request, context: BrowserContext = Depends(get_browser), db: Session = Depends(get_db)
):
    settings = request.app.state.settings
    user = context.user
    subscription = db.get(Subscription, user.id) if user else None
    membership = None
    if subscription:
        membership = {
            "plan_id": subscription.plan_id,
            "is_demo": subscription.is_demo,
            "current_period_end": subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "indicator": "inactive"
            if not active_subscription(subscription, allow_demo=settings.preview_enabled)
            else (
                "ending"
                if subscription.current_period_end <= utcnow() + timedelta(days=5)
                else "active"
            ),
            "days_remaining": max(
                0, math.ceil((subscription.current_period_end - utcnow()).total_seconds() / 86400)
            )
            if subscription.current_period_end
            else 0,
            "status": subscription.status
            if active_subscription(subscription, allow_demo=settings.preview_enabled)
            else (
                "expired" if subscription.status in {"active", "trialing"} else subscription.status
            ),
        }
    settings = request.app.state.settings
    pending_verification = db.get(EmailVerification, context.row.token_hash) if not user else None
    return {
        "csrf_token": csrf_token(context.raw, settings),
        "user": {
            "id": str(user.id),
            "name": user.name,
            "first_name": user.first_name or user.name,
            "last_name": user.last_name or "",
            "email": user.email,
            "is_demo": user.is_demo,
            "email_verified": bool(user.email_verified_at),
        }
        if user
        else None,
        "selected_plan": context.row.selected_plan,
        "verification_pending": bool(
            pending_verification
            and pending_verification.expires_at > utcnow()
            and pending_verification.attempts < 5
        ),
        "trial_eligible": not user or user.trial_used_at is None,
        "progress": dashboard_progress(db, user, onboarding_for(db, context)) if user else None,
        "email_auth_enabled": settings.preview_enabled
        or bool(settings.smtp_host and settings.smtp_from),
        "onboarding": onboarding_for(db, context),
        "subscription": membership,
        "providers": settings.providers,
        "payments_enabled": settings.payments_enabled,
        "local_preview": settings.preview_enabled,
    }


@router.post("/onboarding")
def save_onboarding(
    body: OnboardingInput,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    answers = body.model_dump()
    if context.user:
        profile = db.get(OnboardingProfile, context.user.id)
        if profile:
            profile.answers, profile.updated_at = answers, utcnow()
            profile.schema_version = 2
        else:
            db.add(OnboardingProfile(user_id=context.user.id, answers=answers, schema_version=2))
    else:
        context.row.draft = answers
    db.commit()
    return {"onboarding": answers}


@router.get("/plans")
def plans():
    return {"plans": public_plans()}


@router.post("/preview/register", dependencies=[Depends(require_local_preview)])
def preview_register(
    body: PreviewRegistration,
    request: Request,
    response: Response,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    if context.user:
        raise HTTPException(409, "You are already signed in")
    if not context.row.draft:
        raise HTTPException(409, "Complete onboarding before creating the demo account")
    user = User(name=body.name, is_demo=True, email=None)
    db.add(user)
    db.flush()
    rotate_session(db, context.row, user, response, request.app.state.settings)
    return {"url": "/plans"}


@router.post("/checkout")
def checkout(
    body: CheckoutInput,
    request: Request,
    context: BrowserContext = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not onboarding_for(db, context):
        raise HTTPException(409, "Complete onboarding first")
    settings = request.app.state.settings
    return {
        "url": begin_checkout(db, settings, context.user, body.plan_id, StripeGateway(settings))
    }


@router.post("/preview/pay", dependencies=[Depends(require_local_preview)])
def preview_pay(
    body: CheckoutInput,
    context: BrowserContext = Depends(require_user),
    db: Session = Depends(get_db),
):
    demo_payment(db, context.user, body.plan_id)
    return {"url": "/dashboard"}


@router.post("/plan")
def select_plan(
    body: CheckoutInput,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    context.row.selected_plan = body.plan_id
    db.commit()
    return {"plan_id": body.plan_id}


def require_membership(
    request: Request, context: BrowserContext = Depends(require_user), db: Session = Depends(get_db)
):
    if not active_subscription(
        db.get(Subscription, context.user.id), allow_demo=request.app.state.settings.preview_enabled
    ):
        raise HTTPException(402, "Choose an active plan to use this feature")
    return context


class TrainingRecord(StrictBody):
    minutes: StrictInt = Field(ge=1, le=480)
    goal: Goal


@router.post("/training-sessions", status_code=201)
def record_training(
    body: TrainingRecord,
    context: BrowserContext = Depends(require_membership),
    db: Session = Depends(get_db),
):
    answers = onboarding_for(db, context)
    if not answers or body.goal not in answers["goals"]:
        raise HTTPException(422, "Choose one of your training directions")
    db.add(
        TrainingSession(
            user_id=context.user.id,
            title=body.goal,
            goal=body.goal,
            actual_minutes=body.minutes,
            completed_at=utcnow(),
            status="completed",
        )
    )
    db.commit()
    return {"progress": dashboard_progress(db, context.user, answers)}


@router.post("/billing-portal")
def billing_portal(
    request: Request, context: BrowserContext = Depends(require_user), db: Session = Depends(get_db)
):
    subscription = db.get(Subscription, context.user.id)
    settings = request.app.state.settings
    if not subscription or not subscription.stripe_subscription_id or not settings.payments_enabled:
        raise HTTPException(503, "Subscription management is not configured")
    try:
        provider = StripeGateway(settings).subscription(subscription.stripe_subscription_id)
        portal = stripe.billing_portal.Session.create(
            api_key=settings.stripe_secret_key.get_secret_value(),
            customer=provider["customer"],
            return_url=f"{settings.base_url}/dashboard",
        )
        return {"url": portal.url}
    except (stripe.StripeError, KeyError):
        raise HTTPException(503, "Subscription management is unavailable") from None


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    context: BrowserContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    db.execute(delete(BrowserSession).where(BrowserSession.token_hash == context.row.token_hash))
    db.commit()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=request.app.state.settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


def process_webhook(factory, event, gateway):
    with factory() as db:
        apply_webhook(db, event, gateway)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    settings = request.app.state.settings
    if not settings.payments_enabled:
        raise HTTPException(503, "Payment webhooks are not configured")
    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            body,
            request.headers.get("stripe-signature", ""),
            settings.stripe_webhook_secret.get_secret_value(),
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature") from None
    try:
        await run_in_threadpool(
            process_webhook, request.app.state.session_factory, event, StripeGateway(settings)
        )
    except (BillingUnavailable, stripe.StripeError, KeyError, ValueError):
        raise HTTPException(503, "Webhook could not be reconciled; retry later") from None
    return {"received": True}
