"""Regression tests for isolated offline checks (no ROS or network required)."""

import importlib.util
import io
from contextlib import redirect_stdout
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parents[1] / 'check_offline.py'
_SPEC = importlib.util.spec_from_file_location('arachne_check_offline', _SCRIPT)
check_offline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_offline)


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), *args], stderr=subprocess.STDOUT,
    )


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='arachne-runner-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source with spaces'
        self.source.mkdir()
        git(self.source, 'init', '--quiet')
        git(self.source, 'config', 'user.name', 'Runner test')
        git(self.source, 'config', 'user.email', 'test@localhost')
        git(self.source, 'config', 'commit.gpgSign', 'false')
        git(self.source, 'config', 'core.hooksPath', str(self.source / 'no-hooks'))
        (self.source / '.gitignore').write_text('ignored/\n')
        for name in ('staged.txt', 'unstaged.txt', 'deleted.txt', 'renamed.txt'):
            (self.source / name).write_text('baseline\n')
        (self.source / 'binary.dat').write_bytes(b'\x00\x01\x02')
        git(self.source, 'add', '--all')
        git(self.source, 'commit', '--quiet', '-m', 'baseline')
        self.revision = git(self.source, 'rev-parse', 'HEAD').strip()
        self.destination = self.base / 'snapshot'

    def test_snapshot_keeps_history_and_all_worktree_changes(self):
        (self.source / 'staged.txt').write_text('staged\n')
        git(self.source, 'add', '--', 'staged.txt')
        (self.source / 'staged.txt').write_text('staged and then edited\n')
        (self.source / 'unstaged.txt').write_text('unstaged\n')
        (self.source / 'deleted.txt').unlink()
        git(self.source, 'mv', 'renamed.txt', 'renamed with spaces.txt')
        (self.source / 'binary.dat').write_bytes(b'\x00\xff\x03')
        (self.source / 'new file.txt').write_text('new\n')
        (self.source / 'ignored').mkdir()
        (self.source / 'ignored' / 'cache').write_text('do not copy\n')
        status_before = git(self.source, 'status', '--porcelain')
        index_before = (self.source / '.git' / 'index').read_bytes()
        staged_before = git(self.source, 'diff', '--cached', '--binary')

        revision = check_offline.create_snapshot(self.source, self.destination)

        self.assertEqual(revision.encode(), self.revision)
        for name, content in {
            'staged.txt': 'staged and then edited\n',
            'unstaged.txt': 'unstaged\n',
            'renamed with spaces.txt': 'baseline\n',
            'new file.txt': 'new\n',
        }.items():
            self.assertEqual((self.destination / name).read_text(), content)
        self.assertFalse((self.destination / 'deleted.txt').exists())
        self.assertFalse((self.destination / 'renamed.txt').exists())
        self.assertFalse((self.destination / 'ignored').exists())
        self.assertEqual((self.destination / 'binary.dat').read_bytes(), b'\x00\xff\x03')
        self.assertEqual(git(self.destination, 'status', '--porcelain'), b'')
        self.assertEqual(git(self.destination, 'remote'), b'')
        self.assertEqual(
            git(self.destination, 'show', f'{revision}:staged.txt'), b'baseline\n',
        )
        self.assertEqual(git(self.source, 'rev-parse', 'HEAD').strip(), self.revision)
        self.assertEqual(git(self.source, 'diff', '--cached', '--binary'), staged_before)
        self.assertEqual((self.source / '.git' / 'index').read_bytes(), index_before)
        self.assertEqual(git(self.source, 'status', '--porcelain'), status_before)

    def test_clean_snapshot_does_not_add_a_commit(self):
        check_offline.create_snapshot(self.source, self.destination)
        self.assertEqual(
            git(self.destination, 'rev-parse', 'HEAD').strip(), self.revision,
        )

    def test_snapshot_patch_ignores_diff_display_settings(self):
        git(self.source, 'config', 'diff.noprefix', 'true')
        git(self.source, 'config', 'color.ui', 'always')
        (self.source / 'unstaged.txt').write_text('changed\n')
        check_offline.create_snapshot(self.source, self.destination)
        self.assertEqual(
            (self.destination / 'unstaged.txt').read_text(), 'changed\n',
        )

    def test_force_added_ignored_file_is_in_snapshot_commit(self):
        (self.source / 'ignored').mkdir()
        (self.source / 'ignored' / 'required.txt').write_text('required\n')
        git(self.source, 'add', '--force', '--', 'ignored/required.txt')
        index_before = (self.source / '.git' / 'index').read_bytes()
        check_offline.create_snapshot(self.source, self.destination)
        self.assertEqual(
            git(self.destination, 'show', 'HEAD:ignored/required.txt'), b'required\n',
        )
        self.assertEqual((self.source / '.git' / 'index').read_bytes(), index_before)

    def test_untracked_symlink_is_preserved_without_dereferencing(self):
        (self.source / 'pointer').symlink_to('unstaged.txt')
        check_offline.create_snapshot(self.source, self.destination)
        copied = self.destination / 'pointer'
        self.assertTrue(copied.is_symlink())
        self.assertEqual(os.readlink(copied), 'unstaged.txt')

    def test_tracked_executable_bit_change_is_preserved(self):
        path = self.source / 'unstaged.txt'
        path.chmod(0o755)
        check_offline.create_snapshot(self.source, self.destination)
        self.assertTrue((self.destination / 'unstaged.txt').stat().st_mode & 0o111)

    def test_clone_failure_is_actionable(self):
        self.destination.mkdir()
        (self.destination / 'occupied').write_text('preserve\n')
        with self.assertRaises(check_offline.CheckError):
            check_offline.create_snapshot(self.source, self.destination)
        self.assertEqual((self.destination / 'occupied').read_text(), 'preserve\n')

    def test_inherited_git_overrides_cannot_redirect_snapshot_operations(self):
        index_before = (self.source / '.git' / 'index').read_bytes()
        with patch.dict(os.environ, {
            'GIT_DIR': str(self.source / '.git'),
            'GIT_WORK_TREE': str(self.source),
            'GIT_INDEX_FILE': str(self.source / '.git' / 'index'),
            'GIT_CONFIG_COUNT': '1',
            'GIT_CONFIG_KEY_0': 'core.bare',
            'GIT_CONFIG_VALUE_0': 'true',
        }):
            check_offline.create_snapshot(self.source, self.destination)
        self.assertEqual(git(self.destination, 'rev-parse', 'HEAD').strip(), self.revision)
        self.assertEqual(git(self.source, 'rev-parse', 'HEAD').strip(), self.revision)
        self.assertEqual((self.source / '.git' / 'index').read_bytes(), index_before)
        self.assertEqual(git(self.destination, 'remote'), b'')

    def test_repository_without_a_commit_is_rejected(self):
        empty = self.base / 'empty'
        empty.mkdir()
        git(empty, 'init', '--quiet')
        with self.assertRaises(check_offline.CheckError):
            check_offline.create_snapshot(empty, self.destination)


