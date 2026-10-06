"""Exercise workspace creation and Git's actual staging rules in disposable folders."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class WorkspaceTests(unittest.TestCase):
    def initializer(self):
        path = ROOT / 'tools/workspace.py'
        self.assertTrue(path.is_file(), 'Safe workspace initializer is not implemented')
        spec = importlib.util.spec_from_file_location('workspace', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.initialize

    def test_refuse_nonempty_target(self):
        initialize = self.initializer()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'foreign'
            target.mkdir()
            marker = target / 'owner.txt'
            marker.write_text('keep me')
            with self.assertRaises(FileExistsError):
                initialize(target)
            self.assertEqual(marker.read_text(), 'keep me')
            self.assertEqual(list(target.iterdir()), [marker])

    def test_refuse_symlink_target(self):
        initialize = self.initializer()
        with tempfile.TemporaryDirectory() as tmp:
            owner = Path(tmp) / 'owner'
            owner.mkdir()
            target = Path(tmp) / 'alias'
            target.symlink_to(owner, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                initialize(target)
            self.assertTrue(target.is_symlink())
            self.assertEqual(list(owner.iterdir()), [])

    def test_concurrent_creation_has_one_winner(self):
        initialize = self.initializer()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'new'
            def attempt(_):
                try:
                    initialize(target)
                    return 'created'
                except FileExistsError:
                    return 'refused'
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertCountEqual(list(pool.map(attempt, range(2))),
                                      ['created', 'refused'])
            self.assertEqual(git(target, 'remote'), '')
            self.assertTrue((target / '.workflow/origin.json').is_file())

    def test_record_origin_status(self):
        initialize = self.initializer()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'new'
            initialize(target)
            self.assertEqual(git(target, 'rev-parse', '--show-toplevel'), str(target.resolve()))
            self.assertEqual(git(target, 'symbolic-ref', '--short', 'HEAD'), 'main')
            self.assertEqual(git(target, 'remote'), '')
            self.assertEqual(json.loads((target / '.workflow/origin.json').read_text()),
                             {'origin_present': False, 'push_status': 'pending'})
            with self.assertRaises(FileExistsError):
                initialize(target)
            self.assertEqual(git(target, 'remote'), '')

    def test_no_sensitive_inputs(self):
        sensitive = ['.env', '.env.local', 'server/.env.production', 'token.json',
                     'tokens.json', 'secrets.json', 'cookies.txt', 'cookies.json',
                     'backup.sql', 'database.dump', 'backup.sql.gz',
                     'private/client.mp4', 'client.MOV', 'client.webm',
                     'client.m4v', 'credentials.json', 'private.key', 'capture.har']
        public = ['.env.example', 'server/alembic/versions/0001.py',
                  'docs/contracts.md', 'references/design/preview/example.png']
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, 'init', '-b', 'main')
            shutil.copyfile(ROOT / '.gitignore', root / '.gitignore')
            for name in sensitive + public:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic fixture')
            git(root, 'add', '--all')
            staged = set(git(root, 'ls-files').splitlines())
            self.assertFalse(staged.intersection(sensitive),
                             f'Sensitive files entered index: {staged.intersection(sensitive)}')
            self.assertTrue(set(public).issubset(staged))


if __name__ == '__main__':
    unittest.main()
