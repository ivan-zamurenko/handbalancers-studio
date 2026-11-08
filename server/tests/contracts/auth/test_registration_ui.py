"""Public auth pages are safe server-rendered forms, never credential echoes."""

import pytest
from fastapi.testclient import TestClient
from studio.main import create_app


@pytest.mark.parametrize("path", ["/register", "/verify-email", "/login"])
@pytest.mark.parametrize("language", ["uk", "en"])
def test_auth_pages_are_private_and_do_not_echo_query_credentials(path, language):
    with TestClient(create_app({"app_env": "test"})) as client:
        response = client.get(
            path, params={"lang": language, "password": "sensitive-query-marker", "token": "654321"}
        )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert f'<html lang="{language}"' in response.text
    assert "sensitive-query-marker" not in response.text
    assert "654321" not in response.text
    assert 'data-auth-enabled="false"' in response.text
    assert 'data-oauth-provider="apple"' not in response.text
    assert 'name="password"' not in response.text
    assert 'name="token"' not in response.text
