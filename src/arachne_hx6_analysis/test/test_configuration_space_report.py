"""G4-D1B offline report-triplet tests.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY
No CLI tests.
"""

from __future__ import annotations

import ast
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess

import pytest
import yaml

from arachne_hx6_analysis.architecture_types import REQUIRED_JOINT_NAMES
from arachne_hx6_analysis.configuration_space_evaluate import (
    default_approved_root,
    evaluate_configuration_space,
)
from arachne_hx6_analysis.configuration_space_registry import (
    EXCLUDED_PAIR_IDS,
    EXCLUSION_REASONS,
    INCLUDED_PAIR_IDS,
    uses_aabb_proxy,
)
from arachne_hx6_analysis.configuration_space_report import (
    default_report_config_path,
    load_report_authorization,
    write_configuration_space_reports,
)
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
    IMPLEMENTATION_SCOPE,
    JSON_NAME,
    MARKDOWN_NAME,
    MD_NULL,
    METADATA_KEYS,
    RECORD_KEYS,
    REPORT_NAMES,
    SOURCE_EVALUATOR_SCOPE,
    build_configuration_space_json,
    compact_json,
    official_json_text,
)
from arachne_hx6_analysis.configuration_space_types import (
    CONFIGURATION_SPACE_UNSAMPLED,
    ConfigurationSpaceResult,
    EVALUATED_SCOPE,
    FROZEN_INPUT_RELPATHS,
    G1_DESCRIPTION_COMMIT_SHA,
    G1_DESCRIPTION_TREE_SHA,
    G4_D0_CONTRACT_SHA256,
    HARDWARE_VALIDATION_NOT_VALIDATED,
    IMPLEMENTATION_SCOPE as D1A_SCOPE,
    LIMITATION_AABB_FALSE_POSITIVE,
    LIMITATION_README_ESTIMATE_ONLY,
    LIMITATION_SAMPLED_TRANSITION_ONLY,
    LIMITATION_TIBIA_FOOT_ENDPOINT,
    N_PAIR_INSTANCES_EXCLUDED,
    N_PAIR_INSTANCES_INCLUDED,
    N_RECORDS_EXPECTED_FULL,
    PROXY_STATUS_ANALYSIS_ONLY,
    RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    SAMPLE_COUNT_REQUIRED,
    SAMPLE_SET_NO_INTERSECTION,
    SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
    SOURCE_STATE_OR_PATH,
    SampleRecord,
    SampleSetSummary,
)
from arachne_hx6_analysis.model import InvalidInputError, STATUS_ANALYSIS_ONLY

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = default_approved_root()
_D1A_FILES = (
    'src/arachne_hx6_analysis/config/configuration_space.yaml',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_types.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_registry.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_evaluate.py',
    'src/arachne_hx6_analysis/test/test_configuration_space.py',
)
_D1B_PY_FILES = (
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_report.py',
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_report_payload.py',
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_report_csv.py',
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_report_markdown.py',
)
_STAMP = datetime(2026, 8, 17, 5, 12, 0, tzinfo=timezone.utc)
_STAMP_TEXT = '2026-08-17T05:12:00.000000Z'


def _joints(value: float = 0.01) -> dict[str, float]:
    return {name: value for name in REQUIRED_JOINT_NAMES}


def _geometry_source_for(pair: str) -> tuple[str, ...]:
    if uses_aabb_proxy(pair):
        return ('aabb_proxy', 'primitive=aabb_proxy', 'aabb_proxy')
    return ('disk_capsule', 'primitive=signed_distance_disk_capsule')


def _limitations_for(pair: str, status: str) -> tuple[str, ...]:
    reasons: list[str] = []
    left, right = pair.split('__')
    if left.endswith('_tibia') or right.endswith('_tibia'):
        reasons.append(LIMITATION_TIBIA_FOOT_ENDPOINT)
    if uses_aabb_proxy(pair) and status == RESULT_SAMPLED_INTERSECTION_DETECTED:
        reasons.append(LIMITATION_AABB_FALSE_POSITIVE)
    return tuple(reasons)


