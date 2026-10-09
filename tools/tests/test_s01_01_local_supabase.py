"""Local database access must fail closed before any test command runs."""

import importlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


class LocalSupabaseTests(unittest.TestCase):
    def stack(self):
        self.assertTrue((ROOT / "tools/local_stack.py").is_file(), "Local stack guard is absent")
        return importlib.import_module("tools.local_stack")

    def container(self):
        return {
            "Id": "test-container-id",
            "Name": "/supabase_db_handbalancer-studio-test",
            "State": {"Running": True},
            "Config": {"Labels": {"com.supabase.cli.project": "handbalancer-studio-test"}},
            "NetworkSettings": {
                "Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55322"}]}
            },
            "Mounts": [
                {
                    "Type": "volume",
                    "Name": "supabase_db_handbalancer-studio-test",
                    "Destination": "/var/lib/postgresql/data",
                }
            ],
        }

    def verify(self, stack, **overrides):
        arguments = {
            "app_env": "test",
            "database_url": "postgresql://studio_local_test:secret@127.0.0.1:55322/postgres",
            "supabase_url": "http://127.0.0.1:55321",
            "project_id": "handbalancer-studio-test",
        }
        arguments.update(overrides)
        return stack.verify_test_target(**arguments)

    def test_reject_remote_host(self):
        stack = self.stack()
        urls = {
            "database_url": [
                "postgresql://studio_local_test:secret@db.example.com:55322/postgres",
                "postgresql://studio_local_test:secret@127.0.0.1:54322/postgres",
                "postgresql://studio_local_test:secret@127.0.0.1:55322/postgres?host=db.example.com",
                "postgresql://studio_local_test:secret@127.0.0.1:55322/production",
            ],
            "supabase_url": [
                "https://project.supabase.co",
                "http://127.0.0.1:54321",
                "http://127.0.0.1:55321@evil.example",
                "http://127.0.0.1:55321/proxy",
            ],
        }
        with patch.object(stack.subprocess, "run") as run:
            for field, values in urls.items():
                for value in values:
                    with (
                        self.subTest(field=field, value=value),
                        self.assertRaises(stack.UnsafeDatabaseTarget),
                    ):
                        self.verify(stack, **{field: value})
            run.assert_not_called()

    def test_verify_test_marker(self):
        stack = self.stack()
        with patch.object(stack, "inspect_database", return_value=self.container()) as inspect:
            self.verify(stack)
            inspect.assert_called_once_with("handbalancer-studio-test")
        invalid = []
        for field, value in (
            ("Name", "/supabase_db_handbalancer-studio-dev"),
            ("State", {"Running": False}),
            ("Config", {"Labels": {}}),
            ("Config", {"Labels": {"com.supabase.cli.project": "handbalancer-studio-dev"}}),
            ("NetworkSettings", {"Ports": {"5432/tcp": [{"HostPort": "54322"}]}}),
            ("Mounts", []),
        ):
            container = deepcopy(self.container())
            container[field] = value
            invalid.append(container)
        invalid.append({})
        container = self.container()
        container["Mounts"][0]["Name"] = "supabase_db_handbalancer-studio-dev"
        invalid.append(container)
        for container in invalid:
            with (
                self.subTest(container=container),
                patch.object(stack, "inspect_database", return_value=container),
                self.assertRaises(stack.UnsafeDatabaseTarget),
            ):
                self.verify(stack)

    def test_app_env_and_project_are_not_sufficient(self):
        stack = self.stack()
        with patch.object(stack, "inspect_database", return_value=self.container()) as inspect:
            for overrides in ({"app_env": "dev"}, {"project_id": "handbalancer-studio-dev"}):
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    self.verify(stack, **overrides)
            inspect.assert_not_called()

    def test_only_dedicated_test_login_is_allowed(self):
        stack = self.stack()
        with patch.object(stack, "inspect_database", return_value=self.container()) as inspect:
            for username in ("postgres", "studio_local_dev"):
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    self.verify(
                        stack,
                        database_url=f"postgresql://{username}:secret@127.0.0.1:55322/postgres",
                    )
            inspect.assert_not_called()

    def test_docker_failure_is_closed_and_redacted(self):
        stack = self.stack()
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired("docker", 10)):
            with patch.object(stack.subprocess, "run", side_effect=failure):
                with self.assertRaises(stack.UnsafeDatabaseTarget) as error:
                    self.verify(stack)
                self.assertNotIn("secret", str(error.exception))

    def test_profiles_have_separate_projects_ports_and_workdirs(self):
        stack = self.stack()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configs = []
            for profile in ("dev", "test"):
                workdir = stack.prepare(profile, root=root)
                config = tomllib.loads((workdir / "supabase/config.toml").read_text())
                configs.append(config)
                self.assertIn(profile, workdir.parts)
                self.assertEqual(config["project_id"], f"handbalancer-studio-{profile}")
                self.assertFalse(config["db"]["seed"]["enabled"])
                self.assertFalse(config["db"]["migrations"]["enabled"])
                self.assertEqual(stack.prepare(profile, root=root), workdir)
            dev_ports = {
                configs[0][section]["port"] for section in ("api", "db", "studio", "inbucket")
            }
            test_ports = {
                configs[1][section]["port"] for section in ("api", "db", "studio", "inbucket")
            }
            self.assertTrue(dev_ports.isdisjoint(test_ports))
            self.assertNotEqual(configs[0]["db"]["shadow_port"], configs[1]["db"]["shadow_port"])

    def test_no_implicit_reset(self):
        stack = self.stack()
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(stack, "verify_test_target") as verify,
                patch.object(
                    stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
                ) as run,
            ):
                result = stack.run_tests([sys.executable, "-m", "pytest"], root=Path(directory))
            self.assertEqual(result, 0)
            verify.assert_called_once()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0], [sys.executable, "-m", "pytest"])
            environment = run.call_args.kwargs["env"]
            self.assertEqual(environment["APP_ENV"], "test")
            self.assertIn(":55322/", environment["DATABASE_URL"])
            self.assertEqual(environment["SUPABASE_URL"], "http://127.0.0.1:55321")
            self.assertFalse((Path(directory) / ".local-tools").exists())

    def test_failed_guard_never_launches_tests(self):
        stack = self.stack()
        with (
            patch.object(
                stack, "verify_test_target", side_effect=stack.UnsafeDatabaseTarget("unsafe")
            ),
            patch.object(stack.subprocess, "run") as run,
        ):
            with self.assertRaises(stack.UnsafeDatabaseTarget):
                stack.run_tests([sys.executable, "-m", "pytest"])
            run.assert_not_called()

    def test_reject_remote_docker_before_inspection(self):
        stack = self.stack()
        for environment in ({"DOCKER_HOST": "tcp://remote:2375"}, {"DOCKER_CONTEXT": "production"}):
            with (
                patch.dict("os.environ", environment, clear=True),
                patch.object(stack.subprocess, "run") as run,
            ):
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    stack.inspect_database("handbalancer-studio-test")
                run.assert_not_called()

    def test_local_docker_socket_is_explicit(self):
        stack = self.stack()
        result = subprocess.CompletedProcess([], 0, json.dumps([self.container()]))
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(stack.subprocess, "run", return_value=result) as run,
        ):
            stack.inspect_database("handbalancer-studio-test")
            self.assertEqual(
                run.call_args.kwargs["env"]["DOCKER_HOST"], "unix:///var/run/docker.sock"
            )
            self.assertNotIn("DOCKER_CONTEXT", run.call_args.kwargs["env"])

    def test_docker_client_does_not_inherit_global_credentials(self):
        stack = self.stack()
        with patch.dict("os.environ", {"DOCKER_CONFIG": "/production/docker"}, clear=True):
            environment = stack.docker_environment()
        self.assertEqual(environment.get("DOCKER_CONFIG"), str(ROOT / ".local-tools/docker-client"))

    def test_profile_credentials_are_private_distinct_and_stable(self):
        stack = self.stack()
        with tempfile.TemporaryDirectory() as directory:
            profiles = []
            for profile in ("dev", "test"):
                workdir = stack.prepare(profile, root=Path(directory))
                path = workdir / "credentials.json"
                self.assertTrue(path.is_file(), "Profile credentials are absent")
                original = path.read_bytes()
                credentials = json.loads(original)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertGreaterEqual(len(credentials["db_password"]), 32)
                self.assertGreaterEqual(len(credentials["jwt_secret"]), 32)
                stack.prepare(profile, root=Path(directory))
                self.assertEqual(path.read_bytes(), original)
                profiles.append(credentials)
            self.assertNotEqual(profiles[0]["db_password"], profiles[1]["db_password"])
            self.assertNotEqual(profiles[0]["jwt_secret"], profiles[1]["jwt_secret"])

    def test_runner_preserves_failure_and_rejects_inherited_remote(self):
        stack = self.stack()
        with (
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://production/postgres"}, clear=True
            ),
            patch.object(stack.subprocess, "run") as run,
        ):
            with self.assertRaises(stack.UnsafeDatabaseTarget):
                stack.run_tests([sys.executable, "-m", "pytest"])
            run.assert_not_called()
        with (
            patch.object(stack, "verify_test_target"),
            patch.object(stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)),
        ):
            self.assertEqual(stack.run_tests([sys.executable, "-m", "pytest"]), 7)

    def test_database_fixture_guard_uses_same_boundary(self):
        stack = self.stack()
        path = ROOT / "server/tests/support/database_guard.py"
        self.assertTrue(path.is_file(), "Database fixture guard is absent")
        guard = importlib.import_module("server.tests.support.database_guard")
        with patch.object(stack, "verify_test_target") as verify:
            with patch.dict("os.environ", {"APP_ENV": "test"}, clear=True):
                guard.require_test_database()
            self.assertEqual(verify.call_args.kwargs["app_env"], "test")
            self.assertEqual(verify.call_args.kwargs["database_url"], "")

    def test_direct_fixture_guard_rejects_libpq_overrides(self):
        stack = self.stack()
        guard = importlib.import_module("server.tests.support.database_guard")
        for override in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"):
            environment = {
                "APP_ENV": "test",
                "DATABASE_URL": "postgresql://studio_local_test:fixture@127.0.0.1:55322/postgres",
                "SUPABASE_URL": "http://127.0.0.1:55321",
                "SUPABASE_PROJECT_ID": "handbalancer-studio-test",
                override: "198.51.100.1",
            }
            with (
                patch.dict("os.environ", environment, clear=True),
                patch.object(stack, "inspect_database", return_value=self.container()) as inspect,
            ):
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    guard.require_test_database()
                inspect.assert_not_called()

    def test_explicit_start_is_scoped_and_does_not_reset(self):
        stack = self.stack()
        self.assertTrue(hasattr(stack, "start"), "Explicit profile start is absent")
        key = {"kty": "EC", "alg": "ES256", "kid": "fixture", "d": "private-fixture"}
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                "os.environ",
                {"SUPABASE_DB_PORT": "5432", "SUPABASE_ACCESS_TOKEN": "remote-token"},
                clear=True,
            ),
        ):
            root = Path(directory)
            results = [
                subprocess.CompletedProcess([], 0, "2.120.0\n"),
                subprocess.CompletedProcess([], 0, json.dumps(key)),
                subprocess.CompletedProcess([], 0, "do-not-print-credentials"),
            ]
            with (
                patch.object(stack.subprocess, "run", side_effect=results) as run,
                patch.object(stack, "provision_local_login", create=True) as provision,
            ):
                stack.start("test", root=root)
            provision.assert_called_once_with("test", root=root)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0], ["supabase", "--version"])
            self.assertIn("signing-key", commands[1])
            self.assertEqual(
                commands[2],
                ["supabase", "start", "--workdir", str(root / ".local-tools/supabase/test")],
            )
            environment = run.call_args.kwargs["env"]
            self.assertNotIn("SUPABASE_ACCESS_TOKEN", environment)
            self.assertNotIn("SUPABASE_DB_PORT", environment)
            self.assertEqual(environment["SUPABASE_EXPERIMENTAL_STACK"], "0")
            credentials = json.loads(
                (root / ".local-tools/supabase/test/credentials.json").read_text()
            )
            self.assertNotIn("SUPABASE_DB_PASSWORD", environment)
            self.assertEqual(environment["SUPABASE_AUTH_JWT_SECRET"], credentials["jwt_secret"])
            key_path = root / ".local-tools/supabase/test/supabase/signing_keys.json"
            self.assertEqual(json.loads(key_path.read_text()), [key])
            self.assertEqual(key_path.stat().st_mode & 0o777, 0o600)
            with (
                patch.object(stack.subprocess, "run", side_effect=[results[0], results[2]]) as run,
                patch.object(stack, "provision_local_login", create=True),
            ):
                stack.start("test", root=root)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(json.loads(key_path.read_text()), [key])

    def test_cli_failure_and_wrong_version_do_not_start_stack(self):
        stack = self.stack()
        self.assertTrue(hasattr(stack, "start"), "Explicit profile start is absent")
        for result in (
            subprocess.CompletedProcess([], 0, "9.0.0"),
            subprocess.CompletedProcess([], 1, "secret"),
        ):
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(stack.subprocess, "run", return_value=result) as run,
            ):
                with self.assertRaises(stack.UnsafeDatabaseTarget) as error:
                    stack.start("test", root=Path(directory))
                self.assertEqual(run.call_count, 1)
                self.assertNotIn("secret", str(error.exception))

    def test_prepared_runner_uses_own_password_and_drops_libpq_overrides(self):
        stack = self.stack()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workdir = stack.prepare("test", root=root)
            credentials = json.loads((workdir / "credentials.json").read_text())
            with (
                patch.dict(
                    "os.environ",
                    {
                        "PGHOSTADDR": "198.51.100.1",
                        "PGSERVICE": "production",
                        "SUPABASE_SERVICE_ROLE_KEY": "production-secret",
                    },
                    clear=True,
                ),
                patch.object(stack, "verify_test_target"),
                patch.object(
                    stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
                ) as run,
            ):
                stack.run_tests([sys.executable, "-m", "pytest"], root=root)
            environment = run.call_args.kwargs["env"]
            self.assertIn(credentials["db_password"], environment["DATABASE_URL"])
            self.assertTrue(
                environment["DATABASE_URL"].startswith("postgresql://studio_local_test:")
            )
            self.assertNotIn("PGHOSTADDR", environment)
            self.assertNotIn("PGSERVICE", environment)
            self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", environment)

    def test_local_login_provisioning_is_guarded_and_keeps_password_off_argv(self):
        stack = self.stack()
        self.assertTrue(
            hasattr(stack, "provision_local_login"), "Local login provisioning is absent"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workdir = stack.prepare("test", root=root)
            password = stack.read_credentials(workdir)["db_password"]
            with (
                patch.object(stack, "inspect_database", return_value=self.container()),
                patch.object(
                    stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
                ) as run,
            ):
                stack.provision_local_login("test", root=root)
            arguments = run.call_args.args[0]
            self.assertIn("test-container-id", arguments)
            self.assertNotIn(password, " ".join(arguments))
            sql = run.call_args.kwargs["input"]
            self.assertIn("studio_local_test", sql)
            self.assertIn("NOSUPERUSER", sql)
            self.assertIn("NOBYPASSRLS", sql)
            self.assertNotIn("ALTER ROLE postgres", sql)
            self.assertEqual(run.call_args.kwargs["timeout"], 15)
            invalid = self.container()
            invalid["Config"]["Labels"] = {}
            with (
                patch.object(stack, "inspect_database", return_value=invalid),
                patch.object(stack.subprocess, "run") as run,
            ):
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    stack.provision_local_login("test", root=root)
                run.assert_not_called()


    def test_migration_provisioning_has_separate_private_operator_access(self):
        stack = self.stack()
        self.assertTrue(hasattr(stack, "provision_migration_roles"), "Migration provisioning absent")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workdir = stack.prepare("test", root=root)
            with patch.object(stack, "verify_container", return_value=self.container()), patch.object(stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
                stack.provision_migration_roles("test", root=root)
                password = stack.read_migration_password(workdir)
                stack.provision_migration_roles("test", root=root)
            self.assertEqual(stack.read_migration_password(workdir), password)
            self.assertNotEqual(password, stack.read_credentials(workdir)["db_password"])
            self.assertEqual((workdir / "migration_credentials.json").stat().st_mode & 0o777, 0o600)
            self.assertNotIn(password, " ".join(run.call_args.args[0]))
            sql = run.call_args.kwargs["input"]
            self.assertIn("migration_owner LOGIN NOSUPERUSER", sql)
            self.assertTrue("GRANT USAGE ON SCHEMA auth TO migration_owner;" in sql)
            self.assertTrue("GRANT REFERENCES (id) ON auth.users TO migration_owner;" in sql)
            self.assertTrue("GRANT SELECT" not in sql)
            for role in ("studio_web", "studio_auth_runtime", "studio_worker"):
                self.assertIn(f"{role} NOLOGIN NOSUPERUSER", sql)
            self.assertNotIn("studio_local_test", sql)
            with patch.object(stack, "verify_container", side_effect=stack.UnsafeDatabaseTarget), patch.object(stack.subprocess, "run") as run:
                with self.assertRaises(stack.UnsafeDatabaseTarget):
                    stack.provision_migration_roles("test", root=root)
                run.assert_not_called()

    def test_migration_runner_is_local_and_drops_external_overrides(self):
        stack = self.stack()
        self.assertTrue(hasattr(stack, "run_migrations"), "Migration runner absent")
        with patch.dict(os.environ, {"PGHOSTADDR": "remote", "STUDIO_MIGRATION_DATABASE_URL": "postgresql://remote"}, clear=True), patch.object(stack, "verify_container") as verify, patch.object(stack, "read_migration_password", return_value="a" * 64), patch.object(stack.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            stack.run_migrations("test")
        verify.assert_called_once_with("test")
        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["STUDIO_MIGRATION_DATABASE_URL"], "postgresql+psycopg://migration_owner:" + "a" * 64 + "@127.0.0.1:55322/postgres")
        self.assertNotIn("PGHOSTADDR", environment)
        self.assertNotIn("a" * 64, " ".join(run.call_args.args[0]))
        self.assertEqual(run.call_args.args[0][-2:], ["upgrade", "head"])


def live_isolation():
    import psycopg

    from tools import local_stack as stack

    checks = unittest.TestCase()
    credentials = {
        profile: stack.read_credentials(ROOT / ".local-tools/supabase" / profile)
        for profile in ("dev", "test")
    }
    target = {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql://studio_local_test:"
        + credentials["test"]["db_password"]
        + "@127.0.0.1:55322/postgres",
        "SUPABASE_URL": "http://127.0.0.1:55321",
        "SUPABASE_PROJECT_ID": stack.PROJECTS["test"],
    }
    with patch.dict(os.environ, target):
        from server.tests.support.database_guard import require_test_database

        require_test_database()
        dev_container = stack.inspect_database(stack.PROJECTS["dev"])
        test_container = stack.inspect_database(stack.PROJECTS["test"])
        checks.assertNotEqual(dev_container["Id"], test_container["Id"])
        checks.assertTrue(
            {
                mount.get("Name") for mount in dev_container["Mounts"] if mount["Type"] == "volume"
            }.isdisjoint(
                {
                    mount.get("Name")
                    for mount in test_container["Mounts"]
                    if mount["Type"] == "volume"
                }
            )
        )
        statuses = {}
        for profile in ("dev", "test"):
            workdir = ROOT / ".local-tools/supabase" / profile
            statuses[profile] = json.loads(
                stack.cli_output(
                    ["status", "--workdir", str(workdir), "--output", "json"],
                    workdir,
                    stack.docker_environment(),
                )
            )
        checks.assertTrue(statuses["dev"]["ANON_KEY"] != statuses["test"]["ANON_KEY"])
        for profile, port in (("dev", 54321), ("test", 55321)):
            endpoint = f"http://127.0.0.1:{port}/rest/v1/"
            with urlopen(
                Request(
                    endpoint,
                    headers={
                        "apikey": statuses[profile]["ANON_KEY"],
                        "Authorization": "Bearer " + statuses[profile]["ANON_KEY"],
                    },
                ),
                timeout=5,
            ) as response:
                checks.assertEqual(response.status, 200)
            other = "test" if profile == "dev" else "dev"
            with checks.assertRaises(HTTPError) as rejected:
                urlopen(
                    Request(
                        endpoint,
                        headers={
                            "apikey": statuses[other]["ANON_KEY"],
                            "Authorization": "Bearer " + statuses[other]["ANON_KEY"],
                        },
                    ),
                    timeout=5,
                )
            checks.assertEqual(rejected.exception.code, 401)
            rejected.exception.close()
        connections = {}
        try:
            for profile, port in (("dev", 54322), ("test", 55322)):
                connections[profile] = psycopg.connect(
                    host="127.0.0.1",
                    port=port,
                    dbname="postgres",
                    user=f"studio_local_{profile}",
                    password=credentials[profile]["db_password"],
                    connect_timeout=5,
                )
                other = "test" if profile == "dev" else "dev"
                with (
                    checks.assertRaises(psycopg.OperationalError),
                    psycopg.connect(
                        host="127.0.0.1",
                        port=port,
                        dbname="postgres",
                        user=f"studio_local_{profile}",
                        password=credentials[other]["db_password"],
                        connect_timeout=5,
                    ),
                ):
                    pass
                connection = connections[profile]
                checks.assertEqual(
                    connection.execute(
                        "SELECT rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                    ).fetchone(),
                    (False, False, False, False, False, False),
                )
                with checks.assertRaises(psycopg.errors.InsufficientPrivilege):
                    connection.execute("SELECT * FROM auth.users LIMIT 0")
                connection.rollback()
                connection.execute("CREATE TEMP TABLE s01_isolation_probe (value text)")
                connection.execute("INSERT INTO s01_isolation_probe VALUES (%s)", (profile,))
                connection.commit()
                checks.assertIsNotNone(
                    connection.execute(
                        "SELECT oid FROM pg_class WHERE relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth') AND relname = 'users'"
                    ).fetchone()
                )
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(stack.provision_local_login, ("test", "test")))
            for _ in range(2):
                checks.assertEqual(
                    stack.run_tests(
                        [
                            sys.executable,
                            "-c",
                            "from server.tests.support.database_guard import require_test_database; require_test_database()",
                        ]
                    ),
                    0,
                )
                for profile, connection in connections.items():
                    checks.assertEqual(
                        connection.execute("SELECT value FROM s01_isolation_probe").fetchall(),
                        [(profile,)],
                    )
            checks.assertEqual(
                stack.inspect_database(stack.PROJECTS["dev"])["Id"], dev_container["Id"]
            )
        finally:
            for connection in connections.values():
                connection.close()


if __name__ == "__main__":
    if sys.argv[1:] == ["--live"]:
        outcome = unittest.TextTestRunner(verbosity=2).run(
            unittest.FunctionTestCase(live_isolation)
        )
        raise SystemExit(not outcome.wasSuccessful())
    unittest.main()
