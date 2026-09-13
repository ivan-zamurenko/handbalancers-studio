import secrets
import time
from datetime import timedelta

import pytest
from authlib.jose import JsonWebKey, JsonWebToken
from authlib.jose.errors import JoseError
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from studio.models import BrowserSession, Identity, OAuthAttempt, OnboardingProfile, utcnow
from studio.oauth import consume_attempt, finish_login, validate_id_token
from studio.security import token_hash


@pytest.fixture(scope="module")
def jwt_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public = JsonWebKey.import_key(private).as_dict(is_private=False)
    return private, {"keys": [public]}


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "https://attacker.example"},
        {"aud": "another-client"},
        {"nonce": "another-nonce"},
        {"exp": int(time.time()) - 120},
        {"azp": "another-client"},
        {"sub": ""},
    ],
)
def test_id_token_rejects_wrong_identity_context(jwt_keys, settings, change):
    settings.google_client_id = "fixture-client"
    private, keys = jwt_keys
    payload = {
        "iss": "https://accounts.google.com",
        "aud": "fixture-client",
        "sub": "provider-subject",
        "nonce": "expected-nonce",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    encoded = JsonWebToken(["RS256"]).encode({"alg": "RS256"}, payload | change, private)
    with pytest.raises((JoseError, ValueError)):
        validate_id_token(encoded, keys, settings, "google", "expected-nonce")


def test_signed_id_token_is_verified(jwt_keys, settings):
    settings.google_client_id = "fixture-client"
    private, keys = jwt_keys
    payload = {
        "iss": "https://accounts.google.com",
        "aud": "fixture-client",
        "sub": "provider-subject",
        "nonce": "expected-nonce",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    encoded = JsonWebToken(["RS256"]).encode({"alg": "RS256"}, payload, private)
    assert (
        validate_id_token(encoded, keys, settings, "google", "expected-nonce")["sub"]
        == "provider-subject"
    )


@pytest.mark.postgres
def test_oauth_state_is_browser_bound_provider_bound_and_single_use(db_factory):
    state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with db_factory() as db:
        session = BrowserSession(
            token_hash=token_hash(secrets.token_urlsafe(32)),
            expires_at=utcnow() + timedelta(hours=1),
        )
        db.add(session)
        db.flush()
        db.add(
            OAuthAttempt(
                state_hash=token_hash(state),
                session_hash=session.token_hash,
                browser_hash=token_hash(browser),
                provider="google",
                nonce="nonce",
                code_verifier="verifier",
                expires_at=utcnow() + timedelta(minutes=10),
            )
        )
        db.commit()
    with pytest.raises(ValueError):
        consume_attempt(db_factory, "google", state, secrets.token_urlsafe(32))
    with pytest.raises(ValueError):
        consume_attempt(db_factory, "apple", state, browser)
    assert consume_attempt(db_factory, "google", state, browser)["nonce"] == "nonce"
    with pytest.raises(ValueError):
        consume_attempt(db_factory, "google", state, browser)


@pytest.mark.postgres
def test_oauth_does_not_link_accounts_by_email(db_factory, settings, answers):
    from sqlalchemy import select
    from starlette.responses import Response

    for provider in ("google", "apple"):
        session_hash = token_hash(secrets.token_urlsafe(32))
        with db_factory() as db:
            db.add(
                BrowserSession(
                    token_hash=session_hash, draft=answers, expires_at=utcnow() + timedelta(hours=1)
                )
            )
            db.commit()
        finish_login(
            db_factory,
            settings,
            provider,
            {"session_hash": session_hash},
            {
                "sub": f"{provider}-subject",
                "email": "same@example.invalid",
                "email_verified": True,
                "name": "Fixture",
            },
            Response(),
        )
        with db_factory() as db:
            assert db.get(BrowserSession, session_hash) is None
    with db_factory() as db:
        identities = db.scalars(select(Identity)).all()
        assert len({identity.user_id for identity in identities}) == 2
        assert len(db.scalars(select(OnboardingProfile)).all()) == 2


@pytest.mark.postgres
def test_google_authorization_includes_pkce_and_nonce(client, settings, db_factory):
    from urllib.parse import parse_qs, urlsplit

    from pydantic import SecretStr

    settings.google_client_id = "fixture-client"
    settings.google_client_secret = SecretStr("fixture-secret")
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    assert location.hostname == "accounts.google.com"
    query = parse_qs(location.query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) >= 43
    assert "studio_oauth=" in response.headers["set-cookie"]
    assert "studio_session=" in response.headers["set-cookie"]
    with db_factory() as db:
        attempt = db.get(OAuthAttempt, token_hash(query["state"][0]))
        assert attempt and attempt.nonce == query["nonce"][0]
