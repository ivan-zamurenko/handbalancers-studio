#!/usr/bin/env python3
"""Initialize a NEW empty repository; never reuse or overwrite an existing target."""
import argparse
import json
from pathlib import Path
import subprocess


def initialize(target: Path) -> None:
    target = Path(target).absolute()
    # Exclusive creation also refuses symlinks and concurrent/repeated callers.
    target.mkdir(parents=False, exist_ok=False)
    subprocess.run(['git', '-C', str(target), 'init', '-b', 'main'], check=True,
                   capture_output=True, text=True)
    remotes = subprocess.run(['git', '-C', str(target), 'remote'], check=True,
                             capture_output=True, text=True).stdout.splitlines()
    workflow = target / '.workflow'
    workflow.mkdir()
    (workflow / 'origin.json').write_text(json.dumps({
        'origin_present': 'origin' in remotes, 'push_status': 'pending'
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    try:
        initialize(args.target)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Workspace initialization refused or failed: {error}\n')
