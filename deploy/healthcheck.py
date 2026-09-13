"""Container readiness without credentials, response bodies or query strings in logs."""

import os
import sys
from http.client import HTTPException
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main() -> int:
    host = urlsplit(os.environ.get("BASE_URL", "")).netloc
    if not host:
        return 1
    request = Request("http://127.0.0.1:8000/health/ready", headers={"Host": host})
    try:
        with urlopen(request, timeout=3) as response:
            return 0 if response.status == 200 else 1
    except (OSError, HTTPException, ValueError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
