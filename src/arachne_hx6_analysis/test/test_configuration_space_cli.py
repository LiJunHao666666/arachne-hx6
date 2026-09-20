"""G4-D1C offline CLI wrapper tests.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1C_OFFLINE_CLI_WRAPPER_ONLY
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest
import yaml

from arachne_hx6_analysis.configuration_space_cli import (
    IMPLEMENTATION_SCOPE,
    build_parser,
    load_cli_authorization,
    main,
)
from arachne_hx6_analysis.configuration_space_evaluate import default_approved_root
from arachne_hx6_analysis.configuration_space_report_payload import (
    CSV_NAME,
    JSON_NAME,
    MARKDOWN_NAME,
)
from arachne_hx6_analysis.configuration_space_types import (
    CONFIGURATION_SPACE_UNSAMPLED,
    N_RECORDS_EXPECTED_FULL,
)
from arachne_hx6_analysis.model import AnalysisError, InvalidInputError

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = default_approved_root()
_CLI_PY = _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_cli.py'
_CLI_YAML = _PACKAGE_ROOT / 'config' / 'configuration_space_cli.yaml'
_D1A_YAML = _PACKAGE_ROOT / 'config' / 'configuration_space.yaml'
_D1B_YAML = _PACKAGE_ROOT / 'config' / 'configuration_space_report.yaml'
_SETUP_PY = _PACKAGE_ROOT / 'setup.py'
_REQUIRED = (
    '--approved-root',
    '--output-dir',
    '--configuration-space-cli-yaml',
    '--configuration-space-yaml',
    '--configuration-space-report-yaml',
)
_STRING_FIELDS = (
    ('status', 'NOT_ANALYSIS_ONLY'),
    ('implementation_authorization_status', 'NOT_AUTHORIZED'),
    ('implementation_scope', 'WRONG_SCOPE'),
    ('source_evaluator_scope', 'WRONG_D1A_SCOPE'),
    ('source_reporter_scope', 'WRONG_D1B_SCOPE'),
)
_TRUE_FIELDS = (
    'cli_wrapper_registration_allowed',
    'source_reporter_report_triplet_generation_allowed',
)
_FALSE_FIELDS = (
    'source_evaluator_cli_registration_allowed',
    'source_evaluator_report_file_generation_allowed',
    'source_reporter_cli_registration_allowed',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'gazebo_allowed',
    'px4_allowed',
)
_ALLOWED_RELPATHS = {
    'src/arachne_hx6_analysis/config/configuration_space_cli.yaml',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_cli.py',
    'src/arachne_hx6_analysis/test/test_configuration_space_cli.py',
    'src/arachne_hx6_analysis/setup.py',
    'src/arachne_hx6_analysis/test/test_configuration_space_report.py',
}
_CONTRACT_MERGE_BASELINE = '4ff681340c024005a92d6502c8f83e7ae14bad3f'
_CLI_INTRODUCED_RELPATH = (
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_cli.py'
)
_CONSOLE_SCRIPTS_ENTRY = (
    'configuration_space_report = arachne_hx6_analysis.configuration_space_cli:main'
)
_FROZEN_SHA256 = {
    'src/arachne_hx6_analysis/config/configuration_space.yaml': (
        'd4f6066fbbd454203a63ec1c8e6678005410095ef2e48e68a785614b57e9d167'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_types.py': (
        '986782c37852c7f3022458498433aa9a3446e3aa79fdec6d525207eae0027e99'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_registry.py': (
        '9aa98e3a90c0fc43abc8659419f3b0f536e62c47ade793693271ff3b524ca556'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_evaluate.py': (
        'e57db1527fec05239ba6a92ac72d13539f7b7d8bfb59bd565dd5d8d7b91afc44'
    ),
    'src/arachne_hx6_analysis/test/test_configuration_space.py': (
        'e305abc969e7092c3e9ca10ac47de95d78ecb0b78bba28f97313e2bc5de1802e'
    ),
    'src/arachne_hx6_analysis/config/configuration_space_report.yaml': (
        '864314b1f1d9ff4767ec1f963ba9c5f9449ef404a77655d809f245ed5fe1a546'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report.py': (
        '3e682642fae7d53d08d0f4cebf4e6a33cd063338930dfab99a1bfff2c23427c2'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_payload.py': (
        '47f40255034b79ee8112b7011cbc94a00c430ba9c86ca4d04161ceabe762a2cf'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_csv.py': (
        'e4973545de1fd5bfdb1099f8c0cb8bbe0db156bd7615cbcc12a21570e4a4bece'
    ),
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_markdown.py': (
        '811fc5f0e26f34477bcf295eb028214653eb85fcae6d1b254adf0791d044a951'
    ),
    'docs/G4_D1C_OFFLINE_CLI_WRAPPER_CONTRACT.md': (
        '50e2b43461bc7074853db7beae469af70f1154eba72482d0b8e2900c54ecc760'
    ),
}
_HEAD_FROZEN = (
    'src/arachne_hx6_analysis/package.xml',
    'README.md',
    'docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md',
    'docs/G3_REQUIREMENTS_EVIDENCE_GATES.md',
    'src/arachne_hx6_description/urdf/arachne_hx6.urdf.xacro',
    'src/arachne_hx6_description/urdf/materials.xacro',
    'src/arachne_hx6_description/urdf/hexarotor.xacro',
    'src/arachne_hx6_description/urdf/leg.xacro',
)
_FORBIDDEN_CLI_IMPORTS = {
    'arachne_hx6_analysis.configuration_space_registry',
    'arachne_hx6_analysis.configuration_space_report_csv',
    'arachne_hx6_analysis.configuration_space_report_markdown',
    'arachne_hx6_analysis.configuration_space_report_payload',
    'arachne_hx6_analysis.architecture_kinematics',
    'arachne_hx6_analysis.geometry_kinematics',
    'arachne_hx6_analysis.geometry',
}
_FORBIDDEN_CLI_FUNCS = {
    'evaluate_declared_pair_gap',
    'interpolate_joint_path',
    'signed_gap_aabb',
    'cross_validate_triplet_texts',
    '_restore_report_trio',
    'render_configuration_space_csv',
    'render_configuration_space_markdown',
    'build_configuration_space_json',
    'require_evaluable_pairs',
}
_WRITE_ATTRS = {
    'write_text',
    'write_bytes',
    'replace',
    'unlink',
    'mkdir',
    'rmdir',
    'dump',
    'dumps',
}


def _cli_mapping() -> dict:
    raw = yaml.safe_load(_CLI_YAML.read_text(encoding='utf-8'))
    assert isinstance(raw, dict)
    return raw


def _write_cli_yaml(tmp_path: Path, mutate: Callable[[dict], None] | None = None) -> Path:
    payload = _cli_mapping()
    if mutate is not None:
        mutate(payload)
    dest = tmp_path / 'configuration_space_cli.yaml'
    dest.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )
    return dest


def _argv(tmp_path: Path, cli_yaml: Path | None = None) -> list[str]:
    out = tmp_path / 'out'
    out.mkdir(exist_ok=True)
    yaml_path = cli_yaml if cli_yaml is not None else _CLI_YAML
    return [
        '--approved-root',
        str(_REPO_ROOT),
        '--output-dir',
        str(out),
        '--configuration-space-cli-yaml',
        str(yaml_path),
        '--configuration-space-yaml',
        str(_D1A_YAML),
        '--configuration-space-report-yaml',
        str(_D1B_YAML),
    ]


def _patch_success(monkeypatch, d1a=None, d1b=None):
    calls = {'evaluate': [], 'write': []}
    loaded_d1a = d1a if d1a is not None else object()
    loaded_d1b = d1b if d1b is not None else SimpleNamespace(
        implementation_scope='G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY',
        cli_registration_allowed=False,
        report_triplet_generation_allowed=True,
    )
    if d1a is None:
        loaded_d1a = SimpleNamespace(
            implementation_scope='G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY',
            cli_registration_allowed=False,
            report_file_generation_allowed=False,
        )

    def fake_load_d1a(path):
        calls['d1a_path'] = path
        return loaded_d1a

    def fake_load_d1b(path):
        calls['d1b_path'] = path
        return loaded_d1b

    def fake_eval(**kwargs):
        calls['evaluate'].append(kwargs)
        return {'records': ()}

    def fake_write(result, output_dir, **kwargs):
        calls['write'].append((result, output_dir, kwargs))
        return {}

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.load_configuration_space_config',
        fake_load_d1a,
    )
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.load_report_authorization',
        fake_load_d1b,
    )
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.evaluate_configuration_space',
        fake_eval,
    )
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.write_configuration_space_reports',
        fake_write,
    )
    return calls


def _official_names(directory: Path) -> list[Path]:
    return [
        directory / JSON_NAME,
        directory / CSV_NAME,
        directory / MARKDOWN_NAME,
    ]


def _git_head_bytes(relpath: str) -> bytes:
    return subprocess.check_output(
        ['git', 'show', f'HEAD:{relpath}'],
        cwd=_REPO_ROOT,
    )


def _git_lines(*args: str) -> list[str]:
    output = subprocess.check_output(
        ['git', *args],
        cwd=_REPO_ROOT,
        text=True,
    )
    return [line for line in output.splitlines() if line]


def _d1c_introducing_commits() -> list[str]:
    return _git_lines(
        'log',
        '--diff-filter=A',
        '--format=%H',
        '--reverse',
        '--',
        _CLI_INTRODUCED_RELPATH,
    )


def _d1c_changed_from_baseline_to_worktree() -> set[str]:
    changed = set(
        _git_lines(
            'diff',
            '--name-only',
            '--no-renames',
            _CONTRACT_MERGE_BASELINE,
        )
    )
    changed.update(_git_lines('ls-files', '--others', '--exclude-standard'))
    return changed


def _has_dunder_main_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], ast.Eq) or len(test.comparators) != 1:
            continue
        left = test.left
        right = test.comparators[0]
        names = []
        constants = []
        for item in (left, right):
            if isinstance(item, ast.Name):
                names.append(item.id)
            elif isinstance(item, ast.Constant) and isinstance(item.value, str):
                constants.append(item.value)
        if '__name__' in names and '__main__' in constants:
            return True
    return False


def _calls_sys_exit(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'sys':
            for alias in node.names:
                if alias.name == 'exit':
                    return True
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == 'exit':
            return True
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'exit'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'sys'
        ):
            return True
    return False


def _main_function(tree: ast.AST) -> ast.FunctionDef:
    found = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'main'
    ]
    assert len(found) == 1
    return found[0]


def _entry_strings(text: str) -> list[str]:
    start = text.index("'console_scripts': [")
    end = text.index('],', start)
    block = text[start:end]
    entries = []
    for line in block.splitlines():
        stripped = line.strip().rstrip(',')
        if ' = ' in stripped:
            entries.append(stripped.strip("'\""))
    return entries


def test_five_required_parameters_have_no_defaults():
    parser = build_parser()
    by_option = {}
    for action in parser._actions:
        for option in action.option_strings:
            by_option[option] = action
    for flag in _REQUIRED:
        action = by_option[flag]
        assert action.required is True
        assert action.default is None
    dests = {action.dest for action in parser._actions}
    assert 'test' not in dests
    assert 'generated_at' not in dests
    assert 'clock' not in dests
    assert 'poses' not in dests
    assert 'pair_ids' not in dests
    assert '--test' not in by_option
    assert '--generated-at' not in by_option


@pytest.mark.parametrize('missing', _REQUIRED)
def test_missing_required_argument_exits_2(missing, tmp_path):
    argv = _argv(tmp_path)
    drop_at = argv.index(missing)
    argv = argv[:drop_at] + argv[drop_at + 2 :]
    with pytest.raises(SystemExit) as caught:
        main(argv)
    assert caught.value.code == 2


def test_legal_call_returns_0(tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 0
    assert 'Traceback' not in captured.err
    assert len(calls['evaluate']) == 1
    assert len(calls['write']) == 1


def test_analysis_error_returns_1(tmp_path, monkeypatch, capsys):
    _patch_success(monkeypatch)
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.evaluate_configuration_space',
        lambda **_kwargs: (_ for _ in ()).throw(AnalysisError('eval failed')),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert captured.err.count('\n') == 1
    assert 'Traceback' not in captured.err
    assert 'Traceback' not in captured.out


def test_invalid_input_error_returns_1(tmp_path, monkeypatch, capsys):
    _patch_success(monkeypatch)
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.load_cli_authorization',
        lambda _path: (_ for _ in ()).throw(InvalidInputError('bad cli yaml')),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert captured.err.count('\n') == 1
    assert 'Traceback' not in captured.err


def test_oserror_returns_1(tmp_path, monkeypatch, capsys):
    _patch_success(monkeypatch)
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.evaluate_configuration_space',
        lambda **_kwargs: (_ for _ in ()).throw(OSError('disk full\nmore')),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert captured.err.count('\n') == 1
    assert 'disk full more' in captured.err
    assert 'Traceback' not in captured.err


def test_unknown_cli_yaml_key_fails(tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__setitem__('not_allowed', True))
    rc = main(_argv(tmp_path, path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []
    for official in _official_names(tmp_path / 'out'):
        assert not official.exists()


@pytest.mark.parametrize('key', list(_cli_mapping()))
def test_missing_cli_yaml_key_fails(key, tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__delitem__(key))
    rc = main(_argv(tmp_path, path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []


@pytest.mark.parametrize('field,value', _STRING_FIELDS)
def test_wrong_string_field_fails(field, value, tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__setitem__(field, value))
    rc = main(_argv(tmp_path, path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []


@pytest.mark.parametrize('field', _TRUE_FIELDS)
def test_true_field_must_be_true(field, tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__setitem__(field, False))
    rc = main(_argv(tmp_path, path))
    assert rc == 1
    assert capsys.readouterr().err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []


@pytest.mark.parametrize('field', _FALSE_FIELDS)
def test_false_field_must_be_false(field, tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__setitem__(field, True))
    rc = main(_argv(tmp_path, path))
    assert rc == 1
    assert capsys.readouterr().err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []


@pytest.mark.parametrize('field', _TRUE_FIELDS + _FALSE_FIELDS)
@pytest.mark.parametrize('bad', ['true', 'false', 0, 1])
def test_string_and_integer_bools_rejected(field, bad, tmp_path, monkeypatch, capsys):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(tmp_path, lambda raw: raw.__setitem__(field, bad))
    rc = main(_argv(tmp_path, path))
    assert rc == 1
    assert capsys.readouterr().err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []


def test_d1a_source_mismatch_skips_evaluator_and_writer(
    tmp_path, monkeypatch, capsys
):
    calls = _patch_success(
        monkeypatch,
        d1a=SimpleNamespace(
            implementation_scope='WRONG_D1A',
            cli_registration_allowed=False,
            report_file_generation_allowed=False,
        ),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []
    for official in _official_names(tmp_path / 'out'):
        assert not official.exists()


def test_d1b_source_mismatch_skips_evaluator_and_writer(
    tmp_path, monkeypatch, capsys
):
    calls = _patch_success(
        monkeypatch,
        d1b=SimpleNamespace(
            implementation_scope='WRONG_D1B',
            cli_registration_allowed=False,
            report_triplet_generation_allowed=True,
        ),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []
    for official in _official_names(tmp_path / 'out'):
        assert not official.exists()


def test_evaluate_receives_explicit_config_and_approved_root(
    tmp_path, monkeypatch
):
    d1a = SimpleNamespace(
        implementation_scope='G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY',
        cli_registration_allowed=False,
        report_file_generation_allowed=False,
    )
    calls = _patch_success(monkeypatch, d1a=d1a)
    argv = _argv(tmp_path)
    rc = main(argv)
    assert rc == 0
    kwargs = calls['evaluate'][0]
    assert kwargs['config'] is d1a
    assert kwargs['approved_root'] == Path(_REPO_ROOT)
    assert 'poses' not in kwargs
    assert 'pair_ids' not in kwargs
    assert calls['d1a_path'] == str(_D1A_YAML)


def test_reporter_receives_result_output_dir_and_report_yaml(
    tmp_path, monkeypatch
):
    calls = _patch_success(monkeypatch)
    argv = _argv(tmp_path)
    rc = main(argv)
    assert rc == 0
    result, output_dir, kwargs = calls['write'][0]
    assert result == {'records': ()}
    assert Path(output_dir) == tmp_path / 'out'
    assert kwargs == {'report_config_path': str(_D1B_YAML)}
    assert 'generated_at' not in kwargs
    assert 'clock' not in kwargs
    assert calls['d1b_path'] == str(_D1B_YAML)


def test_setup_py_adds_exactly_one_approved_entry():
    workspace = _SETUP_PY.read_text(encoding='utf-8')
    baseline = subprocess.check_output(
        [
            'git',
            'show',
            f'{_CONTRACT_MERGE_BASELINE}:src/arachne_hx6_analysis/setup.py',
        ],
        cwd=_REPO_ROOT,
    ).decode('utf-8')
    workspace_entries = _entry_strings(workspace)
    baseline_entries = _entry_strings(baseline)
    assert baseline_entries == [
        'propulsion_report = arachne_hx6_analysis.cli:main',
        'architecture_report = arachne_hx6_analysis.architecture_cli:main',
        'requirements_report = arachne_hx6_analysis.requirements_cli:main',
    ]
    assert workspace_entries[:3] == baseline_entries
    assert workspace_entries[3] == _CONSOLE_SCRIPTS_ENTRY
    assert len(workspace_entries) == 4
    g4_entries = [
        item for item in workspace_entries if 'configuration_space' in item
    ]
    assert g4_entries == [_CONSOLE_SCRIPTS_ENTRY]
    assert workspace.count(_CONSOLE_SCRIPTS_ENTRY) == 1


def test_cli_ast_does_not_copy_core_logic():
    source = _CLI_PY.read_text(encoding='utf-8')
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported.isdisjoint(_FORBIDDEN_CLI_IMPORTS)
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert defined.isdisjoint(_FORBIDDEN_CLI_FUNCS)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            assert func.id != 'open'
            continue
        if isinstance(func, ast.Attribute):
            assert func.attr not in _WRITE_ATTRS
    for name in (JSON_NAME, CSV_NAME, MARKDOWN_NAME):
        assert name not in source
    assert '--test' not in source
    assert 'sample_count' not in {
        action.dest for action in build_parser()._actions
    }


def test_import_and_parser_do_not_write_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib
    import arachne_hx6_analysis.configuration_space_cli as cli_mod

    importlib.reload(cli_mod)
    cli_mod.build_parser()
    leftover = [path.name for path in tmp_path.iterdir()]
    assert leftover == []
    for official in _official_names(tmp_path):
        assert not official.exists()


def test_authorization_failure_leaves_no_partial_triplet(
    tmp_path, monkeypatch, capsys
):
    calls = _patch_success(monkeypatch)
    path = _write_cli_yaml(
        tmp_path, lambda raw: raw.__setitem__('procurement_allowed', True)
    )
    rc = main(_argv(tmp_path, path))
    assert rc == 1
    assert capsys.readouterr().err.startswith('ERROR:')
    assert calls['evaluate'] == []
    assert calls['write'] == []
    for official in _official_names(tmp_path / 'out'):
        assert not official.exists()


def test_d1a_d1b_yaml_keep_false_fields():
    d1a = yaml.safe_load(_D1A_YAML.read_text(encoding='utf-8'))
    d1b = yaml.safe_load(_D1B_YAML.read_text(encoding='utf-8'))
    assert d1a['cli_registration_allowed'] is False
    assert d1a['report_file_generation_allowed'] is False
    assert d1a['procurement_allowed'] is False
    assert d1b['cli_registration_allowed'] is False
    assert d1b['report_triplet_generation_allowed'] is True
    assert d1b['procurement_allowed'] is False
    auth = load_cli_authorization(_CLI_YAML)
    assert auth.implementation_scope == IMPLEMENTATION_SCOPE
    assert auth.cli_wrapper_registration_allowed is True
    assert auth.procurement_allowed is False


def test_change_scope_is_three_new_and_two_modified():
    introducing = _d1c_introducing_commits()
    if not introducing:
        changed = _d1c_changed_from_baseline_to_worktree()
        assert changed == _ALLOWED_RELPATHS
        return
    first = introducing[0]
    parent = _git_lines('rev-parse', '--verify', f'{first}^')[0]
    changed = set(
        _git_lines('diff', '--name-only', '--no-renames', parent, first)
    )
    assert changed == _ALLOWED_RELPATHS


def test_cli_ast_has_main_int_and_no_sys_exit_guard():
    source = _CLI_PY.read_text(encoding='utf-8')
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert 'sys' in imported
    assert not _calls_sys_exit(tree)
    assert not _has_dunder_main_guard(tree)
    main_fn = _main_function(tree)
    assert [arg.arg for arg in main_fn.args.args] == ['argv']
    assert isinstance(main_fn.returns, ast.Name)
    assert main_fn.returns.id == 'int'
    workspace_entries = _entry_strings(_SETUP_PY.read_text(encoding='utf-8'))
    assert workspace_entries[-1] == _CONSOLE_SCRIPTS_ENTRY
    assert workspace_entries.count(_CONSOLE_SCRIPTS_ENTRY) == 1


def test_frozen_files_keep_baseline_hashes_and_head_bytes():
    import hashlib

    for relpath, expected in _FROZEN_SHA256.items():
        data = (_REPO_ROOT / relpath).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected
        if relpath != 'src/arachne_hx6_analysis/setup.py':
            if relpath in _ALLOWED_RELPATHS:
                continue
            if relpath == 'docs/G4_D1C_OFFLINE_CLI_WRAPPER_CONTRACT.md':
                assert data == _git_head_bytes(relpath)
    for relpath in _HEAD_FROZEN:
        if not (_REPO_ROOT / relpath).exists():
            # Fall back to globbing description xacro if the exact path differs.
            continue
        assert (_REPO_ROOT / relpath).read_bytes() == _git_head_bytes(relpath)


def test_urdf_xacro_and_g1_g3_remain_frozen():
    description = _REPO_ROOT / 'src' / 'arachne_hx6_description'
    xacros = sorted(description.rglob('*.xacro')) if description.exists() else []
    urdfs = sorted(description.rglob('*.urdf')) if description.exists() else []
    assert xacros or urdfs
    for path in xacros + urdfs:
        relpath = path.relative_to(_REPO_ROOT).as_posix()
        assert path.read_bytes() == _git_head_bytes(relpath)


def test_production_sampling_invariants_remain_frozen():
    assert N_RECORDS_EXPECTED_FULL == 16362
    assert CONFIGURATION_SPACE_UNSAMPLED == (
        'UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE'
    )
    source = _CLI_PY.read_text(encoding='utf-8')
    assert '16362' not in source
    assert 'pair_ids' not in {
        action.dest for action in build_parser()._actions
    }
    assert 'poses' not in {action.dest for action in build_parser()._actions}


def test_real_loaders_cross_check_without_evaluate(
    tmp_path, monkeypatch, capsys
):
    calls = {'evaluate': [], 'write': []}
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.evaluate_configuration_space',
        lambda **kwargs: calls['evaluate'].append(kwargs) or {'ok': True},
    )
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_cli.write_configuration_space_reports',
        lambda result, output_dir, **kwargs: calls['write'].append(
            (result, output_dir, kwargs)
        ),
    )
    rc = main(_argv(tmp_path))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ''
    assert len(calls['evaluate']) == 1
    assert calls['evaluate'][0]['approved_root'] == Path(_REPO_ROOT)
    assert 'poses' not in calls['evaluate'][0]
    assert len(calls['write']) == 1
    assert IMPLEMENTATION_SCOPE in captured.out
    assert 'procurement_allowed: false' in captured.out


@pytest.mark.parametrize('flag, source_path', [
    ('--configuration-space-cli-yaml', _CLI_YAML),
    ('--configuration-space-yaml', _D1A_YAML),
    ('--configuration-space-report-yaml', _D1B_YAML),
])
@pytest.mark.parametrize('problem', [
    'encoding', 'mixed_keys', 'boolean_key', 'sequence_key',
    'contradictory_duplicate', 'identical_duplicate', 'merge',
    'syntax', 'unsafe_tag', 'empty', 'sequence_root',
])
def test_malformed_yaml_fails_before_analysis(
    flag, source_path, problem, tmp_path, monkeypatch, capsys,
):
    base = source_path.read_bytes()
    documents = {
        'encoding': base + b'\xff',
        'mixed_keys': base + b'\n1: unexpected\nunknown_key: unexpected\n',
        'boolean_key': base + b'\ntrue: unexpected\n',
        'sequence_key': base + b'\n? [first, second]\n: unexpected\n',
        'contradictory_duplicate': (
            base + b'\nprocurement_allowed: true\nprocurement_allowed: false\n'
        ),
        'identical_duplicate': base + b'\nprocurement_allowed: false\n',
        'merge': base + b'\n<<: {procurement_allowed: true}\n',
        'syntax': b'status: [unterminated',
        'unsafe_tag': b'!!python/object/apply:builtins.str [unexpected]',
        'empty': b'',
        'sequence_root': b'[]',
    }
    broken = tmp_path / 'malformed.yaml'
    broken.write_bytes(documents[problem])
    argv = _argv(tmp_path)
    argv[argv.index(flag) + 1] = str(broken)
    calls = _patch_success(monkeypatch)

    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err.startswith('ERROR:')
    assert len(captured.err.splitlines()) == 1
    assert 'Traceback' not in captured.err
    assert str(broken) in captured.err
    assert calls['evaluate'] == []
    assert calls['write'] == []
    assert not any(path.exists() for path in _official_names(tmp_path / 'out'))


def test_nested_duplicate_in_evaluator_config_is_rejected(
    tmp_path, monkeypatch, capsys,
):
    text = _D1A_YAML.read_text(encoding='utf-8')
    needle = '  tolerance_m: 1.0e-9'
    assert text.count(needle) == 1
    broken = tmp_path / 'nested-duplicate.yaml'
    broken.write_text(
        text.replace(needle, '  tolerance_m: 1.0\n' + needle),
        encoding='utf-8',
    )
    argv = _argv(tmp_path)
    argv[argv.index('--configuration-space-yaml') + 1] = str(broken)
    calls = _patch_success(monkeypatch)

    assert main(argv) == 1
    assert 'duplicate configuration key' in capsys.readouterr().err
    assert calls['evaluate'] == []
    assert calls['write'] == []


def test_unique_keys_with_scalar_aliases_are_supported(tmp_path):
    text = _CLI_YAML.read_text(encoding='utf-8')
    text = text.replace(
        '\nprocurement_allowed: false',
        '\nprocurement_allowed: &disabled false',
    ).replace(
        '\nhardware_assembly_allowed: false',
        '\nhardware_assembly_allowed: *disabled',
    )
    path = tmp_path / 'scalar-alias.yaml'
    path.write_text(text, encoding='utf-8')
    auth = load_cli_authorization(path)
    assert auth.procurement_allowed is False
    assert auth.hardware_assembly_allowed is False


@pytest.mark.parametrize('field', ['evaluator', 'reporter'])
def test_encoding_failure_on_loader_reread_is_reported(
    field, tmp_path, monkeypatch, capsys,
):
    calls = _patch_success(monkeypatch)

    def unreadable(_path):
        raise UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid start byte')

    target = (
        'load_configuration_space_config' if field == 'evaluator'
        else 'load_report_authorization'
    )
    monkeypatch.setattr(
        f'arachne_hx6_analysis.configuration_space_cli.{target}', unreadable,
    )
    assert main(_argv(tmp_path)) == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err.startswith('ERROR:')
    assert len(captured.err.splitlines()) == 1
    assert calls['evaluate'] == []
    assert calls['write'] == []
