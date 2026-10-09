"""Transaction-scoped private storage, not JWT verification or an auth endpoint.

Keys are supplied explicitly from server configuration and never persisted here.
Commit an attempt consumption BEFORE any provider exchange; rollback leaves it
available. No method commits, logs secrets, or performs external network I/O.
"""

import base64
import hashlib
import json
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from studio.auth.models import AuthAttempt, WebSession


class StoreError(ValueError):
    def __init__(self) -> None:
        super().__init__("Auth storage operation unavailable")


def _hash(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise StoreError()
    return hashlib.sha256(value.encode()).hexdigest()


def _time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _now(session: Session) -> datetime:
    if not session.in_transaction():
        raise StoreError()
    return session.execute(select(func.clock_timestamp())).scalar_one()


def _future(value: datetime, now: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None or value <= now:
        raise StoreError()


class TokenCipher:
    """Versioned AES-256-GCM envelope; supports retained keys during rotation."""

    def __init__(self, active_key_id: str, keys: Mapping[str, bytes]) -> None:
        if (
            active_key_id not in keys
            or not keys
            or any(
                not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id)
                or not isinstance(key, bytes)
                or len(key) != 32
                for key_id, key in keys.items()
            )
        ):
            raise StoreError()
        self._active = active_key_id
        self._keys = dict(keys)

    @staticmethod
    def _aad(key_id: str, context: tuple[str, ...]) -> bytes:
        return json.dumps([1, key_id, *context], separators=(",", ":")).encode()

    def encrypt(self, plaintext: str, context: tuple[str, ...]) -> str:
        if not plaintext or len(plaintext.encode()) > 65536:
            raise StoreError()
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._keys[self._active]).encrypt(
            nonce, plaintext.encode(), self._aad(self._active, context)
        )
        return json.dumps(
            {
                "v": 1,
                "key_id": self._active,
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ciphertext).decode(),
            },
            separators=(",", ":"),
        )

    def decrypt(self, envelope: str, context: tuple[str, ...]) -> str:
        try:
            if len(envelope) > 100000:
                raise ValueError
            value = json.loads(envelope)
            if set(value) != {"v", "key_id", "nonce", "ciphertext"} or value["v"] != 1:
                raise ValueError
            key_id = value["key_id"]
            nonce = base64.b64decode(value["nonce"], validate=True)
            if len(nonce) != 12:
                raise ValueError
            ciphertext = base64.b64decode(value["ciphertext"], validate=True)
            return (
                AESGCM(self._keys[key_id])
                .decrypt(nonce, ciphertext, self._aad(key_id, context))
                .decode()
            )
        except (ValueError, TypeError, KeyError, InvalidTag):
            raise StoreError() from None


@dataclass(frozen=True)
class SessionHandle:
    id: UUID
    cookie: SecretStr


@dataclass(frozen=True)
class AttemptHandle:
    id: UUID
    state: SecretStr
    binding: SecretStr


@dataclass(frozen=True)
class SessionSecrets:
    user_id: UUID
    upstream_session_id: UUID
    access_expires_at: datetime
    access_token: SecretStr
    refresh_token: SecretStr


@dataclass(frozen=True)
class AttemptSecrets:
    user_id: UUID | None
    allowed_return_path: str
    verifier: SecretStr


def _session_context(row: WebSession) -> tuple[str, ...]:
    return (
        "web_sessions",
        str(row.id),
        str(row.user_id),
        str(row.upstream_session_id),
        row.session_key_hash,
        _time(row.expires_at),
        _time(row.access_expires_at),
        "encrypted_tokens",
    )


def _attempt_context(row: AuthAttempt) -> tuple[str, ...]:
    return (
        "auth_attempts",
        str(row.id),
        str(row.user_id),
        row.provider,
        row.state_hash,
        row.nonce_hash,
        row.allowed_return_path,
        _time(row.expires_at),
        "encrypted_verifier",
    )