def _record(**overrides) -> SampleRecord:
    payload = {
        'sample_id': 'path:standing_to_analysis_stowed:i=00000:pair=lf_coxa__base_link',
        'source_state_or_path': SOURCE_STATE_OR_PATH,
        'evaluated_pair': 'lf_coxa__base_link',
        'joint_values': _joints(),
        'geometry_source': _geometry_source_for('lf_coxa__base_link'),
        'proxy_status': PROXY_STATUS_ANALYSIS_ONLY,
        'hardware_validation_status': HARDWARE_VALIDATION_NOT_VALIDATED,
        'nominal_separation_or_intersection': 0.05,
        'result_status': RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
        'limitation_reasons': _limitations_for(
            'lf_coxa__base_link', RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
        ),
    }
    payload.update(overrides)
    return SampleRecord(**payload)


def _one_sample_records(status: str, gap: float) -> tuple[SampleRecord, ...]:
    records = []
    for pair in INCLUDED_PAIR_IDS:
        records.append(
            _record(
                sample_id=f'path:{SOURCE_STATE_OR_PATH}:i=00000:pair={pair}',
                evaluated_pair=pair,
                geometry_source=_geometry_source_for(pair),
                nominal_separation_or_intersection=gap,
                result_status=status,
                limitation_reasons=_limitations_for(pair, status),
            )
        )
    return tuple(records)


def _summary(**overrides) -> SampleSetSummary:
    payload = {
        'sample_set_status': SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
        'configuration_space_status': CONFIGURATION_SPACE_UNSAMPLED,
        'included_pair_ids': INCLUDED_PAIR_IDS,
        'excluded_pair_ids': EXCLUDED_PAIR_IDS,
        'exclusion_reasons': dict(EXCLUSION_REASONS),
        'n_pair_instances_included': N_PAIR_INSTANCES_INCLUDED,
        'n_pair_instances_excluded': N_PAIR_INSTANCES_EXCLUDED,
        'evaluated_scope': EVALUATED_SCOPE,
        'n_samples_requested': SAMPLE_COUNT_REQUIRED,
        'n_samples_valid': 0,
        'n_records_expected': N_RECORDS_EXPECTED_FULL,
        'n_records_valid': 0,
        'n_records_undetermined': N_RECORDS_EXPECTED_FULL,
        'limitation_reasons': (
            LIMITATION_SAMPLED_TRANSITION_ONLY,
            LIMITATION_README_ESTIMATE_ONLY,
        ),
        'transition_proof_flag': LIMITATION_SAMPLED_TRANSITION_ONLY,
        'implementation_scope': D1A_SCOPE,
        'status': STATUS_ANALYSIS_ONLY,
        'procurement_allowed': False,
        'hardware_assembly_allowed': False,
        'report_file_generation_allowed': False,
        'cli_registration_allowed': False,
        'gazebo_allowed': False,
        'px4_allowed': False,
        'g1_description_commit_sha': G1_DESCRIPTION_COMMIT_SHA,
        'g1_description_tree_sha': G1_DESCRIPTION_TREE_SHA,
        'g4_d0_contract_sha256': G4_D0_CONTRACT_SHA256,
        'frozen_input_blob_sha1': {path: 'a' * 40 for path in FROZEN_INPUT_RELPATHS},
    }
    payload.update(overrides)
    return SampleSetSummary(**payload)


def _empty_result() -> ConfigurationSpaceResult:
    return ConfigurationSpaceResult(records=(), summary=_summary())


def _clearance_result() -> ConfigurationSpaceResult:
    records = _one_sample_records(RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE, 0.05)
    summary = _summary(
        sample_set_status=SAMPLE_SET_NO_INTERSECTION,
        n_samples_requested=1,
        n_samples_valid=1,
        n_records_expected=N_PAIR_INSTANCES_INCLUDED,
        n_records_valid=N_PAIR_INSTANCES_INCLUDED,
        n_records_undetermined=0,
    )
    return ConfigurationSpaceResult(records=records, summary=summary)


