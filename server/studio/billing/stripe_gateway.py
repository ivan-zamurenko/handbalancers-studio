"""Pinned test-mode Stripe boundary. Cards stay on Stripe-hosted Checkout."""

import logging
from collections.abc import Callable, Mapping
from typing import Any, TypeVar
from uuid import UUID

import stripe
from pydantic import SecretStr

from studio.billing.catalog import PLANS

API_VERSION = "2026-11-18.endive"
AMOUNTS = {"essential": 1999, "plus": 4999, "pro": 17999, "pro-plus": 29999}
T = TypeVar("T")


class BillingUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Billing is temporarily unavailable")


class _DropStripePayloads(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return False


def _disable_sdk_payload_logging() -> None:
    # Pinned SDK can log raw bodies through BOTH Python logging and stderr.
    # Permanent process configuration avoids temporary overrides racing requests.
    from stripe import _util

    stripe.log = None
    _util.STRIPE_LOG = None
    logger = logging.getLogger("stripe")
    if not any(isinstance(item, _DropStripePayloads) for item in logger.filters):
        logger.addFilter(_DropStripePayloads())


class StripeGateway:
    def __init__(
        self,
        secret: SecretStr,
        prices: Mapping[str, str],
        *,
        http_client: stripe.HTTPClient | None = None,
    ) -> None:
        if not secret.get_secret_value().startswith(("sk_test_", "rk_test_")):
            raise BillingUnavailable()
        if set(prices) != set(PLANS) or any(not p.startswith("price_") for p in prices.values()):
            raise BillingUnavailable()
        if len(set(prices.values())) != len(PLANS):
            raise BillingUnavailable()
        _disable_sdk_payload_logging()
        self.prices = dict(prices)
        self.client = stripe.StripeClient(
            secret.get_secret_value(),
            stripe_version=API_VERSION,
            max_network_retries=0,
            http_client=http_client or stripe.RequestsClient(timeout=10),
        )

    @staticmethod
    def _call(call: Callable[[], T]) -> T:
        try:
            return call()
        except stripe.StripeError:
            raise BillingUnavailable() from None

    @staticmethod
    def test_object(obj: Any) -> Any:
        obj = obj.to_dict() if isinstance(obj, stripe.StripeObject) else obj
        if obj.get("livemode") is not False:
            raise BillingUnavailable()
        return obj

    def validate_price(self, plan_code: str) -> str:
        if plan_code not in self.prices:
            raise BillingUnavailable()
        price_id = self.prices[plan_code]
        price = self.test_object(self._call(lambda: self.client.v1.prices.retrieve(price_id)))
        recurring = price.get("recurring") or {}
        if (
            price["id"] != price_id
            or price.get("active") is not True
            or price.get("currency") != "eur"
            or price.get("unit_amount") != AMOUNTS[plan_code]
            or price.get("type") != "recurring"
            or price.get("billing_scheme") != "per_unit"
            or recurring.get("interval") != "month"
            or recurring.get("interval_count") != 1
            or recurring.get("usage_type") != "licensed"
            or price.get("transform_quantity")
        ):
            raise BillingUnavailable()
        return price_id

    def validate_catalog(self) -> None:
        for plan_code in self.prices:
            self.validate_price(plan_code)

    def create_customer(self, user_id: UUID) -> str:
        customer = self.test_object(
            self._call(
                lambda: self.client.v1.customers.create(
                    {"metadata": {"studio_user_id": str(user_id)}},
                    options={"idempotency_key": f"studio:customer:{user_id}"},
                )
            )
        )
        return str(customer["id"])

    def create_checkout(
        self,
        *,
        attempt_id: UUID,
        customer_id: str,
        plan_code: str,
        trial: bool,
        origin: str,
        expires_at: int,
    ) -> dict[str, Any]:
        if plan_code not in PLANS or (trial and not PLANS[plan_code].trial_allowed):
            raise BillingUnavailable()
        price_id = self.validate_price(plan_code)
        params: Any = {
            "mode": "subscription",
            "customer": customer_id,
            "client_reference_id": str(attempt_id),
            "line_items": [{"price": price_id, "quantity": 1}],
            "payment_method_types": ["card"],
            "payment_method_collection": "always",
            "success_url": f"{origin}/billing/checkout/{attempt_id}",
            "cancel_url": f"{origin}/billing/checkout/{attempt_id}?cancelled=1",
            "expires_at": expires_at,
            "subscription_data": {"metadata": {"studio_attempt_id": str(attempt_id)}},
        }
        if trial:
            params["subscription_data"]["trial_period_days"] = 7
        checkout = self.test_object(
            self._call(
                lambda: self.client.v1.checkout.sessions.create(
                    params,
                    options={"idempotency_key": f"studio:checkout:{attempt_id}"},
                )
            )
        )
        url = checkout.get("url")
        if not isinstance(url, str) or not url.startswith("https://checkout.stripe.com/"):
            raise BillingUnavailable()
        return {"id": str(checkout["id"]), "url": url, "status": str(checkout["status"])}

    def retrieve_checkout(self, identifier: str) -> dict[str, Any]:
        return self.test_object(
            self._call(lambda: self.client.v1.checkout.sessions.retrieve(identifier))
        )

    def retrieve_subscription(self, identifier: str) -> dict[str, Any]:
        return self.test_object(
            self._call(
                lambda: self.client.v1.subscriptions.retrieve(
                    identifier, {"expand": ["latest_invoice", "default_payment_method"]}
                )
            )
        )

    def retrieve_invoice(self, identifier: str) -> dict[str, Any]:
        return self.test_object(self._call(lambda: self.client.v1.invoices.retrieve(identifier)))
