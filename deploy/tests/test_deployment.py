"""Check deployment boundaries without contacting a database or external provider."""

import argparse
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


environment = load_module("studio_deploy_environment", ROOT / "deploy/create_env.py")
healthcheck = load_module("studio_deploy_health", ROOT / "deploy/healthcheck.py")


class EnvironmentTests(unittest.TestCase):
    def test_new_file_is_private_and_has_distinct_url_safe_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.test"
            environment.create_file(path, "studio.example.com")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            values = dict(line.split("=", 1) for line in path.read_text().splitlines()
                          if line and not line.startswith("#"))
            secret_names = ("SESSION_SECRET", "POSTGRES_PASSWORD", "APP_DATABASE_PASSWORD")
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", values[name])
                                for name in secret_names))
            self.assertEqual(len({values[name] for name in secret_names}), 3)
            self.assertEqual(values["APP_ENV"], "production")
            self.assertEqual(values["LOCAL_PREVIEW"], "false")
            self.assertEqual(values["BASE_URL"], "https://studio.example.com")

    def test_existing_file_and_symlink_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".env.test"
            target.write_text("existing data")
            link = Path(directory) / "link"
            link.symlink_to(target)
            for path in (target, link):
                with self.assertRaises(FileExistsError):
                    environment.create_file(path, None)
            self.assertEqual(target.read_text(), "existing data")

    def test_cli_does_not_print_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "deploy/create_env.py"),
                 "--output", str(Path(directory) / ".env.test")],
                capture_output=True, text=True, check=True,
            )
            self.assertNotRegex(result.stdout + result.stderr, r"[0-9a-f]{64}")

    def test_invalid_hosts_fail_before_creating_file(self):
        invalid = ["localhost", "127.0.0.1", "[::1]", "https://studio.example.com",
                   "example.com:443", "a.example.com/path", "foo.localhost",
                   "a.example.com;include bad;", "a..example.com", "a\n.example.com"]
        for host in invalid:
            with self.subTest(host=host), self.assertRaises(argparse.ArgumentTypeError):
                environment.validate_host(host)


class DeploymentBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = yaml.safe_load((ROOT / "compose.yaml").read_text())
        cls.production = yaml.safe_load((ROOT / "compose.production.yaml").read_text())

    def test_only_nginx_publishes_production_ports(self):
        services = self.production["services"]
        for name, service in services.items():
            if name != "nginx":
                self.assertNotIn("ports", service, name)
        self.assertEqual(services["nginx"]["ports"], ["80:80", "443:443"])
        self.assertEqual(self.local["services"]["api"]["ports"], ["127.0.0.1:8000:8000"])

    def test_production_settings_and_proxy_trust_are_explicit(self):
        services = self.production["services"]
        settings = services["api"]["environment"]
        self.assertEqual(settings["APP_ENV"], "production")
        self.assertEqual(settings["LOCAL_PREVIEW"], "false")
        self.assertTrue(settings["BASE_URL"].startswith("https://${STUDIO_HOST:?"))
        self.assertIn("${SESSION_SECRET:?", settings["SESSION_SECRET"])
        command = services["api"]["command"]
        proxy_ip = command[command.index("--forwarded-allow-ips") + 1]
        self.assertEqual(proxy_ip, services["nginx"]["networks"]["edge"]["ipv4_address"])
        self.assertNotEqual(proxy_ip, "*")
        self.assertIn("--no-access-log", command)

    def test_migrations_must_finish_before_api(self):
        for config in (self.local, self.production):
            services = config["services"]
            self.assertEqual(services["api"]["depends_on"]["migrate"]["condition"],
                             "service_completed_successfully")
            self.assertEqual(services["migrate"]["depends_on"]["db"]["condition"],
                             "service_healthy")
            self.assertEqual(services["migrate"]["command"], ["alembic", "upgrade", "head"])
            self.assertTrue(config["networks"]["data"]["internal"])
            self.assertNotIn("ports", services["db"])
            self.assertNotIn("POSTGRES_PASSWORD", services["api"]["environment"])

    def test_bootstrap_has_no_application_proxy(self):
        bootstrap = (ROOT / "deploy/nginx/bootstrap.conf.template").read_text()
        self.assertNotIn("proxy_pass", bootstrap)
        self.assertNotIn("proxy.inc", bootstrap)
        self.assertIn("return 503", bootstrap)
        self.assertIn("/.well-known/acme-challenge/", bootstrap)

    def test_request_logging_and_abuse_controls(self):
        config = (ROOT / "deploy/nginx/nginx.conf").read_text()
        tls = (ROOT / "deploy/nginx/tls.conf.template").read_text()
        proxy = (ROOT / "deploy/nginx/proxy.inc").read_text()
        log = config.split("log_format minimal", 1)[1].split(";", 1)[0]
        for sensitive in ("$request_uri", "$args", "$http_cookie", "$http_referer", "$request_body"):
            self.assertNotIn(sensitive, log)
        self.assertIn("location = /api/session", tls)
        self.assertIn("limit_req zone=studio_session", tls)
        self.assertIn("limit_req zone=studio_auth", tls)
        self.assertIn("location = /api/webhooks/stripe", tls)
        self.assertIn("client_max_body_size 1m;", tls)
        self.assertIn("proxy_set_header X-Forwarded-For $remote_addr;", proxy)
        self.assertNotIn("$proxy_add_x_forwarded_for", proxy)

    def test_shell_scripts_parse(self):
        for path in (ROOT / "deploy").rglob("*.sh"):
            result = subprocess.run(["sh", "-n", str(path)], capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, path.name)

    @unittest.skipUnless(shutil.which("docker"), "Docker CLI unavailable; Compose runtime unverified")
    def test_compose_cli_accepts_configs_without_printing_env(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.test"
            environment.create_file(path, "studio.example.com")
            for filename in ("compose.yaml", "compose.production.yaml"):
                result = subprocess.run(
                    ["docker", "compose", "--env-file", str(path), "-f", str(ROOT / filename),
                     "config", "--quiet"], capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 0, filename)


class HealthcheckTests(unittest.TestCase):
    def test_production_host_used_without_exposing_credentials(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.dict(os.environ, {"BASE_URL": "https://studio.example.com"}), \
                patch.object(healthcheck, "urlopen", return_value=Response()) as call:
            self.assertEqual(healthcheck.main(), 0)
            request = call.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:8000/health/ready")
            self.assertEqual(request.get_header("Host"), "studio.example.com")
            self.assertEqual(call.call_args.kwargs["timeout"], 3)

    def test_unavailable_api_fails_healthcheck(self):
        with patch.dict(os.environ, {"BASE_URL": "https://studio.example.com"}), \
                patch.object(healthcheck, "urlopen", side_effect=OSError):
            self.assertEqual(healthcheck.main(), 1)


class BackupTests(unittest.TestCase):
    def run_backup(self, directory, exit_code):
        base = Path(directory)
        binary = base / "bin"
        binary.mkdir()
        docker = binary / "docker"
        docker.write_text(f"#!/bin/sh\nprintf 'test archive'\nexit {exit_code}\n")
        docker.chmod(0o700)
        destination = base / "backups"
        result = subprocess.run(
            ["sh", str(ROOT / "deploy/backup-database.sh"),
             str(base / ".env.test"), str(destination), "studio"],
            env={**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"},
            capture_output=True, check=False,
        )
        return result, destination

    def test_failed_dump_leaves_no_misleading_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            result, destination = self.run_backup(directory, 1)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(destination.iterdir()), [])

    def test_successful_dump_has_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            result, destination = self.run_backup(directory, 0)
            self.assertEqual(result.returncode, 0)
            archives = list(destination.glob("*.dump"))
            self.assertEqual(len(archives), 1)
            self.assertEqual(stat.S_IMODE(archives[0].stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()
