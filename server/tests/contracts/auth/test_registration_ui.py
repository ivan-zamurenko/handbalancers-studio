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


@pytest.mark.parametrize(
    ("language", "hint"),
    [
        ("uk", "Якщо акаунт із цією адресою вже існує, лист не надійде"),
        ("en", "If an account with this address already exists, no email will arrive"),
    ],
)
def test_verify_page_neutral_existing_account_hint(language, hint):
    with TestClient(create_app({"app_env": "test"})) as client:
        response = client.get("/verify-email", params={"lang": language})
    assert hint in response.text
    assert f'href="/login?lang={language}"' in response.text


@pytest.mark.parametrize("language", ["uk", "en"])
def test_login_page_has_no_separate_verify_link(language):
    with TestClient(create_app({"app_env": "test"})) as client:
        response = client.get("/login", params={"lang": language})
    assert 'href="/verify-email' not in response.text
    assert f'href="/recovery?lang={language}"' in response.text


@pytest.mark.parametrize("path", ["/", "/login", "/register", "/verify-email"])
def test_single_brand_logo_in_header(path):
    with TestClient(create_app({"app_env": "test"})) as client:
        response = client.get(path)
    assert response.text.count('class="wordmark"') == 1
    header = response.text.split('<header class="site-header">', 1)[1].split("</header>", 1)[0]
    assert 'class="wordmark"' in header
    assert "Handbalancer’s Studio</span>" in response.text.split("<footer", 1)[1]
