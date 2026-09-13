"""Create a new private Compose env file. Never display or replace secret values."""

import argparse
import os
import re
import secrets
from pathlib import Path

HOST_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


def validate_host(value: str) -> str:
    host = value.lower()
    if not HOST_PATTERN.fullmatch(host) or host.endswith(".localhost"):
        raise argparse.ArgumentTypeError("Use a public DNS hostname without scheme, port or path")
    return host


def create_file(path: Path, host: str | None) -> None:
    template = Path(__file__).resolve().parents[1] / "server" / ".env.example"
    app_password = secrets.token_hex(32)
    values = {
        "POSTGRES_PASSWORD": secrets.token_hex(32),
        "APP_DATABASE_PASSWORD": app_password,
        "DATABASE_URL": f"postgresql+psycopg://studio:{app_password}@db:5432/studio",
        "SESSION_SECRET": secrets.token_hex(32),
        "APP_ENV": "production" if host else "development",
        "BASE_URL": f"https://{host}" if host else "http://127.0.0.1:8000",
        "STUDIO_HOST": host or "",
    }
    lines = []
    for line in template.read_text(encoding="utf-8").splitlines():
        name = line.partition("=")[0]
        lines.append(f"{name}={values[name]}" if name in values else line)
    # O_EXCL also refuses existing symlinks. The file is private from creation.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", type=validate_host, help="Production DNS hostname; omit for local")
    args = parser.parse_args()
    try:
        create_file(args.output, args.host)
    except FileExistsError:
        parser.exit(1, "Refusing to replace an existing environment file.\n")
    except OSError:
        parser.exit(1, "Could not create environment file; check directory access.\n")
    print("Private environment file created. No secret values were printed.")


if __name__ == "__main__":
    main()
