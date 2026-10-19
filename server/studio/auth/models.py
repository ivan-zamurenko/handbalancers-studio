"""Private transport records, not managed Supabase identities."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from studio.accounts.models import User
from studio.db import Base


class WebSession(Base):
    __tablename__ = "web_sessions"
    __table_args__ = (
        CheckConstraint("session_key_hash ~ '^[0-9a-f]{64}$'", name="ck_sessions_hash"),
        CheckConstraint("row_version > 0", name="ck_sessions_version"),
        {"schema": "studio_private"},
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey(User.id), nullable=False, index=True)
    upstream_session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    encrypted_tokens: Mapped[str] = mapped_column(Text, nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class AuthAttempt(Base):
    __tablename__ = "auth_attempts"
    __table_args__ = (
        CheckConstraint("state_hash ~ '^[0-9a-f]{64}$'", name="ck_attempts_state"),
        CheckConstraint("nonce_hash ~ '^[0-9a-f]{64}$'", name="ck_attempts_nonce"),
        CheckConstraint("provider IN ('google', 'apple')", name="ck_attempts_provider"),
        {"schema": "studio_private"},
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    state_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey(User.id), index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_verifier: Mapped[str] = mapped_column(Text, nullable=False)
    nonce_hash: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_return_path: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (CheckConstraint("attempts BETWEEN 1 AND 11"), {"schema": "studio_private"})
    bucket_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
