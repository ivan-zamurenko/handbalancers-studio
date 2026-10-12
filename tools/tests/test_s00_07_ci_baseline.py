"""CI must fail closed and install only the reviewed dependency locks."""

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class CIBaselineTests(unittest.TestCase):
    def workflow(self):
        path = ROOT / ".github/workflows/ci.yml"
        self.assertTrue(path.is_file(), "CI workflow is absent")
        import yaml

        return yaml.safe_load(path.read_text()), path.read_text()

    def test_missing_tests_fail(self):
        script = ROOT / "tools/checks.py"
        self.assertTrue(script.is_file(), "Fail-closed check runner is absent")
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(script), "--root", tmp],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing required tests", result.stderr)

    def test_each_required_suite_is_mandatory(self):
        script = ROOT / "tools/checks.py"
        self.assertTrue(script.is_file(), "Fail-closed check runner is absent")
        suites = [
            "tools/tests/test_one.py",
            "server/tests/unit/test_one.py",
            "server/tests/contracts/test_one.py",
            "server/tests/security/auth/test_one.py",
            "tests/js/one.test.js",
            "tests/e2e/one.spec.js",
        ]
        for missing in suites:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                for name in suites:
                    if name != missing:
                        path = Path(tmp) / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("# presence fixture; must not execute")
                result = subprocess.run(
                    [sys.executable, str(script), "--root", tmp],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(Path(missing).parent), result.stderr)
                self.assertNotIn("Running:", result.stdout)

    def test_ci_read_only_permissions(self):
        workflow, source = self.workflow()
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["on"]), {"push", "pull_request"})
        self.assertNotIn("secrets.", source)
        self.assertNotIn("pull_request_target", source)
        for job in workflow["jobs"].values():
            self.assertNotIn("environment", job)
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                self.assertNotIn("continue-on-error", step)
                if "uses" in step:
                    self.assertRegex(step["uses"], r"^[\w/-]+@[0-9a-f]{40}$")
                    if step["uses"].startswith("actions/checkout@"):
                        self.assertFalse(step["with"]["persist-credentials"])

    def test_frozen_dependencies(self):
        workflow, _ = self.workflow()
        commands = "\n".join(
            step.get("run", "") for job in workflow["jobs"].values() for step in job["steps"]
        )
        self.assertIn("uv sync --locked", commands)
        self.assertIn("npm ci", commands)
        self.assertIn("python tools/checks.py", commands)
        self.assertIsNone(re.search(r"\b(pip install|uv add|npm install|uv lock)\b", commands))

    def test_check_failure_stops_pipeline(self):
        script = ROOT / "tools/checks.py"
        self.assertTrue(script.is_file(), "Fail-closed check runner is absent")
        spec = importlib.util.spec_from_file_location("studio_checks", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(
            module.subprocess, "run", return_value=subprocess.CompletedProcess([], 5)
        ) as run:
            self.assertEqual(module.run_checks(ROOT), 5)
            self.assertEqual(run.call_count, 1)


def test_auth_security_runs_in_ci():
    from tools.checks import COMMANDS, REQUIRED_SUITES

    assert "server/tests/security/auth" in REQUIRED_SUITES
    assert any(
        "pytest" in command and "server/tests/security/auth" in command for command in COMMANDS
    )