def _result_with_geometry(
    result: ConfigurationSpaceResult,
    pair: str,
    geometry_source: tuple[str, ...],
) -> ConfigurationSpaceResult:
    records = []
    replaced = False
    for record in result.records:
        if record.evaluated_pair == pair:
            records.append(
                _record(
                    sample_id=record.sample_id,
                    evaluated_pair=pair,
                    geometry_source=geometry_source,
                    nominal_separation_or_intersection=(
                        record.nominal_separation_or_intersection
                    ),
                    result_status=record.result_status,
                    limitation_reasons=record.limitation_reasons,
                )
            )
            replaced = True
        else:
            records.append(record)
    if not replaced:
        raise AssertionError(f'pair not found in fixture records: {pair}')
    return ConfigurationSpaceResult(
        records=tuple(records), summary=result.summary
    )


def _mixed_aabb_result() -> ConfigurationSpaceResult:
    records = list(
        _one_sample_records(RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE, 0.05)
    )
    target = 'lf_coxa__base_link'
    for index, record in enumerate(records):
        if record.evaluated_pair == target:
            records[index] = _record(
                sample_id=record.sample_id,
                evaluated_pair=target,
                geometry_source=_geometry_source_for(target),
                nominal_separation_or_intersection=-0.02,
                result_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
                limitation_reasons=_limitations_for(
                    target, RESULT_SAMPLED_INTERSECTION_DETECTED
                ),
            )
            break
    summary = _summary(
        sample_set_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
        n_samples_requested=1,
        n_samples_valid=1,
        n_records_expected=N_PAIR_INSTANCES_INCLUDED,
        n_records_valid=N_PAIR_INSTANCES_INCLUDED,
        n_records_undetermined=0,
    )
    return ConfigurationSpaceResult(records=tuple(records), summary=summary)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_head_bytes(relpath: str) -> bytes:
    return subprocess.check_output(
        ['git', 'show', f'HEAD:{relpath}'],
        cwd=_REPO_ROOT,
    )


def _assert_no_g4_temp_dirs(directory: Path) -> None:
    leftovers = [
        path
        for path in directory.iterdir()
        if path.name.startswith('.arachne_g4_')
    ]
    assert leftovers == []


def _report_bytes(directory: Path) -> dict[str, bytes | None]:
    return {
        name: (directory / name).read_bytes() if (directory / name).exists() else None
        for name in REPORT_NAMES
    }


def _inject_replace_failure(monkeypatch, fail_on: int):
    real_replace = __import__('os').replace
    state = {'n': 0}

    def wrapper(src, dst):
        state['n'] += 1
        if state['n'] == fail_on:
            raise OSError(f'injected os.replace failure on call {fail_on}')
        return real_replace(src, dst)

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_report.os.replace', wrapper
    )
    return state


def _mutated_report_yaml(tmp_path: Path, mutate) -> Path:
    raw = yaml.safe_load(default_report_config_path().read_text(encoding='utf-8'))
    mutate(raw)
    dest = tmp_path / 'configuration_space_report.yaml'
    dest.write_text(yaml.safe_dump(raw, sort_keys=False), encoding='utf-8')
    return dest


@pytest.fixture
def clearance_result():
    return _clearance_result()


@pytest.fixture
def mixed_result():
    return _mixed_aabb_result()


@pytest.fixture(scope='module')
def production_result():
    return evaluate_configuration_space()


def test_authorization_yaml_fields():
    auth = load_report_authorization()
    assert auth.status == STATUS_ANALYSIS_ONLY
    assert auth.implementation_authorization_status == 'GPT_AUTHORIZED'
    assert auth.implementation_scope == IMPLEMENTATION_SCOPE
    assert auth.report_triplet_generation_allowed is True
    assert auth.cli_registration_allowed is False
    assert auth.procurement_allowed is False
    assert auth.hardware_assembly_allowed is False
    assert auth.gazebo_allowed is False
    assert auth.px4_allowed is False
    assert auth.source_evaluator_scope == SOURCE_EVALUATOR_SCOPE
    assert auth.source_evaluator_report_file_generation_allowed is False
    yaml_text = default_report_config_path().read_text(encoding='utf-8')
    assert 'report_triplet_generation_allowed: true' in yaml_text
    assert 'source_evaluator_report_file_generation_allowed: false' in yaml_text
    assert SOURCE_EVALUATOR_SCOPE in yaml_text


