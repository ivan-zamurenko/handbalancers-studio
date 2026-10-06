"""Real installs in disposable environments verify the project's toolchain contract."""

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ToolchainTests(unittest.TestCase):
    def require_files(self):
        for name in (
            "pyproject.toml",
            "uv.lock",
            "package.json",
            "package-lock.json",
            ".python-version",
            ".node-version",
            ".npmrc",
        ):
            self.assertTrue((ROOT / name).is_file(), f"Missing toolchain artifact: {name}")

    def run_command(self, args, cwd, env=None):
        result = subprocess.run(
            args, cwd=cwd, env=env, capture_output=True, text=True, timeout=180, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_python_package_path(self):
        self.require_files()
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(Path(tmp) / "venv"))
            self.run_command(["uv", "sync", "--locked"], ROOT, env)
            python = (
                Path(tmp) / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            )
            source = self.run_command(
                [str(python), "-I", "-c", "import studio; print(studio.__file__)"], tmp
            )
            self.assertEqual(Path(source).resolve(), ROOT / "server/studio/__init__.py")
            info = self.run_command(
                [
                    str(python),
                    "-I",
                    "-c",
                    'import importlib.metadata as m; print(m.distribution("handbalancers-studio").read_text("direct_url.json"))',
                ],
                tmp,
            )
            self.assertTrue(json.loads(info)["dir_info"]["editable"])

    def test_lock_is_reproducible(self):
        self.require_files()
        names = ("uv.lock", "package-lock.json")
        before = {name: (ROOT / name).read_bytes() for name in names}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in (
                "pyproject.toml",
                "uv.lock",
                "package.json",
                "package-lock.json",
                ".python-version",
                ".node-version",
                ".npmrc",
            ):
                shutil.copyfile(ROOT / name, target / name)
            shutil.copytree(ROOT / "server/studio", target / "server/studio")
            env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(target / ".venv"))
            for _ in range(2):
                self.run_command(["uv", "sync", "--locked"], target, env)
                self.run_command(
                    ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], target
                )
                for name in names:
                    self.assertEqual((target / name).read_bytes(), before[name], name)

    def test_no_frontend_rewrite(self):
        self.require_files()
        package = json.loads((ROOT / "package.json").read_text())
        self.assertTrue(package["private"])
        self.assertFalse(package.get("dependencies", {}), "npm is tooling only")
        all_names = set(package.get("devDependencies", {})) | set(package.get("dependencies", {}))
        self.assertFalse({"react", "react-dom", "vite"} & all_names)
        self.assertEqual((ROOT / ".node-version").read_text().strip().split(".")[0], "24")
        self.assertEqual((ROOT / ".python-version").read_text().strip().split(".")[:2], ["3", "13"])
        self.assertEqual(
            self.run_command(["node", "--version"], ROOT).removeprefix("v"),
            (ROOT / ".node-version").read_text().strip(),
        )
        config = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertIn("build-system", config, "Project must be installable")


if __name__ == "__main__":
    unittest.main()
