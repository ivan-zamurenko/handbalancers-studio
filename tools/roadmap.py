#!/usr/bin/env python3
"""Read-only task selector for Studio. Never executes task commands or mutates Git/DB."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

STATUSES = {'todo', 'in_progress', 'in_review', 'done', 'blocked', 'skipped'}
GATE_STATUSES = {'pending', 'approved', 'rejected'}


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('invalid_relative_path')
    raw = Path(relative)
    if raw.is_absolute():
        raise ValueError('absolute_path_forbidden')
    result = (root.resolve() / raw).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('path_outside_workspace')
    return result


def validate_graph(tasks: list[dict[str, Any]], state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids = [t.get('id') for t in tasks]
    if len(ids) != len(set(ids)):
        errors.append('duplicate_task_id')
    by_id = {t.get('id'): t for t in tasks}
    task_states = state.get('tasks', {})
    gates = state.get('gates', {})
    orders = [t.get('order') for t in tasks]
    if len(orders) != len(set(orders)):
        errors.append('duplicate_task_order')
    for t in tasks:
        ident = t.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'S\d{2}-\d{2}(?:[a-z])?', ident):
            errors.append(f'invalid_task_id:{ident}')
        if ident not in task_states:
            errors.append(f'missing_task_state:{ident}')
        if not t.get('test_cases'):
            errors.append(f'no_acceptance_cases:{ident}')
        for dependency in t.get('depends_on', []):
            if dependency not in by_id:
                errors.append(f'unknown_dependency:{ident}:{dependency}')
        for gate in t.get('gates', []):
            if gate not in gates:
                errors.append(f'unknown_gate:{ident}:{gate}')
        status = task_states.get(ident, {}).get('status')
        if status not in STATUSES:
            errors.append(f'invalid_task_status:{ident}:{status}')
        if status == 'done':
            if not task_states[ident].get('evidence'):
                errors.append(f'done_without_evidence:{ident}')
            for dep in t.get('depends_on', []):
                if task_states.get(dep, {}).get('status') != 'done':
                    errors.append(f'done_before_dependency:{ident}:{dep}')
            for gate in t.get('gates', []):
                if gates.get(gate, {}).get('status') != 'approved':
                    errors.append(f'done_before_gate:{ident}:{gate}')
    for extra in set(task_states) - set(ids):
        errors.append(f'unknown_state_task:{extra}')
    for gate, info in gates.items():
        if info.get('status') not in GATE_STATUSES:
            errors.append(f'invalid_gate_status:{gate}')
        if info.get('status') == 'approved' and not info.get('evidence'):
            errors.append(f'gate_without_evidence:{gate}')
    busy = [ident for ident, item in task_states.items() if item.get('status') in {'in_progress', 'in_review'}]
    if len(busy) > 1:
        errors.append('multiple_in_progress')
    active = state.get('active_task')
    if active and active not in by_id:
        errors.append(f'unknown_active_task:{active}')
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(ident: str) -> None:
        if ident in visiting:
            errors.append(f'cycle:{ident}')
            return
        if ident in visited or ident not in by_id:
            return
        visiting.add(ident)
        for dependency in by_id[ident].get('depends_on', []):
            visit(dependency)
        visiting.remove(ident)
        visited.add(ident)

    for ident in by_id:
        visit(ident)
    return sorted(set(errors))


def select_next(tasks: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    errors = validate_graph(tasks, state)
    if errors:
        return {'action': 'repair_state', 'errors': errors, 'task': None}
    task_states, gates = state['tasks'], state['gates']
    ordered = sorted(tasks, key=lambda t: t['order'])
    for t in ordered:
        status = task_states[t['id']]['status']
        if status in {'in_progress', 'in_review'}:
            return {'action': 'resume' if status == 'in_progress' else 'review', 'task': t}
    blocked: list[dict[str, Any]] = []
    for t in ordered:
        status = task_states[t['id']]['status']
        if status in {'done', 'skipped'}:
            continue
        missing_deps = [d for d in t.get('depends_on', []) if task_states[d]['status'] != 'done']
        missing_gates = [g for g in t.get('gates', []) if gates[g]['status'] != 'approved']
        if not missing_deps and not missing_gates and status == 'todo':
            return {'action': 'start', 'task': t, 'skipped_blockers': blocked}
        blocked.append({'id': t['id'], 'dependencies': missing_deps, 'gates': missing_gates,
                        'manually_blocked': status == 'blocked'})
    if blocked:
        return {'action': 'blocked', 'task': None, 'blockers': blocked}
    return {'action': 'complete', 'task': None,
            'note': 'All tasks are done/skipped. This is not an automatic release authorization.'}


def context_paths(task: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys(['AGENTS.md', '.workflow/CURRENT.md', task['card'], *task.get('read', [])]))


def read_inputs(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    document = json.loads(safe_path(root, 'roadmap/tasks.json').read_text(encoding='utf-8'))
    state = json.loads(safe_path(root, '.workflow/state.json').read_text(encoding='utf-8'))
    if not isinstance(document, dict) or not isinstance(document.get('tasks'), list) or not isinstance(state, dict):
        raise ValueError('invalid_document_shape')
    return document['tasks'], state


def validate_files(root: Path, tasks: list[dict[str, Any]], state: dict[str, Any]) -> list[str]:
    errors = validate_graph(tasks, state)
    for task in tasks:
        for path in context_paths(task):
            try:
                if not safe_path(root, path).is_file():
                    errors.append(f'missing_document:{task["id"]}:{path}')
            except ValueError:
                errors.append(f'unsafe_document:{task["id"]}:{path}')
    for ident, item in [*state.get('tasks', {}).items(), *state.get('gates', {}).items()]:
        evidence = item.get('evidence')
        if evidence:
            try:
                if not safe_path(root, evidence).is_file():
                    errors.append(f'missing_evidence:{ident}')
            except ValueError:
                errors.append(f'unsafe_evidence:{ident}')
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('action', choices=['validate', 'next', 'show', 'context', 'status'])
    parser.add_argument('task_id', nargs='?')
    args = parser.parse_args(argv)
    try:
        tasks, state = read_inputs(args.root)
        if args.action == 'validate':
            errors = validate_files(args.root, tasks, state)
            print(json.dumps({'valid': not errors, 'tasks': len(tasks), 'errors': errors}, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        if args.action == 'next':
            result = select_next(tasks, state)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if result['action'] == 'repair_state' else 0
        if args.action == 'status':
            counts = {status: sum(x['status'] == status for x in state['tasks'].values()) for status in sorted(STATUSES)}
            print(json.dumps({'counts': counts, 'gates': state['gates']}, ensure_ascii=False, indent=2))
            return 0
        if not args.task_id:
            parser.error('show/context require task_id')
        task = next((t for t in tasks if t['id'] == args.task_id), None)
        if task is None:
            raise ValueError(f'unknown_task:{args.task_id}')
        if args.action == 'context':
            print('\n'.join(context_paths(task)))
        else:
            print(safe_path(args.root, task['card']).read_text(encoding='utf-8'))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'roadmap error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
