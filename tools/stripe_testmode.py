"""Operator-run external gate, exclusively against the guarded local test stack.

Run via tools/local_stack.py test .venv/bin/python -m tools.stripe_testmode.
Commands on stdin: report, audit, advance, cancel, stop. Credentials never printed.
Browser session fixtures stay in ignored private-evidence with mode0600.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import stripe
import uvicorn
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from studio.auth.gateway import AuthGateway
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.supabase_adapter import SupabaseAuthAdapter
from studio.auth.token_store import TokenCipher, TokenStore
from studio.billing.checkout import CheckoutService
from studio.billing.reconciliation import Reconciler
from studio.billing.stripe_gateway import (
    AMOUNTS,
    API_VERSION,
    BillingUnavailable,
    StripeGateway,
    _disable_sdk_payload_logging,
)
from studio.billing.webhooks import TYPES, WebhookInbox
from studio.main import create_app

from server.tests.support.actors import role_session
from server.tests.support.database_guard import require_test_database
from tools import local_auth_fixture, local_stack

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private-evidence/stripe-testmode"
ORIGIN = "http://127.0.0.1:8787"


def private_json(name, value):
    path = PRIVATE / name
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    path.chmod(0o600)


def check(condition, name):
    if not condition:
        raise AssertionError(name)


def safe_test(value):
    return StripeGateway.test_object(value)


class Gate:
    def __init__(self):
        PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        PRIVATE.chmod(0o700)
        self.stopped = threading.Event()
        self.events = []
        self.replayed = {}
        self.failures = {}
        self.accounts = {}
        self.results = {
            "run_id": uuid4().hex,
            "started_at": int(time.time()),
            "status": "pending",
            "environment": "isolated_local_supabase_and_real_stripe_test",
            "live_charges": False,
        }
        private_json("result.json", self.results)

    def start(self):
        require_test_database()
        local_stack.verify_container("test")
        _disable_sdk_payload_logging()
        key = tomllib.loads((Path.home() / ".config/stripe/config.toml").read_text())["default"][
            "test_mode_api_key"
        ]
        check(key.startswith(("sk_test_", "rk_test_")), "test_key_required")
        for unsafe in ("sk_live_synthetic", "rk_live_synthetic"):
            try:
                StripeGateway(SecretStr(unsafe), {plan: "price_" + plan for plan in AMOUNTS})
            except BillingUnavailable:
                pass
            else:
                raise AssertionError("live_key_accepted")
        try:
            safe_test({"livemode": True})
        except BillingUnavailable:
            pass
        else:
            raise AssertionError("live_object_accepted")
        self.results["no_live_environment"] = True
        self.client = stripe.StripeClient(
            key,
            stripe_version=API_VERSION,
            max_network_retries=0,
            http_client=stripe.RequestsClient(timeout=10),
        )
        self.prices = self.catalog()
        self.gateway = StripeGateway(SecretStr(key), self.prices)
        self.gateway.validate_catalog()
        self.results["test_catalog_validated"] = True
        workdir = ROOT / ".local-tools/supabase/test"
        local_stack.run_migrations("test")
        config = json.loads(
            local_stack.cli_output(
                ["status", "--output", "json"], workdir, local_stack.docker_environment()
            )
        )
        self.engine = create_engine(
            URL.create(
                "postgresql+psycopg",
                username="migration_owner",
                password=local_stack.read_migration_password(workdir),
                host="127.0.0.1",
                port=55322,
                database="postgres",
            ),
            hide_parameters=True,
            pool_pre_ping=True,
        )
        self.tx = lambda: role_session(self.engine, "studio_worker")
        auth = AuthGateway(SupabaseAuthAdapter("http://127.0.0.1:55321", config["ANON_KEY"]))
        cipher = TokenCipher("external-test", {"external-test": secrets.token_bytes(32)})
        oauth = OAuthService(
            auth_transaction=lambda: role_session(self.engine, "studio_auth_runtime"),
            store=TokenStore(cipher, allowed_return_paths=frozenset({"/plans"})),
            gateway=auth,
            validator=JWTValidator(issuer="http://127.0.0.1:55321/auth/v1"),
            supabase_url="http://127.0.0.1:55321",
            public_origin=ORIGIN,
            providers=frozenset(),
        )
        app = create_app({"app_env": "test", "public_origin": ORIGIN})
        app.state.oauth_service = oauth
        app.state.auth_gateway = auth
        app.state.verification_service = oauth
        app.state.web_transaction = lambda actor: role_session(
            self.engine, "studio_web", actor.user_id
        )
        app.state.checkout_service = CheckoutService(
            transaction=self.tx,
            web_transaction=app.state.web_transaction,
            gateway=self.gateway,
            origin=ORIGIN,
        )
        for name in ("studio.access", "uvicorn", "uvicorn.error", "uvicorn.access", "httpx"):
            logging.getLogger(name).setLevel(logging.CRITICAL)
        self.listener = subprocess.Popen(
            [
                "/opt/homebrew/bin/stripe",
                "listen",
                "--forward-to",
                ORIGIN + "/api/webhooks/stripe",
                "--events",
                ",".join(TYPES),
            ],
            env={**os.environ, "STRIPE_API_KEY": key, "STRIPE_NO_AUTO_UPDATE": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        signing = []

        def consume():
            for line in self.listener.stdout:
                match = re.search(r"whsec_[A-Za-z0-9]+", line)
                if match:
                    signing.append(match.group(0))

        threading.Thread(target=consume, daemon=True).start()
        self.wait(lambda: bool(signing), 30, "stripe_listener_ready")
        app.state.webhook_inbox = WebhookInbox(self.tx, SecretStr(signing[0]), cipher)

        @app.middleware("http")
        async def capture(request, call_next):
            if request.url.path == "/api/webhooks/stripe":
                body = await request.body()
                response = await call_next(request)
                if response.status_code == 200:
                    signature = request.headers.get("stripe-signature", "")
                    self.events.append((body, signature))
                    event = json.loads(body)
                    if (
                        event["type"] == "checkout.session.completed"
                        and event["id"] not in self.replayed
                    ):
                        self.replayed[event["id"]] = []

                        def repeat():
                            with httpx.Client(
                                base_url=ORIGIN, timeout=15, trust_env=False
                            ) as client:
                                for _ in range(2):
                                    reply = client.post(
                                        "/api/webhooks/stripe",
                                        content=body,
                                        headers={
                                            "stripe-signature": signature,
                                            "Content-Type": "application/json",
                                        },
                                    )
                                    self.replayed[event["id"]].append(reply.status_code)

                        threading.Thread(target=repeat, daemon=True).start()
                return response
            return await call_next(request)

        self.server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=8787, log_level="critical", access_log=False)
        )
        threading.Thread(target=self.server.run, daemon=True).start()
        self.wait(lambda: self.server.started, 15, "local_server_ready")
        self.worker = Reconciler(self.tx, self.gateway)

        def work():
            while not self.stopped.is_set():
                try:
                    self.worker.run_once()
                except Exception as exc:  # noqa: BLE001 - gate boundary must never print provider secrets
                    self.results["worker_error_type"] = type(exc).__name__
                self.stopped.wait(0.3)

        threading.Thread(target=work, daemon=True).start()
        self.clock = safe_test(
            self.client.v1.test_helpers.test_clocks.create(
                {"frozen_time": int(time.time()), "name": "Studio S13-09 isolated trial"}
            )
        )
        for label in ("pro", "plus", "foreign"):
            self.accounts[label] = self.account(label)
        # Real test-clock customer, linked to a real authenticated synthetic member.
        # No subscription/entitlement is seeded; these come only through Checkout/webhooks.
        customer = safe_test(
            self.client.v1.customers.create(
                {
                    "test_clock": self.clock["id"],
                    "metadata": {
                        "studio_user_id": self.accounts["plus"]["id"],
                        "studio_gate": "S13-09",
                    },
                }
            )
        )
        with self.tx() as s:
            s.execute(
                text(
                    "INSERT INTO studio.billing_customers(user_id,provider_customer_id) VALUES (:u,:c)"
                ),
                {"u": self.accounts["plus"]["id"], "c": customer["id"]},
            )
        private_json(
            "browser.json",
            {"origin": ORIGIN, "accounts": self.accounts, "run_id": self.results["run_id"]},
        )
        print(
            json.dumps({"ready": True, "test_catalog": 4, "synthetic_accounts": 3, "port": 8787}),
            flush=True,
        )

    @staticmethod
    def wait(condition, seconds, name):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.5)
        raise TimeoutError(name)

    def catalog(self):
        path = PRIVATE / "prices.json"
        saved = json.loads(path.read_text()) if path.exists() else {}
        if set(saved) == set(AMOUNTS):
            return saved
        product = safe_test(
            self.client.v1.products.create(
                {
                    "name": "Handbalancer Studio — isolated TEST packages",
                    "metadata": {"studio_gate": "S13-09"},
                },
                options={"idempotency_key": "studio:S13-09:catalog:v1"},
            )
        )
        prices = {}
        for code, amount in AMOUNTS.items():
            item = safe_test(
                self.client.v1.prices.create(
                    {
                        "product": product["id"],
                        "currency": "eur",
                        "unit_amount": amount,
                        "recurring": {"interval": "month"},
                        "nickname": f"Studio TEST {code}",
                        "metadata": {"studio_gate": "S13-09", "plan_code": code},
                    },
                    options={"idempotency_key": f"studio:S13-09:price:{code}:v1"},
                )
            )
            prices[code] = item["id"]
        private_json("prices.json", prices)
        return prices

    def account(self, label):
        email = local_auth_fixture.disposable_email("stripe-" + label)
        with httpx.Client(
            base_url=ORIGIN, headers={"Origin": ORIGIN}, timeout=20, trust_env=False
        ) as c:
            response = c.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "password": secrets.token_urlsafe(24),
                    "first_name": "Тест",
                    "last_name": "Оплата",
                },
            )
            check(response.status_code == 202, "register_" + str(response.status_code))
            response = c.post(
                "/api/auth/verify-email",
                json={"email": email, "token": local_auth_fixture.read_code(email)},
            )
            check(response.status_code == 200, "verify_" + str(response.status_code))
            snapshot = c.get("/api/session").json()
            c.headers["X-CSRF-Token"] = snapshot["csrf_token"]
            response = c.put(
                "/api/me/onboarding",
                json={
                    "goal_codes": ["fitness"],
                    "self_reported_level": 1,
                    "session_minutes": 30,
                    "weekdays": [1],
                    "expected_revision": 0,
                },
            )
            check(response.status_code == 200, "profile_" + str(response.status_code))
            return {
                "id": snapshot["user"]["id"],
                "email": email,
                "cookies": [
                    {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": "127.0.0.1",
                        "path": "/",
                        "httpOnly": True,
                        "sameSite": "Lax",
                    }
                    for cookie in c.cookies.jar
                ],
            }

    @contextmanager
    def browser_client(self, label):
        with httpx.Client(
            base_url=ORIGIN, headers={"Origin": ORIGIN}, timeout=20, trust_env=False
        ) as client:
            for cookie in self.accounts[label]["cookies"]:
                client.cookies.set(cookie["name"], cookie["value"])
            client.headers["X-CSRF-Token"] = client.get("/api/session").json()["csrf_token"]
            yield client

    def projection(self, label):
        with self.engine.connect() as c:
            row = (
                c.execute(
                    text(
                        "SELECT provider_subscription_id,status,plan_code,row_version FROM studio.subscriptions WHERE user_id=:u"
                    ),
                    {"u": self.accounts[label]["id"]},
                )
                .mappings()
                .one_or_none()
            )
            return dict(row) if row else None

    def report(self):
        browser = {}
        for label in ("pro", "plus"):
            path = PRIVATE / f"browser-{label}.json"
            if path.exists():
                saved = json.loads(path.read_text())
                if saved.get("run_id") == self.results["run_id"]:
                    browser[label] = saved
        browser_ok = all(
            browser.get(label, {}).get("real_browser_purchase")
            and browser.get(label, {}).get("real_portal_browser_loaded")
            for label in ("pro", "plus")
        ) and browser.get("pro", {}).get("decline_denied_access")
        required = (
            "real_test_checkout",
            "real_signature",
            "duplicate_event_safe",
            "security_http",
            "trial_card_7days",
            "real_portal_api",
            "trial_end_lifecycle",
            "test_subscription_cleanup",
            "no_live_environment",
        )
        self.results["status"] = (
            "failed"
            if self.failures or self.results.get("worker_error_type")
            else "passed"
            if browser_ok and all(self.results.get(k) for k in required)
            else "pending"
        )
        self.results["browser_verified"] = bool(browser_ok)
        states = {}
        for label in self.accounts:
            row = self.projection(label)
            states[label] = (
                {k: v for k, v in row.items() if k != "provider_subscription_id"} if row else None
            )
        with self.engine.connect() as c:
            event_counts = dict(
                c.execute(
                    text("SELECT state,count(*) FROM studio_private.webhook_events GROUP BY state")
                ).all()
            )
        data = {
            **self.results,
            "failures": self.failures,
            "projection": states,
            "signed_deliveries": len(self.events),
            "inbox": event_counts,
        }
        private_json("result.json", data)
        print(json.dumps(data), flush=True)

    def audit(self):
        for label in ("pro", "plus"):
            self.wait(
                lambda label=label: self.projection(label) is not None, 45, "projection_" + label
            )
        pro, plus = self.projection("pro"), self.projection("plus")
        check(
            pro["status"] == "active" and plus["status"] == "trialing", "paid_and_trial_projection"
        )
        for label, expected in (("pro", 17999), ("plus", 0)):
            sub = self.gateway.retrieve_subscription(
                self.projection(label)["provider_subscription_id"]
            )
            check(
                sub["latest_invoice"]["status"] == "paid"
                and sub["latest_invoice"]["amount_paid"] == expected,
                "actual_invoice_" + label,
            )
            if label == "plus":
                check(
                    sub["trial_end"] - sub["trial_start"] == 7 * 86400
                    and sub["default_payment_method"]["type"] == "card",
                    "actual_card_trial",
                )
        with self.browser_client("pro") as client, self.browser_client("foreign") as foreign:
            with self.engine.connect() as c:
                attempt = c.execute(
                    text(
                        "SELECT id FROM studio.checkout_attempts WHERE user_id=:u ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"u": self.accounts["pro"]["id"]},
                ).scalar_one()
            check(
                foreign.get("/api/me/checkout-attempts/" + str(attempt)).status_code == 404,
                "foreign_attempt",
            )
            check(
                foreign.get("/api/me/subscription").json()["subscription"] is None,
                "foreign_summary",
            )
            body = {"plan_code": "pro", "terms_version": "test-v1"}
            headers = {"Idempotency-Key": str(uuid4())}
            for field, value in [
                ("price_id", "price_injected"),
                ("trial", True),
                ("user_id", self.accounts["foreign"]["id"]),
            ]:
                check(
                    client.post(
                        "/api/checkout", json={**body, field: value}, headers=headers
                    ).status_code
                    == 422,
                    "reject_" + field,
                )
            check(
                client.post("/api/checkout", json=body, headers=headers).status_code == 409,
                "duplicate_subscription",
            )
            check(
                client.post(
                    "/api/checkout", json=body, headers={**headers, "X-CSRF-Token": "invalid"}
                ).status_code
                == 403,
                "csrf",
            )
            check(
                client.post(
                    "/api/checkout",
                    json=body,
                    headers={**headers, "Origin": "https://evil.example"},
                ).status_code
                == 403,
                "origin",
            )
            check(
                client.post(
                    "/api/webhooks/stripe", content=b"{}", headers={"stripe-signature": "invalid"}
                ).status_code
                == 400,
                "invalid_signature",
            )
            matching = [
                (body, sig)
                for body, sig in self.events
                if json.loads(body).get("type") == "checkout.session.completed"
                and json.loads(body)["data"]["object"].get("client_reference_id") == str(attempt)
            ]
            check(bool(matching), "actual_cli_checkout_event")
            raw, _sig = matching[0]
            event_id = json.loads(raw)["id"]
            check(self.replayed.get(event_id) == [200, 200], "actual_duplicate_delivery")
            with self.engine.connect() as c:
                check(
                    c.scalar(
                        text(
                            "SELECT count(*) FROM studio_private.webhook_events WHERE event_id=:e"
                        ),
                        {"e": event_id},
                    )
                    == 1,
                    "inbox_dedupe",
                )
            check(pro["row_version"] == 1, "single_initial_projection")
            portal = client.post("/api/billing-portal", json={})
            check(portal.status_code == 200, "real_portal_" + str(portal.status_code))
        self.results.update(
            real_test_checkout=True,
            real_signature=True,
            duplicate_event_safe=True,
            security_http=True,
            trial_card_7days=True,
            real_portal_api=True,
        )
        self.report()

    def advance(self):
        row = self.projection("plus")
        check(row and row["status"] == "trialing", "trial_before_clock")
        sub = self.gateway.retrieve_subscription(row["provider_subscription_id"])
        safe_test(
            self.client.v1.test_helpers.test_clocks.advance(
                self.clock["id"], {"frozen_time": sub["trial_end"] + 3700}
            )
        )
        self.wait(
            lambda: (
                safe_test(self.client.v1.test_helpers.test_clocks.retrieve(self.clock["id"]))[
                    "status"
                ]
                == "ready"
            ),
            90,
            "clock_ready",
        )
        self.wait(
            lambda: self.projection("plus")["status"] == "active", 90, "trial_renewal_projection"
        )
        sub = self.gateway.retrieve_subscription(row["provider_subscription_id"])
        check(
            sub["latest_invoice"]["status"] == "paid"
            and sub["latest_invoice"]["amount_paid"] == 4999,
            "trial_paid_invoice",
        )
        self.results["trial_end_lifecycle"] = True
        self.report()

    def cancel(self):
        for label in ("pro", "plus"):
            row = self.projection(label)
            if row and row["status"] != "canceled":
                safe_test(self.client.v1.subscriptions.cancel(row["provider_subscription_id"]))
                self.wait(
                    lambda label=label: self.projection(label)["status"] == "canceled",
                    45,
                    "cancellation_" + label,
                )
        self.results["test_subscription_cleanup"] = True
        self.report()

    def close(self):
        if hasattr(self, "stopped"):
            self.stopped.set()
        if hasattr(self, "server"):
            self.server.should_exit = True
        if hasattr(self, "listener"):
            self.listener.terminate()
            self.listener.wait(timeout=10)
        if hasattr(self, "engine"):
            self.engine.dispose()
        (PRIVATE / "browser.json").unlink(missing_ok=True)


def main():
    gate = None
    try:
        gate = Gate()
        gate.start()
        for command in sys.stdin:
            command = command.strip()
            if command == "stop":
                break
            if command not in {"report", "audit", "advance", "cancel"}:
                print('{"error":"unknown_command"}', flush=True)
                continue
            try:
                getattr(gate, command)()
                gate.failures.pop(command, None)
                gate.report()
            except Exception as exc:  # noqa: BLE001 - gate boundary must never print provider secrets
                # Stripe/HTTP exception text can contain secrets. Emit only class and our assertion labels.
                gate.failures[command] = type(exc).__name__
                gate.results["status"] = "failed"
                gate.report()
                print(
                    json.dumps(
                        {
                            "error": type(exc).__name__,
                            "check": str(exc)
                            if isinstance(exc, (AssertionError, TimeoutError))
                            else "provider_or_environment",
                        }
                    ),
                    flush=True,
                )
    except Exception as exc:  # noqa: BLE001 - gate boundary must never print provider secrets
        if gate:
            gate.results["status"] = "failed"
            gate.failures["startup"] = type(exc).__name__
            private_json("result.json", {**gate.results, "failures": gate.failures})
        print(
            json.dumps(
                {
                    "startup_error": type(exc).__name__,
                    "check": str(exc)
                    if isinstance(exc, (AssertionError, TimeoutError))
                    else "provider_or_environment",
                }
            ),
            flush=True,
        )
        return 1
    finally:
        if gate:
            gate.close()
    return 0 if gate and gate.results["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
