"""Explicit opt-in OAuth runtime. Building the app opens no network connections."""

import base64
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from studio.auth.gateway import AuthGateway
from studio.auth.jwt import JWTValidator
from studio.auth.oauth import OAuthService
from studio.auth.rate_limit import AuthLimits
from studio.auth.supabase_adapter import SupabaseAuthAdapter
from studio.auth.token_store import TokenCipher, TokenStore
from studio.settings import Settings


def build_oauth(settings: Settings) -> OAuthService | None:
    providers = frozenset({"google"}) if settings.oauth_google_enabled else frozenset()
    if not providers and not settings.auth_email_enabled:
        return None
    assert settings.auth_database_url and settings.token_encryption_key
    assert settings.supabase_url and settings.supabase_publishable_key and settings.public_origin
    engine = create_engine(
        settings.auth_database_url.get_secret_value(),
        hide_parameters=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        connect_args={"connect_timeout": 5},
    )

    @contextmanager
    def transaction():
        with Session(engine) as session, session.begin():
            # The supplied login must already hold the narrow auth role. Never
            # elevate privileges or accept an owner/BYPASSRLS connection.
            check_auth_role(session)
            session.execute(text("SET LOCAL statement_timeout='5s'"))
            session.execute(text("SET LOCAL lock_timeout='2s'"))
            yield session

    store = TokenStore(
        TokenCipher(
            "v1",
            {
                "v1": base64.b64decode(
                    settings.token_encryption_key.get_secret_value(), validate=True
                )
            },
        ),
        allowed_return_paths=frozenset({"/plans", "/dashboard"}),
    )
    return OAuthService(
        auth_transaction=transaction,
        store=store,
        gateway=AuthGateway(
            SupabaseAuthAdapter(
                settings.supabase_url, settings.supabase_publishable_key.get_secret_value()
            )
        ),
        validator=JWTValidator(issuer=settings.supabase_url.rstrip("/") + "/auth/v1"),
        supabase_url=settings.supabase_url,
        public_origin=settings.public_origin,
        providers=providers,
        limits=AuthLimits(
            client=settings.auth_client_attempts_per_minute,
            account=settings.auth_account_attempts_per_minute,
        ),
        secret=base64.b64decode(settings.token_encryption_key.get_secret_value(), validate=True),
    )


def check_auth_role(session: Session) -> None:
    safe = session.execute(
        text("""
SELECT NOT r.rolsuper AND NOT r.rolbypassrls AND NOT r.rolcreaterole
    AND pg_has_role(current_user, 'studio_auth_runtime', 'USAGE')
    AND NOT pg_has_role(current_user, 'migration_owner', 'MEMBER')
    AND NOT EXISTS (
        SELECT 1 FROM pg_namespace n
        WHERE n.nspname IN ('studio', 'studio_private')
        AND pg_has_role(current_user, n.nspowner, 'MEMBER'))
    AND NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('studio', 'studio_private')
        AND pg_has_role(current_user, c.relowner, 'MEMBER'))
FROM pg_roles r WHERE r.rolname=current_user
""")
    ).scalar_one()
    if not safe:
        raise ValueError("Unsafe auth database role")