@pytest.mark.parametrize(
    'field',
    [
        'cli_registration_allowed',
        'procurement_allowed',
        'hardware_assembly_allowed',
        'gazebo_allowed',
        'px4_allowed',
        'source_evaluator_report_file_generation_allowed',
    ],
)
def test_forbidden_report_field_true_is_invalid(tmp_path, field):
    path = _mutated_report_yaml(tmp_path, lambda raw, name=field: raw.__setitem__(name, True))
    with pytest.raises(InvalidInputError, match=field):
        load_report_authorization(path)


def test_unknown_report_yaml_key_is_invalid(tmp_path):
    path = _mutated_report_yaml(
        tmp_path, lambda raw: raw.__setitem__('not_authorized', True)
    )
    with pytest.raises(InvalidInputError, match='unknown keys'):
        load_report_authorization(path)


def test_d1a_scope_in_d1b_yaml_is_invalid(tmp_path):
    path = _mutated_report_yaml(
        tmp_path,
        lambda raw: raw.__setitem__('implementation_scope', SOURCE_EVALUATOR_SCOPE),
    )
    with pytest.raises(InvalidInputError, match='implementation_scope'):
        load_report_authorization(path)


def test_triplet_full_record_set_and_fields(clearance_result, tmp_path):
    paths = write_configuration_space_reports(
        clearance_result, tmp_path, generated_at=_STAMP
    )
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    assert tuple(payload) == ('metadata', 'records')
    assert tuple(payload['metadata']) == METADATA_KEYS
    assert payload['metadata']['generated_at_utc'] == _STAMP_TEXT
    assert payload['metadata']['source_evaluator_scope'] == SOURCE_EVALUATOR_SCOPE
    assert payload['metadata']['source_evaluator_report_file_generation_allowed'] is False
    assert payload['metadata']['implementation_scope'] == IMPLEMENTATION_SCOPE
    assert payload['metadata']['report_triplet_generation_allowed'] is True
    assert payload['metadata']['configuration_space_status'] == (
        CONFIGURATION_SPACE_UNSAMPLED
    )
    assert payload['metadata']['sample_set_status'] == SAMPLE_SET_NO_INTERSECTION
    assert len(payload['records']) == len(clearance_result.records)
    for index, record in enumerate(payload['records']):
        assert tuple(record) == RECORD_KEYS
        source = clearance_result.records[index]
        assert record['sample_id'] == source.sample_id
        assert record['evaluated_pair'] == source.evaluated_pair
        assert list(record['joint_values']) == list(REQUIRED_JOINT_NAMES)
        assert record['geometry_source'] == list(source.geometry_source)
        assert record['limitation_reasons'] == list(source.limitation_reasons)
    csv_rows = list(csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines()))
    meta_rows = [row for row in csv_rows if row['row_type'] == 'metadata']
    rec_rows = [row for row in csv_rows if row['row_type'] == 'record']
    assert [row['metadata_key'] for row in meta_rows] == list(METADATA_KEYS)
    assert [row['sample_id'] for row in rec_rows] == [
        record.sample_id for record in clearance_result.records
    ]
    md_text = paths['markdown'].read_text(encoding='utf-8')
    assert md_text.count('\n| path:') == len(clearance_result.records)
    _assert_no_g4_temp_dirs(tmp_path)


def test_empty_records_count_is_zero(tmp_path):
    result = _empty_result()
    paths = write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    assert payload['records'] == []
    assert payload['metadata']['n_records'] == 0
    assert payload['metadata']['n_records_valid'] == 0
    assert payload['metadata']['n_aabb_proxy_intersections'] == 0
    csv_rows = list(
        csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines())
    )
    rec_rows = [row for row in csv_rows if row['row_type'] == 'record']
    assert rec_rows == []
    md_text = paths['markdown'].read_text(encoding='utf-8')
    assert md_text.count('\n| path:') == 0
    _assert_no_g4_temp_dirs(tmp_path)


def test_sample_record_affirmative_gap_still_rejects_null():
    with pytest.raises(InvalidInputError, match='not null'):
        _record(nominal_separation_or_intersection=None)


