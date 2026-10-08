"""Isolated local Supabase profiles. Test execution never starts or resets a stack."""

import argparse
import fcntl
import json
import os
import secrets
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {"dev": "handbalancer-studio-dev", "test": "handbalancer-studio-test"}
CLI_VERSION = "2.120.0"


class UnsafeDatabaseTarget(ValueError):
    pass


def config_text(config: dict[str, Any], section: str = "") -> str:
    lines = [f"[{section}]"] if section else []
    lines.extend(
        f"{key} = {json.dumps(value)}"
        for key, value in config.items()
        if not isinstance(value, dict)
    )
    for key, value in config.items():
        if isinstance(value, dict):
            lines.append(config_text(value, f"{section}.{key}" if section else key))
    return "\n".join(lines) + "\n"


def prepare(profile: str, *, root: Path = ROOT) -> Path:
    if profile not in PROJECTS:
        raise UnsafeDatabaseTarget("Only the dev and test profiles are allowed")
    config = tomllib.loads((ROOT / "supabase/config.toml").read_text())
    config["project_id"] = PROJECTS[profile]
    if profile == "test":
        for section in ("api", "db", "studio", "inbucket", "analytics"):
            config[section]["port"] += 1000
        config["db"]["shadow_port"] += 1000
        config["db"]["pooler"]["port"] += 1000
        config["inbucket"]["smtp_port"] += 1000
        config["inbucket"]["pop3_port"] += 1000
        config["edge_runtime"]["inspector_port"] += 1000
        config["auth"]["site_url"] = "http://127.0.0.1:8765"
    workdir = root / ".local-tools/supabase" / profile
    directory = workdir / "supabase"
    directory.mkdir(parents=True, exist_ok=True)
    with (workdir / ".prepare.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = workdir / "credentials.json"
        if not path.exists():
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as output:
                json.dump(
                    {"db_password": secrets.token_hex(32), "jwt_secret": secrets.token_hex(32)},
                    output,
                )
        if (directory / "signing_keys.json").exists():
            config["auth"]["signing_keys_path"] = "./signing_keys.json"
        (directory / "config.toml").write_text(config_text(config))
    return workdir


def docker_environment() -> dict[str, str]:
    host = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
    if os.environ.get("DOCKER_CONTEXT", "default") != "default" or not host.startswith("unix:///"):
        raise UnsafeDatabaseTarget("Only an explicit local Docker Unix socket is allowed")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"}
    }
    environment["DOCKER_HOST"] = host
    environment["DOCKER_CONFIG"] = str(ROOT / ".local-tools/docker-client")
    return environment


