"""Test-only role switching on a guarded operator connection, never app runtime."""

from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

ROLE_SQL = {
    "studio_web": "SET LOCAL ROLE studio_web",
    "studio_auth_runtime": "SET LOCAL ROLE studio_auth_runtime",
    "studio_worker": "SET LOCAL ROLE studio_worker",
}


@contextmanager
def role_session(engine, role, user_id=None):
    with Session(engine) as session, session.begin():
        session.execute(text(ROLE_SQL[role]))
        assert session.scalar(text("SELECT current_user")) == role
        assert session.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one() == (False, False)
        session.execute(
            text("SELECT set_config('studio.user_id', :id, true)"),
            {"id": str(user_id) if user_id is not None else ""},
        )
        yield session
