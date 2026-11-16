"""CI orchestration tests; real PostgreSQL gates run through check_migrations."""

import importlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]


class MigrationCITests(unittest.TestCase):
    def checker(self):
        self.assertTrue((ROOT / "tools/check_migrations.py").is_file(), "Migration gate absent")
        return importlib.import_module("tools.check_migrations")

    def test_single_head(self):
        checker = self.checker()
        checker.single_head(ROOT / "server/alembic")
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory)
            (script / "versions").mkdir()
            with self.assertRaises(checker.MigrationCheckError):
                checker.single_head(script)
            for revision in ("left", "right"):
                (script / "versions" / f"{revision}.py").write_text(
                    f"revision = '{revision}'\ndown_revision = None\n"
                )
            with self.assertRaises(checker.MigrationCheckError):
                checker.single_head(script)
            (script / "versions/right.py").write_text(
                "revision = 'right'\ndown_revision = 'left'\n"
            )
            self.assertEqual(checker.single_head(script), "right")

    def workflow_commands(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
        self.assertIn("database", workflow["jobs"], "Real database CI job absent")
        return workflow["jobs"]["database"]

    def test_upgrade_from_blank(self):
        job = self.workflow_commands()
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        self.assertIn("tools/local_stack.py start test", commands)
        self.assertIn("tools/local_stack.py provision-migrations test", commands)
        self.assertIn("python -m tools.check_migrations --fresh", commands)
        self.assertLess(commands.index("start test"), commands.index("provision-migrations test"))
        self.assertLess(commands.index("provision-migrations test"), commands.index("--fresh"))
        actions = [s for s in job["steps"] if s.get("uses", "").startswith("supabase/setup-cli@")]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["with"]["version"], "2.120.0")
        self.assertNotIn("db reset", commands)
        self.assertNotIn("start dev", commands)
        cleanup = [s for s in job["steps"] if "stop" in s.get("run", "")]
        self.assertEqual(len(cleanup), 1)
        self.assertEqual(cleanup[0]["if"], "always()")
        self.assertIn("--no-backup", cleanup[0]["run"])
        self.assertIn(".local-tools/supabase/test", cleanup[0]["run"])

    def test_role_isolation_survives(self):
        checker = self.checker()
        self.assertIn("server/tests/security/database", checker.DB_SUITES)
        self.assertIn("server/tests/integration/database", checker.DB_SUITES)
        with (
            patch.object(checker, "require_test_database") as guard,
            patch.object(checker, "verify_fresh_database") as fresh,
            patch.object(
                checker.subprocess, "run", return_value=SimpleNamespace(returncode=5)
            ) as run,
        ):
            self.assertEqual(checker.run_guarded(fresh=True), 5)
            guard.assert_called_once()
            fresh.assert_called_once()
            self.assertIn("tools.check_migrations", run.call_args.args[0])
            self.assertIn("-p", run.call_args.args[0])

    def test_empty_second_suite_fails(self):
        checker = self.checker()
        with (
            patch.object(checker, "require_test_database"),
            patch.object(
                checker.subprocess,
                "run",
                side_effect=[SimpleNamespace(returncode=0), SimpleNamespace(returncode=5)],
            ) as run,
        ):
            self.assertEqual(checker.run_guarded(), 5)
            self.assertEqual(run.call_count, 2)
            for call, suite in zip(run.call_args_list, checker.DB_SUITES[:2], strict=True):
                self.assertIn(suite, call.args[0])
                self.assertEqual(sum(item in checker.DB_SUITES for item in call.args[0]), 1)

    def test_auth_suite_is_required_and_run(self):
        checker = self.checker()
        self.assertIn("server/tests/integration/auth", checker.DB_SUITES)
        self.assertIn("server/tests/security/accounts", checker.DB_SUITES)
        with (
            patch.object(checker, "require_test_database"),
            patch.object(checker.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run,
        ):
            self.assertEqual(checker.run_guarded(), 0)
            self.assertEqual(run.call_count, len(checker.DB_SUITES))
            self.assertIn("server/tests/integration/auth", run.call_args.args[0])

    def test_guard_failure_precedes_mutation(self):
        checker = self.checker()
        with (
            patch.object(checker, "require_test_database", side_effect=RuntimeError("guard")),
            patch.object(checker, "verify_fresh_database") as fresh,
            patch.object(checker.subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "guard"):
                checker.run_guarded(fresh=True)
            fresh.assert_not_called()
            run.assert_not_called()

    def test_skipped_db_checks_fail(self):
        checker = self.checker()
        for kind in ("skipped", "xfailed", "xpassed"):
            reporter = SimpleNamespace(stats={kind: [object()]})
            session = SimpleNamespace(
                exitstatus=0,
                config=SimpleNamespace(
                    pluginmanager=SimpleNamespace(get_plugin=lambda _, result=reporter: result)
                ),
            )
            checker.pytest_sessionfinish(session, 0)
            self.assertEqual(session.exitstatus, 1)

    def test_missing_suite_fails_before_guard(self):
        checker = self.checker()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(checker, "require_test_database") as guard,
        ):
            with self.assertRaises(checker.MigrationCheckError):
                checker.run_guarded(root=Path(directory))
            guard.assert_not_called()
