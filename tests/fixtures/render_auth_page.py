"""Real Jinja with explicit synthetic Auth configuration; no network or DB I/O."""

import base64
import sys

from fastapi.testclient import TestClient
from studio.main import create_app

app = create_app(
    {
        "app_env": "test",
        "public_origin": "http://127.0.0.1:8765",
        "auth_email_enabled": True,
        "oauth_google_enabled": True,
        "auth_database_url": "postgresql+psycopg://test:synthetic@127.0.0.1:55322/postgres",
        "supabase_url": "http://127.0.0.1:55321",
        "supabase_publishable_key": "synthetic-public",
        "token_encryption_key": base64.b64encode(b"a" * 32).decode(),
    }
)
path = sys.argv[1]
assert path.split("?")[0] in {"/register", "/verify-email", "/login"}
print(TestClient(app).get(path).text)