class TokenStore:
    def __init__(self, cipher: TokenCipher, *, allowed_return_paths: frozenset[str]) -> None:
        if not allowed_return_paths or any(
            not path.startswith("/")
            or path.startswith("//")
            or "\\" in path
            or any(ord(char) < 32 or ord(char) == 127 for char in path)
            for path in allowed_return_paths
        ):
            raise StoreError()
        self._cipher = cipher
        self._return_paths = frozenset(allowed_return_paths)

    def create_session(
        self,
        session: Session,
        *,
        user_id: UUID,
        upstream_session_id: UUID,
        access_token: str,
        refresh_token: str,
        access_expires_at: datetime,
        expires_at: datetime,
    ) -> SessionHandle:
        now = _now(session)
        _future(access_expires_at, now)
        _future(expires_at, now)
        if not access_token or not refresh_token or not isinstance(user_id, UUID):
            raise StoreError()
        cookie = secrets.token_urlsafe(32)
        row = WebSession(
            id=uuid4(),
            session_key_hash=_hash(cookie),
            user_id=user_id,
            upstream_session_id=upstream_session_id,
            access_expires_at=access_expires_at,
            expires_at=expires_at,
        )
        row.encrypted_tokens = self._cipher.encrypt(
            json.dumps({"access": access_token, "refresh": refresh_token}),
            _session_context(row),
        )
        session.add(row)
        session.flush()
        return SessionHandle(row.id, SecretStr(cookie))

    def read_session(self, session: Session, cookie: str) -> SessionSecrets:
        """Check local lifetime/revocation only; caller must verify upstream identity."""
        now = _now(session)
        row = session.execute(
            select(WebSession)
            .where(
                WebSession.session_key_hash == _hash(cookie),
                WebSession.revoked_at.is_(None),
                WebSession.expires_at > now,
            )
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if row is None:
            raise StoreError()
        try:
            payload = json.loads(self._cipher.decrypt(row.encrypted_tokens, _session_context(row)))
            if set(payload) != {"access", "refresh"} or any(
                not isinstance(value, str) or not value for value in payload.values()
            ):
                raise ValueError
        except (ValueError, TypeError):
            raise StoreError() from None
        return SessionSecrets(
            row.user_id,
            row.upstream_session_id,
            row.access_expires_at,
            SecretStr(payload["access"]),
            SecretStr(payload["refresh"]),
        )

    def revoke_session(self, session: Session, cookie: str) -> None:
        now = _now(session)
        session.execute(
            update(WebSession)
            .where(
                WebSession.session_key_hash == _hash(cookie),
                WebSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    def create_attempt(
        self,
        session: Session,
        *,
        provider: str,
        verifier: str,
        allowed_return_path: str,
        expires_at: datetime,
        user_id: UUID | None = None,
    ) -> AttemptHandle:
        now = _now(session)
        _future(expires_at, now)
        if provider not in {"google", "apple"} or allowed_return_path not in self._return_paths:
            raise StoreError()
        state, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        row = AuthAttempt(
            id=uuid4(),
            state_hash=_hash(state),
            nonce_hash=_hash(binding),
            user_id=user_id,
            provider=provider,
            allowed_return_path=allowed_return_path,
            expires_at=expires_at,
        )
        row.encrypted_verifier = self._cipher.encrypt(verifier, _attempt_context(row))
        session.add(row)
        session.flush()
        return AttemptHandle(row.id, SecretStr(state), SecretStr(binding))

    def consume_attempt(
        self,
        session: Session,
        state: str,
        *,
        provider: str,
        binding: str,
    ) -> AttemptSecrets:
        """Caller must COMMIT this transaction before using the verifier externally."""
        _now(session)
        try:
            row = session.execute(
                select(AuthAttempt)
                .where(
                    AuthAttempt.state_hash == _hash(state),
                    AuthAttempt.provider == provider,
                    AuthAttempt.nonce_hash == _hash(binding),
                )
                .with_for_update(nowait=True)
                .execution_options(
                    populate_existing=True,
                )
            ).scalar_one_or_none()
        except OperationalError as error:
            if getattr(error.orig, "sqlstate", None) == "55P03":
                raise StoreError() from None
            raise
        # Read DB time after acquiring the row lock; never exchange an expired attempt.
        now = _now(session)
        if row is None or row.consumed_at is not None or row.expires_at <= now:
            raise StoreError()
        if row.allowed_return_path not in self._return_paths:
            raise StoreError()
        verifier = self._cipher.decrypt(row.encrypted_verifier, _attempt_context(row))
        row.consumed_at = now
        session.flush()
        return AttemptSecrets(row.user_id, row.allowed_return_path, SecretStr(verifier))
