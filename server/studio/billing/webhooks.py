"""Raw-body signature verification precedes durable acknowledgement."""

import time

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from studio.auth.db_work import run_db
from studio.auth.token_store import StoreError, TokenCipher
from studio.billing.checkout import BillingTransaction
from studio.db import UnsafeWebRole

router = APIRouter()
TYPES = {
    "checkout.session.completed": "checkout.session",
    "checkout.session.expired": "checkout.session",
    "customer.subscription.created": "subscription",
    "customer.subscription.updated": "subscription",
    "customer.subscription.deleted": "subscription",
    "invoice.paid": "invoice",
    "refund.created": "refund",
    "refund.updated": "refund",
    "refund.failed": "refund",
    "invoice.payment_failed": "invoice",
}


class InvalidWebhook(ValueError):
    pass


class WebhookInbox:
    def __init__(self, transaction: BillingTransaction, secret: SecretStr, cipher: TokenCipher):
        self.transaction = transaction
        self.secret = secret
        self.cipher = cipher

    def accept(self, raw: bytes, signature: str) -> None:
        try:
            stamps = [int(p[2:]) for p in signature.split(",") if p.startswith("t=")]
            if len(stamps) != 1 or abs(time.time() - stamps[0]) > 300:
                raise InvalidWebhook()
            event = stripe.Webhook.construct_event(
                raw, signature, self.secret.get_secret_value(), tolerance=300
            ).to_dict()
            obj = event["data"]["object"]
            event_id, event_type, object_id = event["id"], event["type"], obj["id"]
            if (
                event.get("livemode") is not False
                or event.get("account")
                or not isinstance(event_id, str)
                or not event_id.startswith("evt_")
                or len(event_id) > 255
                or not isinstance(event_type, str)
                or not 1 <= len(event_type) <= 100
                or not isinstance(object_id, str)
                or not 1 <= len(object_id) <= 255
            ):
                raise InvalidWebhook()
            if event_type in TYPES and (
                obj.get("object") != TYPES[event_type]
                or (TYPES[event_type] != "refund" and obj.get("livemode") is not False)
            ):
                raise InvalidWebhook()
            encrypted = self.cipher.encrypt(raw.decode("utf-8"), ("stripe-event", event_id))
        except (ValueError, KeyError, TypeError, AttributeError, stripe.SignatureVerificationError):
            raise InvalidWebhook() from None
        with self.transaction() as session:
            session.execute(
                text(
                    "INSERT INTO studio_private.webhook_events (event_id,event_type,object_id,encrypted_payload,state) VALUES (:e,:t,:o,:p,:s) ON CONFLICT(event_id) DO NOTHING"
                ),
                {
                    "e": event_id,
                    "t": event_type,
                    "o": object_id,
                    "p": encrypted,
                    "s": "pending" if event_type in TYPES else "ignored",
                },
            )


@router.post("/api/webhooks/stripe")
async def receive_stripe(request: Request) -> JSONResponse:
    service = getattr(request.app.state, "webhook_inbox", None)
    if service is None:
        raise HTTPException(503)
    signatures = request.headers.getlist("stripe-signature")
    if len(signatures) != 1:
        raise HTTPException(400)
    raw = await request.body()
    try:
        await run_db(service.accept, raw, signatures[0])
    except InvalidWebhook:
        raise HTTPException(400) from None
    except (SQLAlchemyError, UnsafeWebRole, StoreError):
        raise HTTPException(503) from None
    return JSONResponse({"received": True}, headers={"Cache-Control": "no-store"})
