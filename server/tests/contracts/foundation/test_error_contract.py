"""Real HTTP failures expose stable codes and correlate with safe access records."""

import logging
import re

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from studio.main import create_app


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempts: int


def test_validation_envelope(test_settings):
    # Use an annotated endpoint so this exercises FastAPI/Pydantic validation.
    def login(body: LoginInput):
        return {"ok": True}

    app = create_app(test_settings)
    app.add_api_route("/auth/login", login, methods=["POST"])
    marker = "synthetic-password-only"
    with TestClient(app) as client:
        for body in ({"attempts": marker}, {"attempts": 1, marker: marker}):
            response = client.post("/auth/login", json=body)
            assert response.status_code == 422
            error = response.json()["error"]
            assert set(error) == {"code", "message_key", "field_errors", "request_id"}
            assert error["code"] == "validation_error"
            assert error["message_key"] == "errors.validation"
            assert error["field_errors"] == [
                {"field": "body", "message_key": "errors.invalid_input"}
            ]
            assert re.fullmatch(r"[0-9a-f]{32}", error["request_id"])
            assert response.headers["x-request-id"] == error["request_id"]
            assert marker not in response.text
            assert response.headers["cache-control"] == "no-store"


def test_unexpected_error_redacted(test_settings, caplog):
    app = create_app(test_settings)

    def broken():
        raise RuntimeError("SELECT secret FROM users; synthetic-db-password-only")

    app.add_api_route("/broken", broken)
    with caplog.at_level(logging.INFO), TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/broken")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["message_key"] == "errors.internal"
    assert error["field_errors"] == []
    assert response.headers["x-request-id"] == error["request_id"]
    records = [record for record in caplog.records if record.name == "studio.access"]
    assert len(records) == 1
    assert records[0].request_id == error["request_id"]
    assert records[0].status_code == 500
    for value in ("SELECT", "synthetic-db-password-only", "RuntimeError", "Traceback"):
        assert value not in response.text
        assert value not in str([record.__dict__ for record in records])


def test_no_sensitive_request_logging(test_settings, caplog):
    app = create_app(test_settings)

    def login(body: LoginInput):
        return {"ok": True}

    app.add_api_route("/auth/login", login, methods=["POST"])
    marker = "synthetic-auth-secret-only"
    with caplog.at_level(logging.INFO, logger="studio.access"), TestClient(app) as client:
        response = client.post(
            "/auth/login?token=" + marker,
            json={"attempts": marker},
            headers={
                "Cookie": "session=" + marker,
                "Authorization": "Bearer " + marker,
                "X-Request-ID": marker,
            },
        )
        second = client.get("/health/live")
    records = [record for record in caplog.records if record.name == "studio.access"]
    assert len(records) == 2
    assert marker not in str([record.__dict__ for record in records])
    assert marker not in response.text
    assert records[0].request_id == response.headers["x-request-id"]
    assert records[1].request_id == second.headers["x-request-id"]
    assert records[0].request_id != records[1].request_id


def test_http_errors_have_envelope_without_detail(test_settings):
    app = create_app(test_settings)

    def forbidden():
        raise HTTPException(status_code=403, detail="synthetic-private-detail")

    app.add_api_route("/forbidden", forbidden)
    with TestClient(app) as client:
        for method, path, status, code in [
            ("GET", "/missing", 404, "not_found"),
            ("POST", "/health/live", 405, "method_not_allowed"),
            ("GET", "/forbidden", 403, "forbidden"),
        ]:
            response = client.request(method, path)
            assert response.status_code == status
            assert response.json()["error"]["code"] == code
            assert "synthetic-private-detail" not in response.text
            if status == 405:
                assert "GET" in response.headers["allow"]


def test_uvicorn_raw_access_records_are_suppressed(test_settings, caplog):
    create_app(test_settings)
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info("/login?token=synthetic-url-secret")
    assert not [record for record in caplog.records if record.name == "uvicorn.access"]
