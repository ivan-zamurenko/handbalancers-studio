from fastapi.testclient import TestClient
from studio.main import create_app


def test_oauth_feedback_and_unconfigured_buttons():
    client = TestClient(create_app({"app_env": "test"}))
    html = client.get("/login?oauth=cancelled").text
    assert "Вхід скасовано" in html
    assert "data-oauth-provider" not in html
    html = client.get("/login?oauth=%3Cscript%3E").text
    assert "<script>" not in html
