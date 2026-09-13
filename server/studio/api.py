"""HTTP contracts; database writes remain scoped to the browser's authenticated owner."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
from studio.models import BrowserSession, OnboardingProfile, Subscription, User, utcnow
from studio.plans import public_plans
from studio.schemas import CheckoutInput, OnboardingInput, PreviewRegistration
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
    user = context.user
    subscription = db.get(Subscription, user.id) if user else None
    membership = None
    if subscription:
        membership = {
            "plan_id": subscription.plan_id,
            "is_demo": subscription.is_demo,
            "status": subscription.status
            if active_subscription(subscription)
            else (
                "expired" if subscription.status in {"active", "trialing"} else subscription.status
            ),
        }
    settings = request.app.state.settings
    return {
        "csrf_token": csrf_token(context.raw, settings),
        "user": {"id": str(user.id), "name": user.name, "is_demo": user.is_demo} if user else None,
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
