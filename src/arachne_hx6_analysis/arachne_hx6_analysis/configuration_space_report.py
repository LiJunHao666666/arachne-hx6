"""Write G4-D1B JSON/CSV/Markdown configuration-space reports.

All three artifacts are serialized in memory, cross-checked by re-parsing
the memory texts, written to a staging directory, then replaced onto the
final names. Process-local controlled exceptions roll back to the previous
complete trio or to zero official files. This is not crash-atomic across
power loss or filesystem failure.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY
No CLI.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Callable

import yaml

from arachne_hx6_analysis.configuration_space_report_csv import (
    parse_configuration_space_csv,
    render_configuration_space_csv,
)
from arachne_hx6_analysis.configuration_space_report_markdown import (
    parse_configuration_space_markdown,
    render_configuration_space_markdown,
)
from arachne_hx6_analysis.configuration_space_report_payload import (
    CSV_NAME,
    FORBIDDEN_REPORT_PHRASES,
    FORBIDDEN_REPORT_STATUS_WORDS,
    IMPLEMENTATION_AUTHORIZATION_STATUS,
    IMPLEMENTATION_SCOPE,
    JSON_NAME,
    MARKDOWN_NAME,
    METADATA_KEYS,
    RECORD_KEYS,
    REPORT_NAMES,
    ReportAuthorization,
    SOURCE_EVALUATOR_SCOPE,
    build_configuration_space_json,
    json_roundtrip,
    official_json_text,
)
from arachne_hx6_analysis.configuration_space_types import (
    CONFIGURATION_SPACE_UNSAMPLED,
    ConfigurationSpaceResult,
)
from arachne_hx6_analysis.inputs import as_bool, as_mapping, as_str, require_key
from arachne_hx6_analysis.model import (
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
)

_TOP_LEVEL_KEYS = (
    'status',
    'implementation_authorization_status',
    'implementation_scope',
    'report_triplet_generation_allowed',
    'cli_registration_allowed',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'gazebo_allowed',
    'px4_allowed',
    'source_evaluator_scope',
    'source_evaluator_report_file_generation_allowed',
    'report_basenames',
)
_BASENAME_KEYS = ('json', 'csv', 'markdown')
_FALSE_FIELDS = (
    'cli_registration_allowed',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'gazebo_allowed',
    'px4_allowed',
    'source_evaluator_report_file_generation_allowed',
)


def default_report_config_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / 'config'
        / 'configuration_space_report.yaml'
    )


def _require_exact_keys(mapping: dict, allowed: tuple[str, ...], path: str) -> None:
    extra = sorted(set(mapping) - set(allowed))
    missing = [key for key in allowed if key not in mapping]
    if extra:
        raise InvalidInputError(f'{path} unknown keys: {extra}')
    if missing:
        raise InvalidInputError(f'{path} missing keys: {missing}')


def load_report_authorization(
    path: str | Path | None = None,
) -> ReportAuthorization:
    config_path = Path(path) if path is not None else default_report_config_path()
    if not config_path.is_file():
        raise InvalidInputError(f'report config file not found: {config_path}')
    try:
        raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {config_path}: {exc}') from exc
    root = as_mapping(raw, str(config_path))
    _require_exact_keys(root, _TOP_LEVEL_KEYS, 'report config')
    if as_str(require_key(root, 'status', ''), 'status') != STATUS_ANALYSIS_ONLY:
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
    if not as_bool(
        require_key(root, 'report_triplet_generation_allowed', ''),
        'report_triplet_generation_allowed',
    ):
        raise InvalidInputError('report_triplet_generation_allowed must be true')
    for field in _FALSE_FIELDS:
        if as_bool(require_key(root, field, ''), field) is not False:
            raise InvalidInputError(f'{field} must be false')
    source_scope = as_str(
        require_key(root, 'source_evaluator_scope', ''),
        'source_evaluator_scope',
    )
    if source_scope != SOURCE_EVALUATOR_SCOPE:
        raise InvalidInputError(
            f'source_evaluator_scope must be {SOURCE_EVALUATOR_SCOPE}'
        )
    basenames = as_mapping(
        require_key(root, 'report_basenames', ''), 'report_basenames'
    )
    _require_exact_keys(basenames, _BASENAME_KEYS, 'report_basenames')
    json_name = as_str(require_key(basenames, 'json', ''), 'report_basenames.json')
    csv_name = as_str(require_key(basenames, 'csv', ''), 'report_basenames.csv')
    md_name = as_str(
        require_key(basenames, 'markdown', ''), 'report_basenames.markdown'
    )
    if (json_name, csv_name, md_name) != (JSON_NAME, CSV_NAME, MARKDOWN_NAME):
        raise InvalidInputError('report basenames must remain the frozen contract')
    return ReportAuthorization(
        status=STATUS_ANALYSIS_ONLY,
        implementation_authorization_status=auth_status,
        implementation_scope=scope,
        report_triplet_generation_allowed=True,
        cli_registration_allowed=False,
        procurement_allowed=False,
        hardware_assembly_allowed=False,
        gazebo_allowed=False,
        px4_allowed=False,
        source_evaluator_scope=source_scope,
        source_evaluator_report_file_generation_allowed=False,
        json_name=json_name,
        csv_name=csv_name,
        markdown_name=md_name,
    )


def format_generated_at_utc(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise InvalidInputError('generated_at must be a datetime')
    if value.tzinfo is None:
        raise InvalidInputError('generated_at must be timezone-aware')
    utc = value.astimezone(timezone.utc)
    return utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def resolve_generated_at_utc(
    generated_at: datetime | None,
    clock: Callable[[], datetime] | None,
) -> str:
    if generated_at is not None and clock is not None:
        raise InvalidInputError('generated_at and clock must not both be provided')
    if generated_at is not None:
        return format_generated_at_utc(generated_at)
    if clock is not None:
        stamped = clock()
        if not isinstance(stamped, datetime):
            raise InvalidInputError('clock() must return a datetime')
        if stamped.tzinfo is None:
            raise InvalidInputError('clock() must return a timezone-aware datetime')
        return format_generated_at_utc(stamped)
    return format_generated_at_utc(datetime.now(timezone.utc))


def _lstat_or_missing(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _cleanup_optional_trees(*paths: Path | None) -> None:
    errors: list[OSError] = []
    for path in paths:
        if path is None:
            continue
        try:
            shutil.rmtree(path)
        except OSError as exc:
            errors.append(exc)
    if not errors:
        return
    detail = '; '.join(f'{type(item).__name__}: {item}' for item in errors)
    raise OSError(f'temporary directory cleanup failed: {detail}') from errors[0]


def _require_directory_lstat(path: Path, label: str) -> os.stat_result:
    info = _lstat_or_missing(path)
    if info is None:
        raise InvalidInputError(f'{label} does not exist')
    if stat.S_ISLNK(info.st_mode):
        raise InvalidInputError(f'{label} must not be a symbolic link')
    if not stat.S_ISDIR(info.st_mode):
        raise InvalidInputError(f'{label} must be a directory')
    return info


def _require_output_dir(output_dir: str | Path) -> Path:
    if not isinstance(output_dir, (str, Path)):
        raise InvalidInputError('output_dir must be a path')
    if not str(output_dir).strip():
        raise InvalidInputError('output_dir must be a non-empty path')
    path = Path(output_dir)
    info = _lstat_or_missing(path)
    if info is None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise InvalidInputError(f'cannot create output_dir: {exc}') from exc
        _require_directory_lstat(path, 'output_dir')
        return path
    if stat.S_ISLNK(info.st_mode):
        raise InvalidInputError('output_dir must not be a symbolic link')
    if not stat.S_ISDIR(info.st_mode):
        raise InvalidInputError('output_dir must be a directory')
    return path


def _require_official_targets(out: Path) -> int:
    existing = 0
    for name in REPORT_NAMES:
        dest = out / name
        info = _lstat_or_missing(dest)
        if info is None:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise InvalidInputError(f'{name} must not be a symbolic link')
        if stat.S_ISDIR(info.st_mode):
            raise InvalidInputError(f'{name} must not be a directory')
        if not stat.S_ISREG(info.st_mode):
            raise InvalidInputError(f'{name} must be a regular file')
        existing += 1
    if existing in (1, 2):
        raise InvalidInputError(
            'incomplete official report trio is present; refusing to overwrite'
        )
    return existing


def _records_equal(left: dict, right: dict) -> None:
    if tuple(left) != RECORD_KEYS or tuple(right) != RECORD_KEYS:
        raise InvalidInputError('record key order mismatch during cross-check')
    for key in RECORD_KEYS:
        if json_roundtrip(left[key]) != json_roundtrip(right[key]):
            raise InvalidInputError(f'record field mismatch: {key}')


def _metadata_equal(left: dict, right: dict) -> None:
    if tuple(left) != METADATA_KEYS or tuple(right) != METADATA_KEYS:
        raise InvalidInputError('metadata key order mismatch during cross-check')
    for key in METADATA_KEYS:
        if json_roundtrip(left[key]) != json_roundtrip(right[key]):
            raise InvalidInputError(f'metadata field mismatch: {key}')


def _scan_forbidden(blob: str) -> None:
    for word in FORBIDDEN_REPORT_STATUS_WORDS:
        if word in blob:
            raise InvalidInputError(f'report contains forbidden status word {word}')
    lowered = blob.lower()
    for phrase in FORBIDDEN_REPORT_PHRASES:
        if phrase in lowered:
            raise InvalidInputError(f'report contains forbidden phrase {phrase}')


def cross_validate_triplet_texts(
    json_text: str,
    csv_text: str,
    md_text: str,
    payload: dict,
) -> None:
    try:
        parsed_json = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise InvalidInputError('JSON text is not parseable') from exc
    if tuple(parsed_json) != ('metadata', 'records'):
        raise InvalidInputError('reparsed JSON top-level keys are not frozen')
    json_meta = parsed_json['metadata']
    json_records = parsed_json['records']
    if tuple(json_meta) != METADATA_KEYS:
        raise InvalidInputError('reparsed JSON metadata keys are not frozen')
    _metadata_equal(json_meta, payload['metadata'])
    if len(json_records) != len(payload['records']):
        raise InvalidInputError('reparsed JSON record count mismatch')
    for index, record in enumerate(json_records):
        if tuple(record) != RECORD_KEYS:
            raise InvalidInputError('reparsed JSON record key order mismatch')
        _records_equal(record, payload['records'][index])
    if json_meta['configuration_space_status'] != CONFIGURATION_SPACE_UNSAMPLED:
        raise InvalidInputError(
            'configuration_space_status must remain '
            f'{CONFIGURATION_SPACE_UNSAMPLED}'
        )
    csv_meta, csv_records = parse_configuration_space_csv(csv_text)
    md_meta, md_records = parse_configuration_space_markdown(md_text)
    _metadata_equal(csv_meta, payload['metadata'])
    _metadata_equal(md_meta, payload['metadata'])
    if len(csv_records) != len(payload['records']) or len(md_records) != len(
        payload['records']
    ):
        raise InvalidInputError('CSV/Markdown record count mismatch')
    for index, expected in enumerate(payload['records']):
        _records_equal(csv_records[index], expected)
        _records_equal(md_records[index], expected)
        if csv_records[index]['sample_id'] != expected['sample_id']:
            raise InvalidInputError('CSV sample_id order mismatch')
        if md_records[index]['sample_id'] != expected['sample_id']:
            raise InvalidInputError('Markdown sample_id order mismatch')
    _scan_forbidden(json_text + csv_text + md_text)


def _restore_report_trio(out: Path, backup: Path) -> None:
    for name in REPORT_NAMES:
        dest = out / name
        previous = backup / name
        if previous.exists():
            shutil.copy2(previous, dest)
        else:
            dest.unlink(missing_ok=True)


def write_configuration_space_reports(
    result: ConfigurationSpaceResult,
    output_dir: str | Path,
    *,
    generated_at: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
    report_config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write JSON, CSV, and Markdown into output_dir as one trio."""
    auth = load_report_authorization(report_config_path)
    stamp = resolve_generated_at_utc(generated_at, clock)
    out = _require_output_dir(output_dir)
    existing = _require_official_targets(out)
    payload = build_configuration_space_json(result, stamp, auth)
    json_text = official_json_text(payload)
    csv_text = render_configuration_space_csv(payload['metadata'], payload['records'])
    md_text = render_configuration_space_markdown(
        payload['metadata'], payload['records']
    )
    cross_validate_triplet_texts(json_text, csv_text, md_text, payload)
    contents = {
        JSON_NAME: json_text,
        CSV_NAME: csv_text,
        MARKDOWN_NAME: md_text,
    }
    staging: Path | None = None
    backup: Path | None = None
    backed_up = False
    keep_backup = False
    try:
        staging = Path(tempfile.mkdtemp(prefix='.arachne_g4_write_', dir=out))
        backup = Path(tempfile.mkdtemp(prefix='.arachne_g4_backup_', dir=out))
        for name, text in contents.items():
            (staging / name).write_text(text, encoding='utf-8')
        if existing == 3:
            for name in REPORT_NAMES:
                current = out / name
                info = _lstat_or_missing(current)
                if (
                    info is None
                    or stat.S_ISLNK(info.st_mode)
                    or not stat.S_ISREG(info.st_mode)
                ):
                    raise InvalidInputError(
                        f'{name} must be a regular file before backup'
                    )
                shutil.copy2(current, backup / name)
            backed_up = True
        for name in REPORT_NAMES:
            dest = out / name
            info = _lstat_or_missing(dest)
            if info is not None and (
                stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)
            ):
                raise InvalidInputError(
                    f'{name} must be a regular file before replace'
                )
            os.replace(staging / name, dest)
    except Exception as primary:
        restore_error: BaseException | None = None
        try:
            if backed_up:
                _restore_report_trio(out, backup)
            elif existing == 0:
                for name in REPORT_NAMES:
                    (out / name).unlink(missing_ok=True)
        except Exception as restore_exc:
            keep_backup = True
            restore_error = restore_exc
        try:
            _cleanup_optional_trees(staging, None if keep_backup else backup)
        except OSError as cleanup_exc:
            primary.add_note(
                f'temporary directory cleanup failed: {cleanup_exc}'
            )
        if restore_error is not None:
            raise primary from restore_error
        raise
    _cleanup_optional_trees(staging, backup)
    return {
        'json': out / JSON_NAME,
        'csv': out / CSV_NAME,
        'markdown': out / MARKDOWN_NAME,
    }
