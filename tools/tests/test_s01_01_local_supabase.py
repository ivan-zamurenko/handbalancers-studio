"""Local database access must fail closed before any test command runs."""

import importlib
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class LocalSupabaseTests(unittest.TestCase):
    def stack(self):
        self.assertTrue((ROOT / "tools/local_stack.py").is_file(), "Local stack guard is absent")
        return importlib.import_module("tools.local_stack")

    def container(self):
        return {
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
            "database_url": "postgresql://postgres:secret@127.0.0.1:55322/postgres",
            "supabase_url": "http://127.0.0.1:55321",
            "project_id": "handbalancer-studio-test",
        }
        arguments.update(overrides)
        return stack.verify_test_target(**arguments)

    def test_reject_remote_host(self):
        stack = self.stack()
        urls = {
            "database_url": [
                "postgresql://postgres:secret@db.example.com:55322/postgres",
                "postgresql://postgres:secret@127.0.0.1:54322/postgres",
                "postgresql://postgres:secret@127.0.0.1:55322/postgres?host=db.example.com",
                "postgresql://postgres:secret@127.0.0.1:55322/production",
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
                "DATABASE_URL": "postgresql://postgres:fixture@127.0.0.1:55322/postgres",
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
            with patch.object(stack.subprocess, "run", side_effect=results) as run:
                stack.start("test", root=root)
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
            self.assertEqual(environment["SUPABASE_DB_PASSWORD"], credentials["db_password"])
            self.assertEqual(environment["SUPABASE_AUTH_JWT_SECRET"], credentials["jwt_secret"])
            key_path = root / ".local-tools/supabase/test/supabase/signing_keys.json"
            self.assertEqual(json.loads(key_path.read_text()), [key])
            self.assertEqual(key_path.stat().st_mode & 0o777, 0o600)
            with patch.object(stack.subprocess, "run", side_effect=[results[0], results[2]]) as run:
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
            self.assertNotIn("PGHOSTADDR", environment)
            self.assertNotIn("PGSERVICE", environment)
            self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", environment)


if __name__ == "__main__":
    unittest.main()