class InvocationTests(unittest.TestCase):
    def test_environment_prefers_snapshot_and_clears_external_pytest_options(self):
        with patch.dict(os.environ, {
            'PYTHONPATH': '/stale/install',
            'PYTEST_ADDOPTS': '-k nonexistent',
            'PYTEST_PLUGINS': 'unrelated_plugin',
        }):
            env = check_offline.test_environment(Path('/snapshot'))
        self.assertEqual(
            env['PYTHONPATH'].split(os.pathsep)[0],
            '/snapshot/src/arachne_hx6_analysis',
        )
        self.assertEqual(env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'], '1')
        self.assertNotIn('PYTEST_ADDOPTS', env)
        self.assertNotIn('PYTEST_PLUGINS', env)

    def test_missing_xacro_reports_prerequisite_before_snapshot(self):
        def which(name):
            return '/usr/bin/git' if name == 'git' else None

        with patch.object(check_offline.shutil, 'which', side_effect=which), \
                patch.object(check_offline, 'create_snapshot') as snapshot:
            self.assertEqual(check_offline.main(['--suite', 'all']), 1)
            snapshot.assert_not_called()

    def test_missing_module_reports_prerequisite_before_snapshot(self):
        with patch.object(check_offline.importlib.util, 'find_spec', return_value=None), \
                patch.object(check_offline, 'create_snapshot') as snapshot:
            self.assertEqual(check_offline.main([]), 1)
            snapshot.assert_not_called()

    def test_main_propagates_pytest_failure_and_cleans_snapshot(self):
        for code, expected in [(0, 0), (1, 1), (2, 2), (5, 5), (-2, 130)]:
            with self.subTest(exit_code=code):
                destinations = []

                def snapshot(_source, destination):
                    destination.mkdir()
                    destinations.append(destination)
                    return 'test-revision'

                with patch.object(check_offline, 'create_snapshot', side_effect=snapshot), \
                        patch.object(check_offline.subprocess, 'run') as run, \
                        redirect_stdout(io.StringIO()):
                    run.return_value.returncode = code
                    self.assertEqual(check_offline.main(['--suite', 'cli']), expected)
                    self.assertEqual(run.call_args.kwargs['cwd'], destinations[0])
                self.assertFalse(destinations[0].exists())

    def test_unknown_suite_is_argument_error(self):
        with self.assertRaises(SystemExit) as raised:
            check_offline.build_parser().parse_args(['--suite', 'hardware'])
        self.assertEqual(raised.exception.code, 2)
