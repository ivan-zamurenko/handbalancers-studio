"""Disposable local Auth identities for the isolated test stack only.

Codes are read from the loopback mail catcher and the message is deleted there;
nothing is written to disk or sent elsewhere.
"""

import json
import re
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx

from tools import local_stack

MAIL_CATCHER_HOST = "127.0.0.1"
MAIL_CATCHER = f"http://{MAIL_CATCHER_HOST}:55324"
CODE = re.compile(r"\b[0-9]{6}\b")


class UnsafeMailCatcher(ValueError):
    pass


def disposable_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.test"


def _client(base_url: str) -> httpx.Client:
    if urlsplit(base_url).hostname != MAIL_CATCHER_HOST:
        raise UnsafeMailCatcher("Only the loopback local mail catcher is allowed")
    return httpx.Client(base_url=base_url, timeout=5, trust_env=False)


def _matching(mail: httpx.Client, email: str) -> list[str]:
    messages = mail.get("/api/v1/messages").raise_for_status().json()["messages"]
    return [
        message["ID"]
        for message in messages
        if any(recipient["Address"] == email for recipient in message["To"])
    ]


def messages_for(email: str, *, base_url: str = MAIL_CATCHER) -> list[str]:
    with _client(base_url) as mail:
        return _matching(mail, email)


def read_code(email: str, *, base_url: str = MAIL_CATCHER, attempts: int = 40) -> str:
    with _client(base_url) as mail:
        for _ in range(attempts):
            ids = _matching(mail, email)
            if ids:
                body = mail.get(f"/api/v1/message/{ids[0]}").raise_for_status().json()
                mail.request("DELETE", "/api/v1/messages", json={"IDs": ids}).raise_for_status()
                match = CODE.search(body["Text"])
                if match is None:
                    raise AssertionError("Local email must contain a six-digit code")
                return match.group(0)
            time.sleep(0.1)
    raise TimeoutError("Local email did not arrive within bounded wait")


def managed_user(auth_id: UUID) -> dict[str, Any] | None:
    """Read-only lookup in the guarded test container's managed auth.users."""
    container = local_stack.verify_container("test")
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            container["Id"],
            "psql",
            "-X",
            "-q",
            "-tA",
            "--no-password",
            "-U",
            "supabase_admin",
            "-d",
            "postgres",
            "--set",
            "ON_ERROR_STOP=1",
            "-v",
            f"id={UUID(str(auth_id))}",
        ],
        input=(
            "BEGIN READ ONLY;\n"
            "SELECT json_build_object('email', email, 'confirmed', email_confirmed_at IS NOT NULL)"
            " FROM auth.users WHERE id = :'id';\n"
            "COMMIT;\n"
        ),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
        env=local_stack.docker_environment(),
    )
    rows = [line for line in result.stdout.splitlines() if line.startswith("{")]
    return json.loads(rows[0]) if rows else None
