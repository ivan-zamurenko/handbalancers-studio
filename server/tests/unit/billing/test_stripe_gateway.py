"""Stripe boundary tests use SDK HTTP transport, never a live payment."""

import importlib
import json
from uuid import uuid4

import pytest
import stripe
from pydantic import SecretStr

PRICES = {
    "essential": "price_essential",
    "plus": "price_plus",
    "pro": "price_pro",
    "pro-plus": "price_proplus",
}
AMOUNTS = {"essential": 1999, "plus": 4999, "pro": 17999, "pro-plus": 29999}


@pytest.fixture
def api():
    return importlib.import_module("studio.billing.stripe_gateway")


class Transport(stripe.HTTPClient):
    name = "test"

    def __init__(self):
        super().__init__()
        self.calls = []
        self.responses = []

    def request(self, method, url, headers, post_data=None, **kwargs):
        self.calls.append((method, url, headers, post_data))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return json.dumps(result).encode(), 200, {}


def gateway(api):
    transport = Transport()
    return api.StripeGateway(
        SecretStr("sk_test_synthetic"), PRICES, http_client=transport
    ), transport


def price(plan, **changes):
    return {
        "id": PRICES[plan],
        "object": "price",
        "livemode": False,
        "active": True,
        "currency": "eur",
        "unit_amount": AMOUNTS[plan],
        "type": "recurring",
        "recurring": {"interval": "month", "interval_count": 1, "usage_type": "licensed"},
        "billing_scheme": "per_unit",
        **changes,
    }


def test_configured_price_matches(api):
    gw, http = gateway(api)
    http.responses = [price(p) for p in PRICES]
    gw.validate_catalog()
    assert len(http.calls) == 4
    assert all(call[2]["Stripe-Version"] == api.API_VERSION for call in http.calls)


@pytest.mark.parametrize(
    "change",
    [
        {"livemode": True},
        {"active": False},
        {"currency": "usd"},
        {"unit_amount": 1},
        {"recurring": {"interval": "year", "interval_count": 1}},
        {"recurring": {"interval": "month", "interval_count": 2}},
        {"id": "price_other"},
        {"type": "one_time"},
    ],
)
def test_price_mismatch_closed(api, change):
    gw, http = gateway(api)
    http.responses = [price("essential", **change)]
    with pytest.raises(api.BillingUnavailable):
        gw.validate_catalog()


@pytest.mark.parametrize("key", ["sk_live_synthetic", "rk_live_synthetic", "", "invalid"])
def test_mode_mismatch_denied(api, key):
    with pytest.raises(api.BillingUnavailable):
        api.StripeGateway(SecretStr(key), PRICES)


def test_client_price_id_ignored_and_no_cards_in_app(api):
    gw, http = gateway(api)
    http.responses = [
        price("plus"),
        {
            "id": "cs_test_synthetic",
            "object": "checkout.session",
            "livemode": False,
            "url": "https://checkout.stripe.com/c/pay/cs_test_synthetic",
            "status": "open",
        },
    ]
    attempt = uuid4()
    gw.create_checkout(
        attempt_id=attempt,
        customer_id="cus_synthetic",
        plan_code="plus",
        trial=True,
        origin="http://127.0.0.1:8765",
        expires_at=1800000000,
    )
    body = http.calls[-1][3]
    from urllib.parse import parse_qs

    fields = parse_qs(body)
    assert fields.get("allowed_payment_method_types[0]") == ["card"]
    assert not any(key.startswith("payment_method_types") for key in fields)
    assert "price_plus" in body and "payment_method_collection=always" in body
    assert "trial_period_days%5D=7" in body or "trial_period_days]=7" in body
    assert http.calls[-1][2]["Idempotency-Key"] == f"studio:checkout:{attempt}"
    for extra in ({"price_id": "price_evil"}, {"card_number": "synthetic"}, {"amount": 1}):
        with pytest.raises(TypeError):
            gw.create_checkout(
                attempt_id=attempt,
                customer_id="cus_synthetic",
                plan_code="plus",
                trial=False,
                origin="http://127.0.0.1:8765",
                expires_at=1800000000,
                **extra,
            )


def test_pro_cannot_get_trial(api):
    gw, http = gateway(api)
    with pytest.raises(api.BillingUnavailable):
        gw.create_checkout(
            attempt_id=uuid4(),
            customer_id="cus_synthetic",
            plan_code="pro",
            trial=True,
            origin="http://127.0.0.1:8765",
            expires_at=1800000000,
        )
    assert not http.calls


def test_network_failure_sanitized_and_bounded(api):
    gw, http = gateway(api)
    http.responses = [stripe.APIConnectionError("private provider detail")]
    with pytest.raises(api.BillingUnavailable) as error:
        gw.validate_catalog()
    assert "private" not in str(error.value)
    assert len(http.calls) == 1


def test_sdk_payload_and_error_are_not_logged(api, caplog, capsys, monkeypatch):
    import logging

    from stripe import _util

    monkeypatch.setattr(stripe, "log", "debug")
    monkeypatch.setattr(_util, "STRIPE_LOG", "debug")
    caplog.set_level(logging.DEBUG, logger="stripe")
    marker = "private-provider-response-marker"

    class ErrorTransport(Transport):
        def request(self, *args, **kwargs):
            return (
                json.dumps(
                    {"error": {"type": "invalid_request_error", "message": marker}}
                ).encode(),
                400,
                {},
            )

    gw = api.StripeGateway(SecretStr("sk_test_synthetic"), PRICES, http_client=ErrorTransport())
    with pytest.raises(api.BillingUnavailable):
        gw.validate_catalog()
    captured = capsys.readouterr()
    assert marker not in caplog.text + captured.out + captured.err


def test_discovery_refuses_truncated_results(api):
    gw, http = gateway(api)
    http.responses = [
        {"object": "list", "data": [], "has_more": True, "url": "/v1/checkout/sessions"}
    ]
    with pytest.raises(api.BillingUnavailable):
        gw.list_checkouts("cus_synthetic")


@pytest.mark.parametrize("malformed", [None, "live", "foreign_customer", "foreign_url"])
def test_portal_validates_provider_response(api, malformed):
    gw, http = gateway(api)
    payload = {
        "object": "billing_portal.session",
        "id": "bps_test",
        "livemode": False,
        "customer": "cus_owner",
        "return_url": "https://studio.test/subscription",
        "url": "https://billing.stripe.com/p/session/test_synthetic",
    }
    if malformed == "live":
        payload["livemode"] = True
    if malformed == "foreign_customer":
        payload["customer"] = "cus_foreign"
    if malformed == "foreign_url":
        payload["url"] = "https://evil.test/session"
    http.responses = [payload]
    if malformed:
        with pytest.raises(api.BillingUnavailable):
            gw.create_portal("cus_owner", "https://studio.test/subscription")
    else:
        assert gw.create_portal("cus_owner", "https://studio.test/subscription") == payload["url"]
        assert "customer=cus_owner" in http.calls[0][3]