def test_renderer_parser_null_gap_semantics():
    auth = load_report_authorization()
    payload = build_configuration_space_json(
        _clearance_result(), _STAMP_TEXT, auth
    )
    record = dict(payload['records'][0])
    record['nominal_separation_or_intersection'] = None
    records = [record]
    json_text = official_json_text(
        {'metadata': payload['metadata'], 'records': records}
    )
    parsed_json = json.loads(json_text)
    json_gap = parsed_json['records'][0]['nominal_separation_or_intersection']
    assert json_gap is None
    assert json_gap not in (0, 0.0)
    assert '"nominal_separation_or_intersection": null' in json_text

    csv_text = render_configuration_space_csv(payload['metadata'], records)
    csv_rows = list(csv.DictReader(csv_text.splitlines()))
    rec_rows = [row for row in csv_rows if row['row_type'] == 'record']
    assert rec_rows[0]['nominal_separation_or_intersection_m'] == ''
    assert rec_rows[0]['nominal_separation_or_intersection_m'] not in ('0', '0.0')
    _csv_meta, csv_records = parse_configuration_space_csv(csv_text)
    csv_gap = csv_records[0]['nominal_separation_or_intersection']
    assert csv_gap is None
    assert csv_gap not in (0, 0.0)

    md_text = render_configuration_space_markdown(payload['metadata'], records)
    rendered_cells = [
        cell.strip()
        for cell in md_text.split('\n')
        if cell.startswith('| path:')
    ]
    assert rendered_cells
    gap_index = RECORD_KEYS.index('nominal_separation_or_intersection')
    gap_cell = rendered_cells[0].strip('|').split('|')[gap_index].strip()
    assert gap_cell == MD_NULL
    _md_meta, md_records = parse_configuration_space_markdown(md_text)
    md_gap = md_records[0]['nominal_separation_or_intersection']
    assert md_gap is None
    assert md_gap not in (0, 0.0)


def test_non_finite_json_rejected(clearance_result, tmp_path, monkeypatch):
    real = build_configuration_space_json

    def bad(result, generated_at_utc, auth):
        payload = real(result, generated_at_utc, auth)
        payload['metadata']['n_records'] = float('nan')
        return payload

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_report.build_configuration_space_json',
        bad,
    )
    with pytest.raises(InvalidInputError):
        write_configuration_space_reports(
            clearance_result, tmp_path, generated_at=_STAMP
        )
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}


def test_fixed_timestamp_is_byte_identical(clearance_result, tmp_path):
    first = write_configuration_space_reports(
        clearance_result, tmp_path / 'a', generated_at=_STAMP
    )
    second = write_configuration_space_reports(
        clearance_result, tmp_path / 'b', generated_at=_STAMP
    )
    for kind in ('json', 'csv', 'markdown'):
        assert first[kind].read_bytes() == second[kind].read_bytes()
    json_text = first['json'].read_text(encoding='utf-8')
    assert json_text.endswith('\n')
    assert not json_text.endswith('\n\n')


def test_generated_at_and_clock_both_rejected(clearance_result, tmp_path):
    with pytest.raises(InvalidInputError, match='generated_at and clock'):
        write_configuration_space_reports(
            clearance_result,
            tmp_path,
            generated_at=_STAMP,
            clock=lambda: _STAMP,
        )


def test_naive_datetime_rejected(clearance_result, tmp_path):
    naive = datetime(2026, 8, 17, 5, 12, 0)
    with pytest.raises(InvalidInputError, match='timezone-aware'):
        write_configuration_space_reports(
            clearance_result, tmp_path, generated_at=naive
        )
    with pytest.raises(InvalidInputError, match='timezone-aware'):
        write_configuration_space_reports(
            clearance_result, tmp_path, clock=lambda: naive
        )


def test_aabb_limitation_dynamic(mixed_result, tmp_path):
    paths = write_configuration_space_reports(
        mixed_result, tmp_path, generated_at=_STAMP
    )
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    meta = payload['metadata']
    assert meta['n_records'] == len(mixed_result.records)
    assert meta['n_aabb_proxy_intersections'] == 1
    assert meta['n_aabb_false_positive_limitations'] == 1
    assert meta['n_result_sampled_intersection_detected'] == 1
    for record in payload['records']:
        aabb = 'aabb_proxy' in record['geometry_source']
        hit = record['result_status'] == RESULT_SAMPLED_INTERSECTION_DETECTED
        has_fp = LIMITATION_AABB_FALSE_POSITIVE in record['limitation_reasons']
        assert has_fp == (aabb and hit)


