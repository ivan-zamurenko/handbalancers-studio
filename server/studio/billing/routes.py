"""Thin authenticated Checkout endpoints; no browser route grants entitlement."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from studio.accounts.routes import _actor
from studio.auth.db_work import run_db
from studio.auth.oauth_routes import HEADERS
from studio.billing.checkout import (
    CheckoutConflict,
    CheckoutForbidden,
    CheckoutNotFound,
    CheckoutService,
)
from studio.billing.stripe_gateway import BillingUnavailable
from studio.db import UnsafeWebRole

router = APIRouter()


class CheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    plan_code: Literal["essential", "plus", "pro", "pro-plus"]
    terms_version: Literal["test-v1"]


def service_for(request: Request) -> CheckoutService:
    service = getattr(request.app.state, "checkout_service", None)
    if service is None:
        raise HTTPException(503)
    return service


@router.post("/api/checkout")
async def checkout(request: Request, data: CheckoutInput) -> JSONResponse:
    actor, _ = await _actor(request, mutating=True)
    keys = request.headers.getlist("idempotency-key")
    if len(keys) != 1 or not 1 <= len(keys[0]) <= 128:
        raise HTTPException(422)
    try:
        result = await run_db(
            service_for(request).begin,
            actor,
            plan_code=data.plan_code,
            terms_version=data.terms_version,
            key=keys[0],
        )
    except CheckoutForbidden:
        raise HTTPException(403) from None
    except CheckoutConflict:
        raise HTTPException(409) from None
    except (BillingUnavailable, SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return JSONResponse(jsonable_encoder(result), headers=HEADERS)


@router.get("/api/me/checkout-attempts/{attempt_id}")
async def checkout_status(request: Request, attempt_id: UUID) -> JSONResponse:
    actor, _ = await _actor(request, mutating=False)
    try:
        result = await run_db(service_for(request).get, actor, attempt_id)
    except CheckoutNotFound:
        raise HTTPException(404) from None
    except (SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return JSONResponse(jsonable_encoder(result), headers=HEADERS)


class PortalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


@router.post("/api/billing-portal")
async def billing_portal(request: Request, data: PortalInput) -> JSONResponse:
    from studio.billing.portal import create_portal

    actor, _ = await _actor(request, mutating=True)
    try:
        result = await run_db(create_portal, service_for(request), actor)
    except CheckoutNotFound:
        return JSONResponse(
            {
                "error": {
                    "code": "checkout_required",
                    "message_key": "billing.checkout_required",
                    "field_errors": [],
                    "request_id": request.state.request_id,
                }
            },
            status_code=409,
            headers=HEADERS,
        )
    except (BillingUnavailable, SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return JSONResponse(result, headers=HEADERS)


@router.get("/api/me/subscription")
async def subscription_status(request: Request) -> JSONResponse:
    from studio.billing.summary import subscription_summary

    actor, _ = await _actor(request, mutating=False)
    try:
        result = await run_db(subscription_summary, service_for(request), actor)
    except (SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return JSONResponse(jsonable_encoder(result), headers=HEADERS)


@router.get("/subscription", include_in_schema=False)
async def subscription_page(request: Request):
    from studio.accounts.entry import entry_destination
    from studio.public.routes import member_redirect, render

    destination = await entry_destination(request)
    if destination != "/dashboard":
        return member_redirect(request, destination)
    return render(request, "member/subscription.html")


@router.get("/billing/checkout/{attempt_id}", include_in_schema=False)
async def payment_page(request: Request, attempt_id: UUID):
    from studio.accounts.entry import entry_destination
    from studio.public.routes import member_redirect, render

    destination = await entry_destination(request)
    if destination != "/dashboard":
        return member_redirect(request, destination)
    actor, _ = await _actor(request, mutating=False)
    try:
        await run_db(service_for(request).get, actor, attempt_id)
    except CheckoutNotFound:
        raise HTTPException(404) from None
    except (SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return render(request, "public/checkout_status.html")


@router.get("/api/me/payments")
async def payment_records(
    request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 25, before: UUID | None = None
) -> JSONResponse:
    from studio.billing.payments import payment_history

    actor, _ = await _actor(request, mutating=False)
    transaction = getattr(request.app.state, "web_transaction", None)
    if transaction is None:
        raise HTTPException(503)
    try:
        result = await run_db(payment_history, transaction, actor, limit=limit, before=before)
    except (SQLAlchemyError, UnsafeWebRole):
        raise HTTPException(503) from None
    return JSONResponse(jsonable_encoder(result), headers=HEADERS)
