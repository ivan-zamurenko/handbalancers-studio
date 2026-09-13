"""Integration tests create and remove only their own random schema in a local *_test DB."""

import os
import secrets
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from studio.db import make_session_factory
from studio.models import Base
from studio.settings import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/studio_test",
        session_secret=secrets.token_urlsafe(32),
        app_env="development",
        local_preview=True,
        base_url="http://127.0.0.1:8000",
    )


@pytest.fixture
def db_factory():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    url = make_url(dsn)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not url.database
        or not url.database.endswith("_test")
    ):
        pytest.fail("Tests require a local PostgreSQL database whose name ends with _test")
    schema = "test_" + uuid.uuid4().hex
    administration = create_engine(url, hide_parameters=True, isolation_level="AUTOCOMMIT")
    with administration.connect() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(
        url, hide_parameters=True, connect_args={"options": f"-csearch_path={schema}"}
    )
    try:
        Base.metadata.create_all(engine)
        yield make_session_factory(engine)
    finally:
        engine.dispose()
        with administration.connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        administration.dispose()


@pytest.fixture
def client(settings, db_factory, monkeypatch):
    # main's ASGI entry point requires configuration even when a factory is injected below.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/studio_test")
    monkeypatch.setenv("SESSION_SECRET", secrets.token_urlsafe(32))
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("BASE_URL", settings.base_url)
    from fastapi.testclient import TestClient

    from studio.main import create_app

    with TestClient(
        create_app(settings, db_factory), base_url=settings.base_url, client=("127.0.0.1", 50000)
    ) as test_client:
        yield test_client


@pytest.fixture
def answers():
    return {
        "goals": ["handstand", "strength"],
        "experience": "beginner",
        "days": [0, 2, 4],
        "minutes": 30,
        "minutes_plus": False,
        "timezone": "Europe/Kyiv",
        "locale": "uk",
    }


def csrf_headers(client):
    state = client.get("/api/session").json()
    return {"Origin": str(client.base_url).rstrip("/"), "X-CSRF-Token": state["csrf_token"]}


def register_demo(client, answers):
    headers = csrf_headers(client)
    assert client.post("/api/onboarding", json=answers, headers=headers).status_code == 200
    assert (
        client.post("/api/preview/register", json={"name": "Тест"}, headers=headers).status_code
        == 200
    )
    return csrf_headers(client)