def test_no_intersection_keeps_unsampled_status(clearance_result, tmp_path):
    paths = write_configuration_space_reports(
        clearance_result, tmp_path, generated_at=_STAMP
    )
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    assert payload['metadata']['sample_set_status'] == SAMPLE_SET_NO_INTERSECTION
    assert payload['metadata']['configuration_space_status'] == (
        CONFIGURATION_SPACE_UNSAMPLED
    )
    blob = (
        paths['json'].read_text(encoding='utf-8')
        + paths['csv'].read_text(encoding='utf-8')
        + paths['markdown'].read_text(encoding='utf-8')
    )
    assert 'UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE' in blob
    assert 'not a complete configuration-space proof' in blob.lower() or (
        'complete configuration-space proof' in blob
    )


@pytest.mark.parametrize('fail_on', [1, 2, 3])
def test_empty_dir_replace_failure_leaves_zero_files(
    clearance_result, tmp_path, monkeypatch, fail_on
):
    out = tmp_path / f'empty_{fail_on}'
    out.mkdir()
    _inject_replace_failure(monkeypatch, fail_on)
    with pytest.raises(OSError, match=f'call {fail_on}'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )
    assert _report_bytes(out) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(out)


@pytest.mark.parametrize('fail_on', [1, 2, 3])
def test_existing_trio_replace_failure_restores_previous(
    clearance_result, tmp_path, monkeypatch, fail_on
):
    out = tmp_path / f'prev_{fail_on}'
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = datetime(2026, 2, 1, tzinfo=timezone.utc)
    write_configuration_space_reports(clearance_result, out, generated_at=old)
    before = _report_bytes(out)
    assert all(payload is not None for payload in before.values())
    _inject_replace_failure(monkeypatch, fail_on)
    with pytest.raises(OSError, match=f'call {fail_on}'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=new
        )
    assert _report_bytes(out) == before
    _assert_no_g4_temp_dirs(out)


def test_cross_validation_failure_zero_official_update(
    clearance_result, tmp_path, monkeypatch
):
    out = tmp_path / 'cross'
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    write_configuration_space_reports(clearance_result, out, generated_at=old)
    before = _report_bytes(out)

    def boom(*_args, **_kwargs):
        raise InvalidInputError('injected cross-validation failure')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_report.cross_validate_triplet_texts',
        boom,
    )
    with pytest.raises(InvalidInputError, match='injected cross-validation'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )
    assert _report_bytes(out) == before
    _assert_no_g4_temp_dirs(out)


def test_incomplete_existing_trio_is_left_untouched(clearance_result, tmp_path):
    out = tmp_path / 'mixed'
    out.mkdir()
    partial = out / JSON_NAME
    partial.write_text('keep-me\n', encoding='utf-8')
    with pytest.raises(InvalidInputError, match='incomplete official report trio'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )
    assert partial.read_text(encoding='utf-8') == 'keep-me\n'
    assert not (out / CSV_NAME).exists()
    assert not (out / MARKDOWN_NAME).exists()


def test_dangling_symlink_output_dir_rejected(clearance_result, tmp_path):
    missing = tmp_path / 'missing_dir'
    link = tmp_path / 'dangling_out'
    link.symlink_to(missing)
    assert stat.S_ISLNK(link.lstat().st_mode)
    with pytest.raises(InvalidInputError, match='symbolic link'):
        write_configuration_space_reports(
            clearance_result, link, generated_at=_STAMP
        )
    assert stat.S_ISLNK(link.lstat().st_mode)
    assert link.readlink() == missing
    assert not missing.exists()
    _assert_no_g4_temp_dirs(tmp_path)


