"""Real public templates with synthetic registration availability, no auth provider."""

import json
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from studio.main import create_app

app = create_app({"app_env": "test"})
# Presentation flag only: do not install a fake auth runtime or provider credentials.
if "--google-only" in sys.argv:
    app.state.oauth_service = SimpleNamespace(providers=frozenset({"google"}))
else:
    app.state.settings = app.state.settings.model_copy(update={"auth_email_enabled": True})
with TestClient(app) as client:
    print(
        json.dumps(
            {
                f"{path}?lang={lang}": client.get(f"{path}?lang={lang}").text
                for path in ("/", "/plans")
                for lang in ("uk", "en")
            }
        )
    )
