"""Run the isolated local database/application without exposing credentials."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
PYTHON = ROOT / ".local-tools/python/bin/python"
PGDATA = ROOT / ".local-tools/postgres/data"


def environment() -> dict[str, str]:
    result = dict(os.environ)
    config = SERVER / ".env"
    if not config.exists():
        raise SystemExit("Missing server/.env. See docs/deployment.md; never paste credentials into chat.")
    for line in config.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def postgres_binary(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for version in ("17", "16", "15", "14"):
        candidate = Path(f"/opt/homebrew/opt/postgresql@{version}/bin/{name}")
        if candidate.exists():
            return str(candidate)
    raise SystemExit("PostgreSQL binaries not found. Use Docker Compose or install PostgreSQL.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve", "migrate", "test", "db-start", "db-stop", "db-status"])
    args = parser.parse_args()
    if args.command.startswith("db-"):
        if not (PGDATA / "PG_VERSION").exists():
            raise SystemExit("Isolated database not initialized. See docs/local-development.md.")
        binary = postgres_binary("pg_ctl")
        command = [binary, "-D", str(PGDATA)]
        if args.command == "db-start":
            sock = Path(f"/private/tmp/hbs-postgres-{os.getuid()}")
            sock.mkdir(mode=0o700, exist_ok=True)
            os.chmod(sock, 0o700)
            command += ["-l", str(PGDATA.parent / "server.log"), "-o", f"-h 127.0.0.1 -p 55432 -k {sock}", "-w", "start"]
        elif args.command == "db-stop":
            command += ["-m", "fast", "-w", "stop"]
        else:
            command += ["status"]
        raise SystemExit(subprocess.call(command))
    if not PYTHON.exists():
        raise SystemExit("Missing .local-tools/python environment. See docs/local-development.md.")
    env = environment()
    if args.command == "serve":
        command = [str(PYTHON), "-m", "uvicorn", "studio.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"]
    elif args.command == "migrate":
        command = [str(PYTHON), "-m", "alembic", "upgrade", "head"]
    else:
        # Only the dedicated local test database is used. Never reuse production data.
        url = env["DATABASE_URL"]
        if "@127.0.0.1:55432/studio" not in url:
            raise SystemExit("Tests require the isolated local PostgreSQL instance.")
        env["TEST_DATABASE_URL"] = url.rsplit("/", 1)[0] + "/studio_test"
        command = [str(PYTHON), "-m", "pytest", "-q"]
    raise SystemExit(subprocess.call(command, cwd=SERVER, env=env))


if __name__ == "__main__":
    main()
