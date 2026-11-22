"""Separate narrow worker login for trusted billing; never the public web login."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from studio.billing.checkout import BillingTransaction, CheckoutService
from studio.billing.stripe_gateway import StripeGateway
from studio.db import UnsafeWebRole
from studio.settings import Settings

_WORKER_CHECK = text("""
SELECT NOT r.rolsuper AND NOT r.rolbypassrls AND NOT r.rolcreaterole
 AND pg_has_role(current_user,'studio_worker','USAGE')
 AND NOT pg_has_role(current_user,'studio_web','MEMBER')
 AND NOT pg_has_role(current_user,'studio_auth_runtime','MEMBER')
 AND NOT pg_has_role(current_user,'migration_owner','MEMBER')
 AND NOT EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname IN ('studio','studio_private')
                 AND pg_has_role(current_user,n.nspowner,'MEMBER'))
FROM pg_roles r WHERE r.rolname=current_user
""")


def billing_transaction(settings: Settings) -> BillingTransaction:
    assert settings.worker_database_url is not None
    engine = create_engine(
        settings.worker_database_url.get_secret_value(),
        hide_parameters=True,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=0,
        pool_timeout=5,
        connect_args={"connect_timeout": 5},
    )

    @contextmanager
    def transaction() -> Iterator[Session]:
        with Session(engine) as session, session.begin():
            if not session.scalar(_WORKER_CHECK):
                raise UnsafeWebRole("Billing requires a narrow studio_worker login")
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            session.execute(text("SET LOCAL lock_timeout='2s'"))
            yield session

    return transaction


def build_checkout(settings: Settings, web_transaction) -> CheckoutService | None:
    if not settings.billing_enabled:
        return None
    assert settings.stripe_secret_key and settings.public_origin and web_transaction
    gateway = StripeGateway(
        settings.stripe_secret_key,
        {
            "essential": settings.stripe_price_essential,
            "plus": settings.stripe_price_plus,
            "pro": settings.stripe_price_pro,
            "pro-plus": settings.stripe_price_pro_plus,
        },
    )
    return CheckoutService(
        transaction=billing_transaction(settings),
        web_transaction=web_transaction,
        gateway=gateway,
        origin=settings.public_origin,
    )
