"""One local/CI entrypoint; missing suites or any failed command fail the gate."""

import argparse
import subprocess
import sys
from pathlib import Path

REQUIRED_SUITES = {
    "tools/tests": "test_*.py",
    "server/tests/unit": "test_*.py",
    "server/tests/contracts": "test_*.py",
    "tests/js": "*.test.js",
    "tests/e2e": "*.spec.js",
}
COMMANDS = (
    ("uv", "run", "--locked", "ruff", "check", "server/studio", "tools/checks.py"),
    ("uv", "run", "--locked", "ruff", "format", "--check", "server/studio", "tools/checks.py"),
    ("uv", "run", "--locked", "mypy", "server/studio", "tools/checks.py"),
    ("uv", "run", "--locked", "pytest", "server/tests/unit", "-q"),
    ("uv", "run", "--locked", "pytest", "server/tests/contracts", "-q"),
    # Includes real Chromium checks against the owned local test server.
    ("uv", "run", "--locked", "pytest", "tools/tests", "-q"),
    ("npm", "run", "test:js"),
    ("python", "tools/roadmap.py", "validate"),
)


def run_checks(root: Path) -> int:
    for directory, pattern in REQUIRED_SUITES.items():
        if not any((root / directory).rglob(pattern)):
            print(f"Missing required tests: {directory}/{pattern}", file=sys.stderr)
            return 1
    for command in COMMANDS:
        print("Running: " + " ".join(command), flush=True)
        try:
            result = subprocess.run(command, cwd=root, check=False)
        except OSError:
            print(f"Unable to start required check: {command[0]}", file=sys.stderr)
            return 1
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    raise SystemExit(run_checks(parser.parse_args().root))
