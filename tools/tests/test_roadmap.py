"""Acceptance tests for the execution-kit utility, not the application."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'roadmap.py'


def load_module():
    if not MODULE_PATH.exists():
        raise AssertionError('The required roadmap utility has not been implemented yet')
    spec = importlib.util.spec_from_file_location('studio_roadmap', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_task(ident, order, deps=(), gates=()):
    return {'id': ident, 'order': order, 'stage': '00', 'slug': ident.lower(),
            'depends_on': list(deps), 'gates': list(gates),
            'card': 'roadmap/tasks/' + ident + '.md', 'read': ['docs/contracts.md'],
            'title': ident, 'test_cases': [{'name': 'a', 'expected': 'real behavior'}],
            'test_file': 'server/tests/test_' + ident + '.py', 'files': ['server/studio/a.py'],
            'command': 'pytest', 'commit': 'feat: ' + ident, 'kind': 'unit'}


def state_for(tasks):
    return {'tasks': {t['id']: {'status': 'todo', 'evidence': None} for t in tasks},
            'gates': {'G_EXT': {'status': 'pending', 'evidence': None}}, 'active_task': None}


class RoadmapAcceptance(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tasks = [make_task('S00-01', 1), make_task('S00-02', 2, ['S00-01']),
                      make_task('S00-03', 3, ['S00-02'], ['G_EXT']),
                      make_task('S00-04', 4, ['S00-02'])]
        self.state = state_for(self.tasks)

    def test_initial_next_is_first(self):
        self.assertEqual(self.mod.select_next(self.tasks, self.state)['task']['id'], 'S00-01')

    def test_done_unblocks_dependency(self):
        self.state['tasks']['S00-01'] = {'status': 'done', 'evidence': 'e.json'}
        self.assertEqual(self.mod.select_next(self.tasks, self.state)['task']['id'], 'S00-02')

    def test_pending_external_gate_does_not_block_independent_work(self):
        for ident in ['S00-01', 'S00-02']:
            self.state['tasks'][ident] = {'status': 'done', 'evidence': 'e.json'}
        self.assertEqual(self.mod.select_next(self.tasks, self.state)['task']['id'], 'S00-04')

    def test_approved_gate_unblocks_but_does_not_complete_task(self):
        for ident in ['S00-01', 'S00-02']:
            self.state['tasks'][ident] = {'status': 'done', 'evidence': 'e.json'}
        self.state['gates']['G_EXT'] = {'status': 'approved', 'evidence': 'approval.md'}
        result = self.mod.select_next(self.tasks, self.state)
        self.assertEqual(result['task']['id'], 'S00-03')
        self.assertEqual(self.state['tasks']['S00-03']['status'], 'todo')

    def test_in_progress_is_resumed(self):
        self.state['tasks']['S00-01']['status'] = 'in_progress'
        self.assertEqual(self.mod.select_next(self.tasks, self.state)['action'], 'resume')

    def test_multiple_in_progress_is_error(self):
        self.state['tasks']['S00-01']['status'] = 'in_progress'
        self.state['tasks']['S00-02']['status'] = 'in_progress'
        self.assertIn('multiple_in_progress', self.mod.validate_graph(self.tasks, self.state))

    def test_missing_dependency_is_rejected(self):
        self.tasks[1]['depends_on'] = ['S99-99']
        self.assertTrue(any('unknown_dependency' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_cycle_is_rejected(self):
        self.tasks[0]['depends_on'] = ['S00-02']
        self.assertTrue(any('cycle' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_duplicate_id_is_rejected(self):
        self.tasks.append(copy.deepcopy(self.tasks[0]))
        self.assertTrue(any('duplicate_task_id' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_done_requires_evidence(self):
        self.state['tasks']['S00-01']['status'] = 'done'
        self.assertTrue(any('done_without_evidence' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_done_requires_done_dependencies(self):
        self.state['tasks']['S00-02'] = {'status': 'done', 'evidence': 'e.json'}
        self.assertTrue(any('done_before_dependency' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_gate_approval_requires_evidence(self):
        self.state['gates']['G_EXT']['status'] = 'approved'
        self.assertTrue(any('gate_without_evidence' in x for x in self.mod.validate_graph(self.tasks, self.state)))

    def test_safe_path_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self.mod.safe_path(Path(temp), '../private.env')

    def test_context_contains_only_relevant_documents(self):
        result = self.mod.context_paths(self.tasks[0])
        self.assertIn('AGENTS.md', result)
        self.assertIn(self.tasks[0]['card'], result)
        self.assertNotIn('references/v3/START_HERE.html', result)

    def test_selector_is_read_only(self):
        before = copy.deepcopy(self.state)
        self.mod.select_next(self.tasks, self.state)
        self.assertEqual(before, self.state)

    def test_all_done_returns_complete(self):
        for ident in self.state['tasks']:
            self.state['tasks'][ident] = {'status': 'done', 'evidence': 'e.json'}
        self.state['gates']['G_EXT'] = {'status': 'approved', 'evidence': 'ok.md'}
        self.assertEqual(self.mod.select_next(self.tasks, self.state)['action'], 'complete')


if __name__ == '__main__':
    unittest.main()
