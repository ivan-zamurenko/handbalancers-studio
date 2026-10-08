"""Exercise the actual JS/Playwright entrypoints, including unsafe-origin refusal."""

import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BrowserHarnessTests(unittest.TestCase):
    def run_harness(self, *args, origin="http://127.0.0.1:8765"):
        self.assertTrue((ROOT / "playwright.config.js").is_file(), "Browser harness is absent")
        return subprocess.run(
            ["npm", "run", "test:e2e", "--", *args],
            cwd=ROOT,
            env=dict(os.environ, TEST_BASE_URL=origin),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def test_reject_nonlocal_test_origin(self):
        for origin in ("https://production.example", "http://127.0.0.1:8000", ""):
            with self.subTest(origin=origin):
                result = self.run_harness("--list", origin=origin)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Unsafe test origin", result.stdout + result.stderr)

    def test_isolated_browser_context(self):
        result = self.run_harness("--grep", "context isolation")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 passed", result.stdout)

    def test_refuse_existing_server(self):
        class ExistingApp(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')

            def log_message(self, *args):
                pass

        with HTTPServer(("127.0.0.1", 8765), ExistingApp) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                result = self.run_harness("--grep", "health smoke")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("already used", result.stdout + result.stderr)
            finally:
                server.shutdown()
                worker.join(timeout=5)

    def test_health_smoke(self):
        result = self.run_harness("--grep", "health smoke")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
