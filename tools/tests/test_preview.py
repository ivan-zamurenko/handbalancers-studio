"""Motion studies are available only through explicit credential-free local tooling."""

import pytest
from fastapi.testclient import TestClient

from tools.serve_preview import create_preview_app


@pytest.mark.parametrize("origin", ["http://127.0.0.1:8000", "http://127.0.0.1:8765"])
def test_preview_ignores_inherited_credentials_and_serves_studies(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_EMAIL_ENABLED", "true")
    monkeypatch.setenv("OAUTH_GOOGLE_ENABLED", "true")
    app = create_preview_app(origin)
    assert app.state.settings.auth_email_enabled is False
    assert app.state.oauth_service is None
    with TestClient(app) as client:
        for path in ["index.html", "cycle.html", "options.js", "overview.gif"]:
            assert client.get("/_previews/handstand/" + path).status_code == 200
        assert client.get("/static/previews/handstand/index.html").status_code == 404
        assert client.get("/_previews/%2e%2e/serve_preview.py").status_code == 404


@pytest.mark.parametrize("origin", ["https://example.com", "http://0.0.0.0:8000", ""])
def test_preview_rejects_nonlocal_origin(origin):
    with pytest.raises(ValueError, match="owned local origin"):
        create_preview_app(origin)
