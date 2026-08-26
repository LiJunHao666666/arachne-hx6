"""G4-D1C offline CLI wrapper for configuration-space reports.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1C_OFFLINE_CLI_WRAPPER_ONLY
No D1A evaluator copy. No D1B renderer/rollback copy. No D1D.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import sys

import yaml

from arachne_hx6_analysis.configuration_space_evaluate import (
    evaluate_configuration_space,
    load_configuration_space_config,
)
from arachne_hx6_analysis.configuration_space_report import (
    load_report_authorization,
    write_configuration_space_reports,
)
from arachne_hx6_analysis.inputs import as_bool, as_mapping, as_str, require_key
from arachne_hx6_analysis.model import (
    AnalysisError,
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
)

IMPLEMENTATION_AUTHORIZATION_STATUS = 'GPT_AUTHORIZED'
IMPLEMENTATION_SCOPE = 'G4_D1C_OFFLINE_CLI_WRAPPER_ONLY'
SOURCE_EVALUATOR_SCOPE = 'G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY'
SOURCE_REPORTER_SCOPE = 'G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY'

_TOP_LEVEL_KEYS = (
    'status',
    'implementation_authorization_status',
    'implementation_scope',
    'cli_wrapper_registration_allowed',
    'source_evaluator_scope',
    'source_evaluator_cli_registration_allowed',
    'source_evaluator_report_file_generation_allowed',
    'source_reporter_scope',
    'source_reporter_cli_registration_allowed',
    'source_reporter_report_triplet_generation_allowed',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'gazebo_allowed',
    'px4_allowed',
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


@dataclass(frozen=True)
class CliAuthorization:
    status: str
    implementation_authorization_status: str
    implementation_scope: str
    cli_wrapper_registration_allowed: bool
    source_evaluator_scope: str
    source_evaluator_cli_registration_allowed: bool
    source_evaluator_report_file_generation_allowed: bool
    source_reporter_scope: str
    source_reporter_cli_registration_allowed: bool
    source_reporter_report_triplet_generation_allowed: bool
    procurement_allowed: bool
    hardware_assembly_allowed: bool
    gazebo_allowed: bool
    px4_allowed: bool


def _require_exact_keys(mapping: dict, allowed: tuple[str, ...], path: str) -> None:
    extra = sorted(set(mapping) - set(allowed))
    missing = [key for key in allowed if key not in mapping]
    if extra:
        raise InvalidInputError(f'{path} unknown keys: {extra}')
    if missing:
        raise InvalidInputError(f'{path} missing keys: {missing}')


def _require_equal(actual: object, expected: object, name: str) -> None:
    if actual != expected:
        raise InvalidInputError(
            f'{name} mismatch: cli={expected!r} loaded={actual!r}'
        )


def load_cli_authorization(path: str | Path) -> CliAuthorization:
    config_path = Path(path)
    if not config_path.is_file():
        raise InvalidInputError(f'cli config file not found: {config_path}')
    try:
        raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {config_path}: {exc}') from exc
    root = as_mapping(raw, str(config_path))
    _require_exact_keys(root, _TOP_LEVEL_KEYS, 'cli config')
    status = as_str(require_key(root, 'status', ''), 'status')
    if status != STATUS_ANALYSIS_ONLY:
        raise InvalidInputError('status must be ANALYSIS_ONLY')
    auth_status = as_str(
        require_key(root, 'implementation_authorization_status', ''),
        'implementation_authorization_status',
    )
    if auth_status != IMPLEMENTATION_AUTHORIZATION_STATUS:
        raise InvalidInputError(
            'implementation_authorization_status must be GPT_AUTHORIZED'
        )
    scope = as_str(
        require_key(root, 'implementation_scope', ''), 'implementation_scope'
    )
    if scope != IMPLEMENTATION_SCOPE:
        raise InvalidInputError(
            f'implementation_scope must be {IMPLEMENTATION_SCOPE}'
        )
    evaluator_scope = as_str(
        require_key(root, 'source_evaluator_scope', ''),
        'source_evaluator_scope',
    )
    if evaluator_scope != SOURCE_EVALUATOR_SCOPE:
        raise InvalidInputError(
            f'source_evaluator_scope must be {SOURCE_EVALUATOR_SCOPE}'
        )
    reporter_scope = as_str(
        require_key(root, 'source_reporter_scope', ''),
        'source_reporter_scope',
    )
    if reporter_scope != SOURCE_REPORTER_SCOPE:
        raise InvalidInputError(
            f'source_reporter_scope must be {SOURCE_REPORTER_SCOPE}'
        )
    values: dict[str, bool] = {}
    for field in _TRUE_FIELDS:
        if as_bool(require_key(root, field, ''), field) is not True:
            raise InvalidInputError(f'{field} must be true')
        values[field] = True
    for field in _FALSE_FIELDS:
        if as_bool(require_key(root, field, ''), field) is not False:
            raise InvalidInputError(f'{field} must be false')
        values[field] = False
    return CliAuthorization(
        status=STATUS_ANALYSIS_ONLY,
        implementation_authorization_status=auth_status,
        implementation_scope=scope,
        cli_wrapper_registration_allowed=values['cli_wrapper_registration_allowed'],
        source_evaluator_scope=evaluator_scope,
        source_evaluator_cli_registration_allowed=values[
            'source_evaluator_cli_registration_allowed'
        ],
        source_evaluator_report_file_generation_allowed=values[
            'source_evaluator_report_file_generation_allowed'
        ],
        source_reporter_scope=reporter_scope,
        source_reporter_cli_registration_allowed=values[
            'source_reporter_cli_registration_allowed'
        ],
        source_reporter_report_triplet_generation_allowed=values[
            'source_reporter_report_triplet_generation_allowed'
        ],
        procurement_allowed=values['procurement_allowed'],
        hardware_assembly_allowed=values['hardware_assembly_allowed'],
        gazebo_allowed=values['gazebo_allowed'],
        px4_allowed=values['px4_allowed'],
    )


def _cross_check_loaded_configs(auth: CliAuthorization, d1a: object, d1b: object) -> None:
    _require_equal(
        getattr(d1a, 'implementation_scope'),
        auth.source_evaluator_scope,
        'D1A implementation_scope',
    )
    _require_equal(
        getattr(d1a, 'cli_registration_allowed'),
        auth.source_evaluator_cli_registration_allowed,
        'D1A cli_registration_allowed',
    )
    _require_equal(
        getattr(d1a, 'report_file_generation_allowed'),
        auth.source_evaluator_report_file_generation_allowed,
        'D1A report_file_generation_allowed',
    )
    _require_equal(
        getattr(d1b, 'implementation_scope'),
        auth.source_reporter_scope,
        'D1B implementation_scope',
    )
    _require_equal(
        getattr(d1b, 'cli_registration_allowed'),
        auth.source_reporter_cli_registration_allowed,
        'D1B cli_registration_allowed',
    )
    _require_equal(
        getattr(d1b, 'report_triplet_generation_allowed'),
        auth.source_reporter_report_triplet_generation_allowed,
        'D1B report_triplet_generation_allowed',
    )


def _format_error(exc: BaseException) -> str:
    return ' '.join(str(exc).splitlines())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Arachne-HX6 G4-D1C offline configuration-space CLI wrapper. '
            'ANALYSIS_ONLY. NOT_FOR_PROCUREMENT. Contract-text implementation '
            'scope G4_D1C_OFFLINE_CLI_WRAPPER_ONLY.'
        )
    )
    parser.add_argument(
        '--approved-root',
        required=True,
        help='Approved repository root used by the D1A evaluator.',
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Caller-supplied directory for the D1B report triplet.',
    )
    parser.add_argument(
        '--configuration-space-cli-yaml',
        required=True,
        help='Path to the D1C CLI authorization YAML.',
    )
    parser.add_argument(
        '--configuration-space-yaml',
        required=True,
        help='Path to the D1A configuration-space YAML.',
    )
    parser.add_argument(
        '--configuration-space-report-yaml',
        required=True,
        help='Path to the D1B report-authorization YAML.',
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(None if argv is None else list(argv))
    try:
        auth = load_cli_authorization(args.configuration_space_cli_yaml)
        d1a_config = load_configuration_space_config(args.configuration_space_yaml)
        d1b_auth = load_report_authorization(args.configuration_space_report_yaml)
        _cross_check_loaded_configs(auth, d1a_config, d1b_auth)
        result = evaluate_configuration_space(
            config=d1a_config,
            approved_root=Path(args.approved_root),
        )
        write_configuration_space_reports(
            result,
            args.output_dir,
            report_config_path=args.configuration_space_report_yaml,
        )
    except (AnalysisError, OSError) as exc:
        print(f'ERROR: {_format_error(exc)}', file=sys.stderr)
        return 1
    print('ANALYSIS_ONLY')
    print('NOT_FOR_PROCUREMENT')
    print(f'implementation_scope: {IMPLEMENTATION_SCOPE}')
    print('procurement_allowed: false')
    return 0
