"""UI fixture only: real Jinja HTML, synthetic provider availability; no OAuth runtime."""
from types import SimpleNamespace
from fastapi.testclient import TestClient
from studio.main import create_app
app = create_app({'app_env':'test'})
app.state.oauth_service = SimpleNamespace(providers=frozenset({'google'}))
print(TestClient(app).get('/login').text)
