"""Minimal product profile; managed Auth metadata is reference-only."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from studio.db import Base

# A cross-schema FK needs a target Column, but auth must never enter product
# metadata/create_all/autogenerate. Supabase owns this table and its full schema.
_auth_users = Table("users", MetaData(), Column("id", Uuid, primary_key=True), schema="auth")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        CheckConstraint("role IN ('member', 'coach')", name="ck_users_role"),
        CheckConstraint("locale IN ('uk', 'en')", name="ck_users_locale"),
        CheckConstraint("row_version > 0", name="ck_users_row_version"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    auth_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey(_auth_users.c.id, name="fk_users_auth_user_id"), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'member'"))
    locale: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
