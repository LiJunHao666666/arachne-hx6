#!/usr/bin/env python3
"""Run offline regressions against an isolated snapshot of the working tree.

The temporary repository retains local history and includes staged, unstaged,
and non-ignored untracked files. No build, install, fetch, push, or hardware I/O.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

_ANALYSIS_TESTS = 'src/arachne_hx6_analysis/test'
_CONTROL_TESTS = [
    'src/arachne_hx6_control/test/test_gazebo_flight_scenario.py',
    'src/arachne_hx6_control/test/test_flight_command_guard.py',
    'src/arachne_hx6_control/test/test_gazebo_link_loss_scenario.py',
    'src/arachne_hx6_control/test/test_flight_evidence.py',
]
_SUITES = {
    'cli': [f'{_ANALYSIS_TESTS}/test_configuration_space_cli.py'],
    'analysis': [_ANALYSIS_TESTS],
    'all': [
        _ANALYSIS_TESTS,
        'src/arachne_hx6_description/test',
        *_CONTROL_TESTS,
        'scripts/tests',
    ],
}


class CheckError(RuntimeError):
    """An actionable workspace or prerequisite error."""


def _command_environment() -> dict[str, str]:
    # Git location/config overrides can redirect -C commands to the caller's
    # real repository or index. Never propagate them into snapshot operations.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_OPTIONAL_LOCKS'] = '0'
    return env


def _git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ['git', '-C', str(root), *args],
        input=data, capture_output=True, check=False, env=_command_environment(),
    )
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace').strip()
        raise CheckError(f'git {args[0]} failed: {detail}')
    return result.stdout


def create_snapshot(source: Path, destination: Path) -> str:
    """Copy the current source state; commit only inside the temporary clone."""
    revision = _git(source, 'rev-parse', '--verify', 'HEAD').decode().strip()
    # This is a machine-readable patch, independent of user display settings.
    patch = _git(
        source, 'diff', '--binary', '--no-ext-diff', '--no-textconv',
        '--no-color', '--src-prefix=a/', '--dst-prefix=b/', '--no-relative', 'HEAD',
    )
    untracked = _git(source, 'ls-files', '--others', '--exclude-standard', '-z')
    result = subprocess.run(
        ['git', 'clone', '--quiet', '--no-hardlinks', '--no-checkout',
         '--', str(source), str(destination)],
        capture_output=True, check=False, env=_command_environment(),
    )
    if result.returncode:
        raise CheckError(
            'local snapshot clone failed: '
            + result.stderr.decode('utf-8', errors='replace').strip()
        )
    # A snapshot must not inherit a working remote or execute user hooks.
    _git(destination, 'remote', 'remove', 'origin')
    _git(destination, 'config', 'core.hooksPath', str(destination / '.git' / 'no-hooks'))
    _git(destination, 'checkout', '--quiet', '--detach', revision)
    if patch:
        # Preserve index membership for additions that match ignore rules.
        _git(
            destination, 'apply', '--index', '--binary', '--whitespace=nowarn',
            '-', data=patch,
        )
    for raw_path in untracked.split(b'\0'):
        if not raw_path:
            continue
        relative = Path(os.fsdecode(raw_path))
        original = source / relative
        copied = destination / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        if original.is_symlink():
            copied.symlink_to(os.readlink(original))
        elif original.is_file():
            shutil.copy2(original, copied)
        else:
            raise CheckError(f'untracked file changed during snapshot: {relative}')
    # Stage only the private clone, never the caller's index. Frozen-input
    # hashes and historical scope tests remain active against the new snapshot.
    _git(destination, 'add', '--all')
    if _git(destination, 'diff', '--cached', '--name-only'):
        _git(
            destination, '-c', 'user.name=Offline validation',
            '-c', 'user.email=offline-validation@localhost',
            '-c', 'commit.gpgSign=false', 'commit', '--quiet', '--no-verify',
            '-m', 'Temporary working-tree snapshot for offline validation',
        )
    if _git(destination, 'status', '--porcelain'):
        raise CheckError('snapshot is not clean; refusing an incomplete check')
    return revision


def test_environment(root: Path) -> dict[str, str]:
    """Load this snapshot's Python sources, not an installed stale package."""
    env = _command_environment()
    package_paths = [
        str(root / 'src' / 'arachne_hx6_analysis'),
        str(root / 'src' / 'arachne_hx6_control'),
    ]
    inherited = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = os.pathsep.join(
        filter(None, [*package_paths, inherited]),
    )
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    # External pytest options must not silently deselect tests or add paths.
    env.pop('PYTEST_ADDOPTS', None)
    env.pop('PYTEST_PLUGINS', None)
    return env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Run Arachne-HX6 offline tests in a local temporary Git snapshot. '
            'ANALYSIS_ONLY / NOT_FOR_PROCUREMENT. No network required.'
        ),
    )
    parser.add_argument(
        '--suite', choices=tuple(_SUITES), default='analysis',
        help='cli; analysis (default); all (analysis, URDF, and runner tests)',
    )
    parser.add_argument(
        '--keep-snapshot', action='store_true',
        help='retain the temporary directory for inspecting a failed run',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        if shutil.which('git') is None:
            raise CheckError('git is required')
        missing = [name for name in ('pytest', 'yaml') if importlib.util.find_spec(name) is None]
        if missing:
            raise CheckError('missing Python modules: ' + ', '.join(missing))
        if args.suite == 'all' and shutil.which('xacro') is None:
            raise CheckError(
                'all requires xacro; first run: source /opt/ros/jazzy/setup.bash'
            )
        if not (root / _ANALYSIS_TESTS).is_dir():
            raise CheckError('run the script from an Arachne-HX6 checkout')
        with tempfile.TemporaryDirectory(prefix='arachne-offline-') as temp:
            snapshot = Path(temp) / 'workspace'
            revision = create_snapshot(root, snapshot)
            print(f'Source revision: {revision}', flush=True)
            print(f'Suite: {args.suite}; working-tree changes included', flush=True)
            print(f'Snapshot: {snapshot}', flush=True)
            print('ANALYSIS_ONLY / NOT_FOR_PROCUREMENT', flush=True)
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', '-o', 'addopts=',
                 '-q', '--tb=short', *_SUITES[args.suite]],
                cwd=snapshot, env=test_environment(snapshot), check=False,
            )
            if args.keep_snapshot:
                # Move to a new owned directory before TemporaryDirectory cleanup.
                retained = Path(tempfile.mkdtemp(prefix='arachne-offline-retained-'))
                shutil.move(str(snapshot), str(retained / 'workspace'))
                print(f'Retained snapshot: {retained / "workspace"}', flush=True)
            print(f'Offline test exit code: {result.returncode}', flush=True)
            return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except (CheckError, OSError) as exc:
        print('ERROR: ' + ' '.join(str(exc).splitlines()), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Offline check interrupted.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
