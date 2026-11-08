import asyncio
import json
import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

ISSUER = "https://project.example.test/auth/v1"
KEY = ec.generate_private_key(ec.SECP256R1())
USER = str(uuid4())
SESSION = str(uuid4())


def signed(**changes):
    claims = {
        "iss": ISSUER,
        "aud": "authenticated",
        "sub": USER,
        "session_id": SESSION,
        "exp": int(time.time()) + 60,
        "iat": int(time.time()),
        "role": "authenticated",
        "user_metadata": {"role": "coach"},
    }
    claims.update(changes)
    return jwt.encode(claims, KEY, algorithm="ES256", headers={"kid": "first"})


def make_validator():
    from studio.auth.jwt import JWTValidator

    calls = []

    async def fetch():
        calls.append(True)
        key = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key()))
        return {"keys": [dict(key, kid="first", alg="ES256", use="sig")]}

    return JWTValidator(issuer=ISSUER, fetch_jwks=fetch), calls


def test_metadata_not_authority():
    verifier, calls = make_validator()
    identity = asyncio.run(verifier.verify(signed()))
    assert str(identity.user_id) == USER
    assert str(identity.session_id) == SESSION
    assert not hasattr(identity, "role")
    assert len(calls) == 1


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode({"sub": USER}, "", algorithm="none"),
        jwt.encode({"sub": USER}, "x" * 32, algorithm="HS256"),
    ],
)
def test_reject_unsigned(token):
    from studio.auth.jwt import InvalidIdentity

    verifier, calls = make_validator()
    with pytest.raises(InvalidIdentity):
        asyncio.run(verifier.verify(token))
    assert not calls


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://other.test/auth/v1"},
        {"aud": "other"},
        {"exp": 1},
        {"sub": "not-uuid"},
        {"session_id": None},
        {"exp": None},
        {"iat": int(time.time()) + 300},
    ],
)
def test_reject_wrong_project_expired_or_invalid_identity(changes):
    from studio.auth.jwt import InvalidIdentity

    verifier, _ = make_validator()
    with pytest.raises(InvalidIdentity):
        asyncio.run(verifier.verify(signed(**changes)))


def test_refresh_jwks_unknown_kid_is_bounded():
    from studio.auth.jwt import InvalidIdentity

    verifier, calls = make_validator()

    async def run():
        await verifier.verify(signed())
        token = jwt.encode({"sub": USER}, KEY, algorithm="ES256", headers={"kid": "unknown"})
        for _ in range(20):
            with pytest.raises(InvalidIdentity):
                await verifier.verify(token)

    asyncio.run(run())
    assert len(calls) <= 2


def test_signature_tampering_rejected():
    from studio.auth.jwt import InvalidIdentity

    verifier, _ = make_validator()
    other = ec.generate_private_key(ec.SECP256R1())
    claims = jwt.decode(signed(), options={"verify_signature": False})
    token = jwt.encode(claims, other, algorithm="ES256", headers={"kid": "first"})
    with pytest.raises(InvalidIdentity):
        asyncio.run(verifier.verify(token))


def test_rotation_refresh_after_cooldown(monkeypatch):
    from studio.auth import jwt as module

    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    verifier, calls = make_validator()

    async def run():
        await verifier.verify(signed())
        clock[0] += 31
        new_key = ec.generate_private_key(ec.SECP256R1())

        async def fetch():
            calls.append(True)
            raw = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(new_key.public_key()))
            return {"keys": [dict(raw, kid="second", alg="ES256")]}

        verifier._fetch = fetch
        token = jwt.encode(
            jwt.decode(signed(), options={"verify_signature": False}),
            new_key,
            algorithm="ES256",
            headers={"kid": "second"},
        )
        assert str((await verifier.verify(token)).user_id) == USER

    asyncio.run(run())
    assert len(calls) == 2


def test_failed_fetch_singleflight_and_cooldown():
    from studio.auth.jwt import InvalidIdentity, JWTValidator

    calls = []

    async def fetch():
        calls.append(True)
        await asyncio.sleep(0)
        raise TimeoutError("provider secret should not escape")

    verifier = JWTValidator(issuer=ISSUER, fetch_jwks=fetch)

    async def attempt():
        with pytest.raises(InvalidIdentity) as failure:
            await verifier.verify(signed())
        assert "secret" not in str(failure.value)

    async def run():
        await asyncio.gather(*(attempt() for _ in range(20)))

    asyncio.run(run())
    assert len(calls) == 1


def test_key_rotation_outage_stays_retryable_through_cooldown(monkeypatch):
    from studio.auth import jwt as module

    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    verifier, calls = make_validator()
    new_token = jwt.encode(
        {"sub": USER},
        KEY,
        algorithm="ES256",
        headers={"kid": "new-key"},
    )

    async def failed_refresh():
        calls.append(True)
        raise TimeoutError()

    async def run():
        await verifier.verify(signed())
        clock[0] += 31
        verifier._fetch = failed_refresh
        for _ in range(2):
            with pytest.raises(module.IdentityVerificationUnavailable):
                await verifier.verify(new_token)
        # A previously verified cached key still works during its valid TTL.
        assert str((await verifier.verify(signed())).user_id) == USER

    asyncio.run(run())
    assert len(calls) == 2