def test_dangling_symlink_official_basename_rejected(clearance_result, tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    dangling = out / JSON_NAME
    dangling.symlink_to(out / 'missing.json')
    before = dangling.readlink()
    with pytest.raises(InvalidInputError, match='symbolic link'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )
    assert stat.S_ISLNK(dangling.lstat().st_mode)
    assert dangling.readlink() == before
    assert not (out / CSV_NAME).exists()
    assert not (out / MARKDOWN_NAME).exists()
    _assert_no_g4_temp_dirs(out)


def test_second_mkdtemp_failure_cleans_first(
    clearance_result, tmp_path, monkeypatch
):
    out = tmp_path / 'mkdtemp_fail'
    out.mkdir()
    real_mkdtemp = __import__('tempfile').mkdtemp
    state = {'n': 0}

    def wrapper(*args, **kwargs):
        state['n'] += 1
        if state['n'] == 2:
            raise OSError('injected second mkdtemp failure')
        return real_mkdtemp(*args, **kwargs)

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_report.tempfile.mkdtemp',
        wrapper,
    )
    with pytest.raises(OSError, match='injected second mkdtemp failure') as caught:
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )
    assert 'injected second mkdtemp failure' in str(caught.value)
    assert _report_bytes(out) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(out)


def test_unknown_geometry_source_rejected(clearance_result, tmp_path):
    result = _result_with_geometry(
        clearance_result,
        'lf_coxa__base_link',
        ('unknown_geometry_source',),
    )
    with pytest.raises(InvalidInputError, match='geometry family'):
        write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(tmp_path)


def test_geometry_source_both_families_rejected(clearance_result, tmp_path):
    result = _result_with_geometry(
        clearance_result,
        'lf_coxa__base_link',
        (
            'aabb_proxy',
            'primitive=aabb_proxy',
            'disk_capsule',
            'primitive=signed_distance_disk_capsule',
        ),
    )
    with pytest.raises(InvalidInputError, match='both AABB and disk-capsule'):
        write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(tmp_path)


def test_aabb_pair_with_disk_tags_rejected(clearance_result, tmp_path):
    result = _result_with_geometry(
        clearance_result,
        'lf_coxa__base_link',
        _geometry_source_for('lf_coxa__analysis_disk_hex_1'),
    )
    with pytest.raises(InvalidInputError, match='AABB registry pair'):
        write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(tmp_path)


def test_disk_pair_with_aabb_tags_rejected(clearance_result, tmp_path):
    result = _result_with_geometry(
        clearance_result,
        'lf_coxa__analysis_disk_hex_1',
        _geometry_source_for('lf_coxa__base_link'),
    )
    with pytest.raises(InvalidInputError, match='disk-capsule pair'):
        write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}
    _assert_no_g4_temp_dirs(tmp_path)


