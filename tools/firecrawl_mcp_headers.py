"""Codex-only header protocol. Never run this helper to display real credentials."""

import json
import os
import re
import sys
from pathlib import Path


def auth_headers(environ: dict[str, str], credential_file: Path) -> dict[str, str]:
    if environ.get("FIRECRAWL_API_KEY"):
        key = environ["FIRECRAWL_API_KEY"]
        url = environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
    else:
        if not credential_file.exists():
            return {}
        data = json.loads(credential_file.read_text())
        key = data.get("apiKey")
        if not key:
            return {}
        url = data.get("apiUrl", "https://api.firecrawl.dev")
    if (
        not isinstance(key, str)
        or not re.fullmatch(r"fc-[A-Za-z0-9_-]+", key)
        or not isinstance(url, str)
        or url.rstrip("/") != "https://api.firecrawl.dev"
    ):
        raise ValueError("Invalid Firecrawl credential configuration")
    return {"Authorization": "Bearer " + key}


def credential_path() -> Path:
    home_dir = Path.home()
    if sys.platform == "darwin":
        return home_dir / "Library/Application Support/firecrawl-cli/credentials.json"
    if sys.platform == "win32":
        return home_dir / "AppData/Roaming/firecrawl-cli/credentials.json"
    return home_dir / ".config/firecrawl-cli/credentials.json"


if __name__ == "__main__":
    try:
        headers = auth_headers(dict(os.environ), credential_path())
    except (OSError, ValueError, TypeError, AttributeError):
        print("Firecrawl credential configuration is unavailable", file=sys.stderr)
        raise SystemExit(1) from None
    # stdout is consumed privately by Codex's documented http_headers_helper protocol.
    print(json.dumps(headers))