def inspect_database(project_id: str) -> dict[str, Any]:
    environment = docker_environment()
    try:
        result = subprocess.run(
            ["docker", "container", "inspect", f"supabase_db_{project_id}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            env=environment,
        )
        containers = json.loads(result.stdout)
        if not isinstance(containers, list) or len(containers) != 1:
            raise ValueError
        if not isinstance(containers[0], dict):
            raise TypeError
        return containers[0]
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        raise UnsafeDatabaseTarget("Local Docker database cannot be verified") from None


def read_credentials(workdir: Path) -> dict[str, str]:
    path = workdir / "credentials.json"
    try:
        value = json.loads(path.read_text())
        if path.stat().st_mode & 0o077 or not isinstance(value, dict):
            raise ValueError
        for key in ("db_password", "jwt_secret"):
            if not isinstance(value.get(key), str) or len(value[key]) != 64:
                raise ValueError
            if any(character not in "0123456789abcdef" for character in value[key]):
                raise ValueError
        return value
    except (OSError, ValueError):
        raise UnsafeDatabaseTarget("Prepare private local credentials before starting") from None


def cli_output(command: list[str], workdir: Path, environment: dict[str, str]) -> str:
    try:
        result = subprocess.run(
            ["supabase", *command],
            cwd=workdir,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=600 if command[0] == "start" else 30,
        )
        if result.returncode:
            raise UnsafeDatabaseTarget("Local Supabase command failed; output withheld")
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise UnsafeDatabaseTarget("Local Supabase CLI is unavailable or timed out") from None


def start(profile: str, *, root: Path = ROOT) -> None:
    environment = docker_environment()
    workdir = prepare(profile, root=root)
    with (workdir / ".prepare.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        credentials = read_credentials(workdir)
        environment.update(
            SUPABASE_AUTH_JWT_SECRET=credentials["jwt_secret"],
            SUPABASE_EXPERIMENTAL_STACK="0",
        )
        if cli_output(["--version"], workdir, environment).strip() != CLI_VERSION:
            raise UnsafeDatabaseTarget(f"Supabase CLI {CLI_VERSION} is required")
        key_path = workdir / "supabase/signing_keys.json"
        if not key_path.exists():
            output = cli_output(
                ["gen", "signing-key", "--algorithm", "ES256", "--output", "json"],
                workdir,
                environment,
            )
            try:
                key = json.loads(output)
                if key["kty"] != "EC" or key["alg"] != "ES256" or not key["d"]:
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                raise UnsafeDatabaseTarget("CLI did not generate an ES256 private key") from None
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as key_file:
                json.dump([key], key_file)
        config_path = workdir / "supabase/config.toml"
        config = tomllib.loads(config_path.read_text())
        config["auth"]["signing_keys_path"] = "./signing_keys.json"
        config_path.write_text(config_text(config))
        cli_output(["start", "--workdir", str(workdir)], workdir, environment)
        provision_local_login(profile, root=root)


def verify_test_target(
    *,
    app_env: str,
    database_url: str,
    supabase_url: str,
    project_id: str,
    environment: Mapping[str, str] | None = None,
) -> None:
    environment = os.environ if environment is None else environment
    if any(key.startswith("PG") for key in environment):
        raise UnsafeDatabaseTarget("libpq environment overrides are forbidden for test connections")
    if app_env != "test" or project_id != PROJECTS["test"]:
        raise UnsafeDatabaseTarget("Test environment and dedicated project are required")
    try:
        database = urlsplit(database_url)
        api = urlsplit(supabase_url)
        valid = (
            database.scheme in {"postgresql", "postgresql+psycopg"}
            and database.username == "studio_local_test"
            and database.hostname == "127.0.0.1"
            and database.port == 55322
            and database.path == "/postgres"
            and not database.query
            and not database.fragment
            and api.scheme == "http"
            and api.hostname == "127.0.0.1"
            and api.port == 55321
            and api.path in {"", "/"}
            and api.username is None
            and api.password is None
            and not api.query
            and not api.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise UnsafeDatabaseTarget("Only dedicated loopback test endpoints are allowed")
    verify_container("test")


def verify_container(profile: str) -> dict[str, Any]:
    if profile not in PROJECTS:
        raise UnsafeDatabaseTarget("Only local dev and test profiles are allowed")
    project_id = PROJECTS[profile]
    port = "55322" if profile == "test" else "54322"
    container = inspect_database(project_id)
    name = f"supabase_db_{project_id}"
    try:
        valid = (
            container["Name"] == f"/{name}"
            and container["State"]["Running"] is True
            and container["Config"]["Labels"]["com.supabase.cli.project"] == project_id
            and any(
                binding["HostPort"] == port and binding["HostIp"] in {"127.0.0.1", "0.0.0.0"}
                for binding in container["NetworkSettings"]["Ports"]["5432/tcp"]
            )
            and any(
                mount["Type"] == "volume"
                and mount["Name"] == name
                and mount["Destination"] == "/var/lib/postgresql/data"
                for mount in container["Mounts"]
            )
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise UnsafeDatabaseTarget("Running test container, port and volume markers are required")
    return container


def provision_local_login(profile: str, *, root: Path = ROOT) -> None:
    container = verify_container(profile)
    credentials = read_credentials(root / ".local-tools/supabase" / profile)
    username = f"studio_local_{profile}"
    password = credentials["db_password"]
    sql = f"""
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10s';
SELECT pg_advisory_xact_lock(190101);
DO $local_login$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{username}') THEN
        CREATE ROLE {username};
    END IF;
END
$local_login$;
ALTER ROLE {username} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD '{password}';
GRANT CONNECT, TEMPORARY ON DATABASE postgres TO {username};
COMMIT;
"""
    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container["Id"],
                "psql",
                "-X",
                "--no-password",
                "-U",
                "supabase_admin",
                "-d",
                "postgres",
                "--set",
                "ON_ERROR_STOP=1",
            ],
            input=sql,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
            env=docker_environment(),
        )
    except (OSError, subprocess.SubprocessError, KeyError):
        raise UnsafeDatabaseTarget("Could not provision the verified local login") from None


def run_tests(command: list[str], *, root: Path = ROOT) -> int:
    if not command:
        raise UnsafeDatabaseTarget("An explicit test command is required")
    environment = os.environ.copy()
    environment["APP_ENV"] = "test"
    workdir = root / ".local-tools/supabase/test"
    password = ""
    if (workdir / "credentials.json").exists():
        password = ":" + read_credentials(workdir)["db_password"]
    environment.setdefault(
        "DATABASE_URL", f"postgresql://studio_local_test{password}@127.0.0.1:55322/postgres"
    )
    environment.setdefault("SUPABASE_URL", "http://127.0.0.1:55321")
    environment.setdefault("SUPABASE_PROJECT_ID", PROJECTS["test"])
    environment = {
        key: value
        for key, value in environment.items()
        if not key.startswith("PG")
        and (not key.startswith("SUPABASE_") or key in {"SUPABASE_URL", "SUPABASE_PROJECT_ID"})
    }
    verify_test_target(
        app_env=environment["APP_ENV"],
        database_url=environment["DATABASE_URL"],
        supabase_url=environment["SUPABASE_URL"],
        project_id=environment["SUPABASE_PROJECT_ID"],
        environment=environment,
    )
    return subprocess.run(command, cwd=root, env=environment, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("profile", choices=PROJECTS)
    start_parser = commands.add_parser("start")
    start_parser.add_argument("profile", choices=PROJECTS)
    test_parser = commands.add_parser("test")
    test_parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            print(prepare(args.profile).relative_to(ROOT))
            return 0
        if args.action == "start":
            start(args.profile)
            print(f"Local {args.profile} stack started; credentials remain private")
            return 0
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        return run_tests(command)
    except (UnsafeDatabaseTarget, OSError):
        print(
            "Local stack refused: check local prerequisites and isolated test target",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
