"""One transaction-scoped SQLAlchemy session per request; migrations are explicit."""

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from studio.settings import Settings


def make_engine(settings: Settings):
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        echo=False,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db