def test_symlink_output_dir_rejected(clearance_result, tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    assert stat.S_ISLNK(link.lstat().st_mode)
    with pytest.raises(InvalidInputError, match='symbolic link'):
        write_configuration_space_reports(
            clearance_result, link, generated_at=_STAMP
        )
    assert list(real.iterdir()) == []


def test_symlink_official_target_rejected(clearance_result, tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    target = tmp_path / 'elsewhere.json'
    target.write_text('x', encoding='utf-8')
    (out / JSON_NAME).symlink_to(target)
    (out / CSV_NAME).write_text('x', encoding='utf-8')
    (out / MARKDOWN_NAME).write_text('x', encoding='utf-8')
    with pytest.raises(InvalidInputError, match='symbolic link'):
        write_configuration_space_reports(
            clearance_result, out, generated_at=_STAMP
        )


def test_empty_output_dir_rejected(clearance_result):
    with pytest.raises(InvalidInputError, match='non-empty'):
        write_configuration_space_reports(
            clearance_result, '   ', generated_at=_STAMP
        )


def test_em_dash_plain_string_rejected(clearance_result, tmp_path):
    records = list(clearance_result.records)
    records[0] = _record(
        sample_id=MD_NULL,
        evaluated_pair=records[0].evaluated_pair,
        geometry_source=records[0].geometry_source,
        limitation_reasons=records[0].limitation_reasons,
    )
    result = ConfigurationSpaceResult(
        records=tuple(records), summary=clearance_result.summary
    )
    with pytest.raises(InvalidInputError, match='missing-value marker'):
        write_configuration_space_reports(result, tmp_path, generated_at=_STAMP)
    assert _report_bytes(tmp_path) == {name: None for name in REPORT_NAMES}


def test_forbidden_status_words_absent(clearance_result, tmp_path):
    paths = write_configuration_space_reports(
        clearance_result, tmp_path, generated_at=_STAMP
    )
    blob = (
        paths['json'].read_text(encoding='utf-8')
        + paths['csv'].read_text(encoding='utf-8')
        + paths['markdown'].read_text(encoding='utf-8')
    )
    for word in FORBIDDEN_REPORT_STATUS_WORDS:
        assert word not in blob
    lowered = blob.lower()
    for phrase in FORBIDDEN_REPORT_PHRASES:
        assert phrase not in lowered


def _d1b_imports_argparse(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == 'argparse' or alias.name.startswith('argparse.')
                for alias in node.names
            ):
                return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == 'argparse' or node.module.startswith('argparse.'):
                return True
    return False


def _d1b_has_module_level_main(tree: ast.AST) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == 'main':
                return True
    return False


def _d1b_has_dunder_main_guard(tree: ast.AST) -> bool:
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


def _d1b_instantiates_argument_parser(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == 'ArgumentParser':
            return True
        if isinstance(func, ast.Attribute) and func.attr == 'ArgumentParser':
            return True
    return False


def _d1b_declares_console_scripts(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 'console_scripts':
            return True
    return False


def _d1b_parses_cli_arguments(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {'parse_args', 'add_argument', 'add_parser'}:
            return True
    return False


def test_no_cli_or_argparse_in_d1b_modules():
    for path in _D1B_PY_FILES:
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        assert not _d1b_imports_argparse(tree)
        assert not _d1b_has_module_level_main(tree)
        assert not _d1b_has_dunder_main_guard(tree)
        assert not _d1b_instantiates_argument_parser(tree)
        assert not _d1b_declares_console_scripts(tree)
        assert not _d1b_parses_cli_arguments(tree)
    yaml_text = default_report_config_path().read_text(encoding='utf-8')
    assert 'cli_registration_allowed: false' in yaml_text


def test_d1a_five_files_match_head():
    for relpath in _D1A_FILES:
        workspace = (_REPO_ROOT / relpath).read_bytes()
        head = _git_head_bytes(relpath)
        assert workspace == head
        assert _sha256_bytes(workspace) == _sha256_bytes(head)


def test_g1_g3_g4_d0_match_head():
    relpaths = list(FROZEN_INPUT_RELPATHS) + [
        'docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md',
        'docs/G3_REQUIREMENTS_EVIDENCE_GATES.md',
        'src/arachne_hx6_analysis/config/system_requirements.yaml',
        'src/arachne_hx6_analysis/config/evidence_ledger.yaml',
        'src/arachne_hx6_analysis/config/geometry_uncertainty_budget.yaml',
        'src/arachne_hx6_analysis/config/stow_requirements.yaml',
        'src/arachne_hx6_analysis/config/architecture_envelope.yaml',
        'src/arachne_hx6_analysis/config/propulsion_scenarios.yaml',
        'src/arachne_hx6_analysis/package.xml',
    ]
    for relpath in relpaths:
        workspace = (_REPO_ROOT / relpath).read_bytes()
        head = _git_head_bytes(relpath)
        assert workspace == head


def test_production_frozen_16362_and_606(production_result, tmp_path):
    paths = write_configuration_space_reports(
        production_result, tmp_path, generated_at=_STAMP
    )
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    assert payload['metadata']['n_records'] == 16362
    assert payload['metadata']['n_aabb_proxy_intersections'] == 606
    assert payload['metadata']['n_aabb_false_positive_limitations'] == 606
    assert len(payload['records']) == 16362
    csv_rows = list(csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines()))
    rec_rows = [row for row in csv_rows if row['row_type'] == 'record']
    assert len(rec_rows) == 16362
    md_text = paths['markdown'].read_text(encoding='utf-8')
    assert md_text.count('\n| path:') == 16362
    assert payload['metadata']['procurement_allowed'] is False
    assert compact_json(16362) == '16362'
    _assert_no_g4_temp_dirs(tmp_path)
