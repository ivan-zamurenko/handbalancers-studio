from fastapi.testclient import TestClient
from studio.main import create_app


def test_unconfigured_provider_fail_closed():
    client = TestClient(create_app({"app_env": "test", "public_origin": "http://testserver"}))
    assert (
        client.post(
            "/api/auth/oauth/google/start", headers={"Origin": "http://testserver"}, json={}
        ).status_code
        == 503
    )
    assert (
        client.post(
            "/api/auth/oauth/apple/start", headers={"Origin": "https://evil.test"}, json={}
        ).status_code
        == 403
    )
    response = client.get(
        "/auth/callback?code=synthetic&attempt=bad&provider=google", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?oauth=unavailable"
    assert response.headers["cache-control"] == "no-store"
    assert "synthetic" not in response.text
    assert client.get("/api/session").json() == {"authenticated": False}


def test_config_requires_all_oauth_dependencies():
    import pytest
    from pydantic import ValidationError
    from studio.settings import Settings

    with pytest.raises(ValidationError):
        Settings(app_env="test", oauth_google_enabled=True)
