"""Signed raw HTTP, durable database inbox, duplicate and privacy guarantees."""

import hashlib
import hmac
import importlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from studio.auth.token_store import TokenCipher
from studio.main import create_app

from server.tests.integration.database.test_auth_storage import (  # noqa: F401
    database_engine,
    storage_db,
)
from server.tests.support.actors import role_session

SECRET = "whsec_synthetic_test_only"


def raw_event(**changes):
    return json.dumps(
        {
            "id": "evt_synthetic",
            "object": "event",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_test_synthetic",
                    "object": "checkout.session",
                    "livemode": False,
                    "customer_email": "private-marker@example.test",
                }
            },
            **changes,
        }
    ).encode()


def signed(raw, age=0):
    stamp = int(time.time()) - age
    digest = hmac.new(SECRET.encode(), str(stamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"


@pytest.fixture
def inbox(storage_db):  # noqa: F811
    api = importlib.import_module("studio.billing.webhooks")
    service = api.WebhookInbox(
        lambda: role_session(storage_db, "studio_worker"),
        SecretStr(SECRET),
        TokenCipher("test", {"test": b"x" * 32}),
    )
    app = create_app({"app_env": "test"})
    app.state.webhook_inbox = service
    client = TestClient(app)
    try:
        yield client, service, storage_db
    finally:
        with storage_db.begin() as c:
            c.execute(text("DELETE FROM studio_private.webhook_events"))


@pytest.mark.parametrize("age", [600, -600])
def test_invalid_signature_rejected(inbox, age):
    client, _, db = inbox
    raw = raw_event()
    assert (
        client.post(
            "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": signed(raw, age)}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": "bad"}
        ).status_code
        == 400
    )
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio_private.webhook_events")) == 0


def test_raw_body_verified(inbox):
    client, _, db = inbox
    raw = raw_event()
    assert (
        client.post(
            "/api/webhooks/stripe", content=raw + b" ", headers={"Stripe-Signature": signed(raw)}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": signed(raw)}
        ).status_code
        == 200
    )
    with db.connect() as c:
        assert c.execute(
            text("SELECT event_id,object_id,state FROM studio_private.webhook_events")
        ).one() == ("evt_synthetic", "cs_test_synthetic", "pending")


def test_duplicate_event_once(inbox):
    _, service, db = inbox
    raw = raw_event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: service.accept(raw, signed(raw)), range(2)))
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio_private.webhook_events")) == 1


def test_database_failure_retries(inbox):
    client, service, db = inbox

    @contextmanager
    def failing():
        raise OperationalError("synthetic", None, Exception("private database marker"))
        yield

    service.transaction = failing
    raw = raw_event()
    response = client.post(
        "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": signed(raw)}
    )
    assert response.status_code == 503
    assert "private" not in response.text
    with db.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM studio_private.webhook_events")) == 0


def test_no_payload_logs_or_storage(inbox, caplog, capsys):
    client, service, db = inbox
    raw = raw_event()
    response = client.post(
        "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": signed(raw)}
    )
    assert response.status_code == 200
    out = capsys.readouterr()
    assert "private-marker" not in caplog.text + out.out + out.err + response.text
    with db.connect() as c:
        assert "private-marker" not in str(
            c.execute(text("SELECT * FROM studio_private.webhook_events")).all()
        )
        encrypted = c.scalar(text("SELECT encrypted_payload FROM studio_private.webhook_events"))
        assert service.cipher.decrypt(encrypted, ("stripe-event", "evt_synthetic")) == raw.decode()
    for role in ("studio_web", "studio_auth_runtime"):
        with pytest.raises(ProgrammingError), role_session(db, role) as s:
            s.execute(text("SELECT * FROM studio_private.webhook_events"))


@pytest.mark.parametrize("changes", [{"livemode": True}, {"account": "acct_foreign"}, {"id": ""}])
def test_wrong_mode_account_or_id_closed(inbox, changes):
    client, _, _db = inbox
    raw = raw_event(**changes)
    assert (
        client.post(
            "/api/webhooks/stripe", content=raw, headers={"Stripe-Signature": signed(raw)}
        ).status_code
        == 400
    )
