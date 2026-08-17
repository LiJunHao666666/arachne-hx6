"""G4-D1A offline in-memory configuration-space tests.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT. No report, CLI, or write-API tests.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import math
from pathlib import Path
import subprocess

import pytest
import yaml

from arachne_hx6_analysis.architecture_kinematics import _capsules_for_pose
from arachne_hx6_analysis.architecture_types import (
    LEG_JOINT_SUFFIXES,
    LEG_PREFIXES,
    REQUIRED_JOINT_NAMES,
)
from arachne_hx6_analysis.configuration_space_evaluate import (
    _analysis_disks,
    _capsules_by_name,
    _static_boxes,
    classify_signed_gap,
    default_approved_root,
    default_configuration_space_config_path,
    evaluate_configuration_space,
    evaluate_declared_pair_gap,
    git_blob_sha1,
    load_configuration_space_config,
    resolve_under_approved_root,
    signed_gap_aabb,
    verify_frozen_blob_bytes,
    verify_imported_frozen_python_modules,
)
from arachne_hx6_analysis.configuration_space_registry import (
    ANALYSIS_DISKS,
    CAMERA_LINK,
    EXCLUDED_PAIR_IDS,
    EXCLUSION_REASONS,
    FOOT_LINKS,
    INCLUDED_PAIR_IDS,
    LEG_SEGMENTS,
    SENSOR_PODS,
    pair_id,
    require_evaluable_pair,
    require_evaluable_pairs,
    reversed_pair_id,
    uses_aabb_proxy,
)
from arachne_hx6_analysis.configuration_space_types import (
    AFFIRMATIVE_SAMPLE_SET_STATUSES,
    APPROVED_SOLVER_TOLERANCE_M,
    CONFIGURATION_SPACE_UNSAMPLED,
    ConfigurationSpaceResult,
    EVALUATED_SCOPE,
    FORBIDDEN_STATUS_WORDS,
    FROZEN_INPUT_RELPATHS,
    FrozenGeometryModelError,
    G1_DESCRIPTION_COMMIT_SHA,
    G1_DESCRIPTION_TREE_SHA,
    G4_D0_CONTRACT_SHA256,
    HARDWARE_VALIDATION_NOT_VALIDATED,
    IMPLEMENTATION_SCOPE,
    LIMITATION_AABB_FALSE_POSITIVE,
    LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE,
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
    SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL,
    SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
    SOURCE_STATE_OR_PATH,
    SampleRecord,
    SampleSetSummary,
    require_unique_sample_ids,
)
from arachne_hx6_analysis.geometry import (
    Aabb,
    Capsule,
    HorizontalDisk,
    box_from_center_size,
)
from arachne_hx6_analysis.geometry_solver import GeometryConvergenceError
from arachne_hx6_analysis.model import InvalidInputError

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_IMPL_PY_FILES = (
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_types.py',
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_registry.py',
    _PACKAGE_ROOT / 'arachne_hx6_analysis' / 'configuration_space_evaluate.py',
)
_NEW_YAML = _PACKAGE_ROOT / 'config' / 'configuration_space.yaml'


def _joints(value: float = 0.01) -> dict[str, float]:
    return {name: value for name in REQUIRED_JOINT_NAMES}


def _record(**overrides):
    payload = {
        'sample_id': 'path:standing_to_analysis_stowed:i=00000:pair=lf_coxa__base_link',
        'source_state_or_path': SOURCE_STATE_OR_PATH,
        'evaluated_pair': 'lf_coxa__base_link',
        'joint_values': _joints(),
        'geometry_source': ('aabb_proxy', 'primitive=aabb_proxy'),
        'proxy_status': PROXY_STATUS_ANALYSIS_ONLY,
        'hardware_validation_status': HARDWARE_VALIDATION_NOT_VALIDATED,
        'nominal_separation_or_intersection': 0.05,
        'result_status': RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
        'limitation_reasons': (),
    }
    payload.update(overrides)
    return SampleRecord(**payload)


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


def _summary(**overrides):
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
        'implementation_scope': IMPLEMENTATION_SCOPE,
        'status': 'ANALYSIS_ONLY',
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


def _mutated_yaml(tmp_path: Path, mutate) -> Path:
    raw = yaml.safe_load(
        default_configuration_space_config_path().read_text(encoding='utf-8')
    )
    mutate(raw)
    dest = tmp_path / 'configuration_space.yaml'
    dest.write_text(yaml.safe_dump(raw, sort_keys=False), encoding='utf-8')
    return dest


def _copy_frozen(tmp_path: Path) -> Path:
    root = default_approved_root()
    for relpath in FROZEN_INPUT_RELPATHS:
        dest = tmp_path / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((root / relpath).read_bytes())
    return tmp_path


@pytest.fixture(scope='module')
def config():
    return load_configuration_space_config()


@pytest.fixture(scope='module')
def production_result():
    return evaluate_configuration_space()


def test_config_safety_and_authorization_fields(config):
    assert config.status == 'ANALYSIS_ONLY'
    assert config.implementation_authorization_status == 'GPT_AUTHORIZED'
    assert config.implementation_scope == IMPLEMENTATION_SCOPE
    assert config.procurement_allowed is False
    assert config.hardware_assembly_allowed is False
    assert config.report_file_generation_allowed is False
    assert config.cli_registration_allowed is False
    assert config.gazebo_allowed is False
    assert config.px4_allowed is False
    assert config.sample_count == SAMPLE_COUNT_REQUIRED
    assert config.source_state_or_path == SOURCE_STATE_OR_PATH
    assert config.solver_tolerance_m == APPROVED_SOLVER_TOLERANCE_M
    assert config.g4_d0_contract_sha256 == G4_D0_CONTRACT_SHA256
    assert config.hex_arm_span_m == pytest.approx(0.30)
    assert config.hex_rotor_radius_m == pytest.approx(0.060)


def test_unknown_config_key_is_invalid(tmp_path):
    path = _mutated_yaml(tmp_path, lambda raw: raw.__setitem__('not_authorized', True))
    with pytest.raises(InvalidInputError, match='unknown keys'):
        load_configuration_space_config(path)


@pytest.mark.parametrize(
    'field',
    [
        'procurement_allowed',
        'hardware_assembly_allowed',
        'report_file_generation_allowed',
        'cli_registration_allowed',
        'gazebo_allowed',
        'px4_allowed',
    ],
)
def test_forbidden_field_true_is_invalid(tmp_path, field):
    path = _mutated_yaml(tmp_path, lambda raw, name=field: raw.__setitem__(name, True))
    with pytest.raises(InvalidInputError, match=field):
        load_configuration_space_config(path)


def test_authorization_scope_mismatch_is_invalid(tmp_path):
    path = _mutated_yaml(
        tmp_path,
        lambda raw: raw.__setitem__(
            'implementation_scope', 'G4_D1B_REPORTS_AND_CLI'
        ),
    )
    with pytest.raises(InvalidInputError, match='implementation_scope'):
        load_configuration_space_config(path)


def test_authorization_status_mismatch_is_invalid(tmp_path):
    path = _mutated_yaml(
        tmp_path,
        lambda raw: raw.__setitem__(
            'implementation_authorization_status', 'NOT_AUTHORIZED'
        ),
    )
    with pytest.raises(InvalidInputError, match='implementation_authorization_status'):
        load_configuration_space_config(path)


def test_missing_units_are_invalid(tmp_path):
    path = _mutated_yaml(tmp_path, lambda raw: raw.__delitem__('joint_unit'))
    with pytest.raises(InvalidInputError, match='joint_unit'):
        load_configuration_space_config(path)
    path = _mutated_yaml(
        tmp_path,
        lambda raw: raw.__setitem__('length_unit', ''),
    )
    with pytest.raises(InvalidInputError):
        load_configuration_space_config(path)


def test_solver_tolerance_must_remain_1e_9(tmp_path):
    def mutate(raw):
        raw['solver']['tolerance_m'] = 1.0e-3
    path = _mutated_yaml(tmp_path, mutate)
    with pytest.raises(InvalidInputError, match='1e-9'):
        load_configuration_space_config(path)


@pytest.mark.parametrize('relpath', FROZEN_INPUT_RELPATHS)
def test_each_frozen_blob_correct_and_wrong(config, tmp_path, relpath):
    root = default_approved_root()
    blobs = {
        item: (root / item).read_bytes() for item in FROZEN_INPUT_RELPATHS
    }
    assert verify_frozen_blob_bytes(config, blobs) == ()
    wrong = dict(blobs)
    wrong[relpath] = blobs[relpath] + b'\n'
    with pytest.raises(InvalidInputError, match='frozen blob SHA mismatch'):
        verify_frozen_blob_bytes(config, wrong)


def test_tmp_dir_bytes_sha_without_git(config, tmp_path):
    _copy_frozen(tmp_path)
    blobs = {
        relpath: (tmp_path / relpath).read_bytes()
        for relpath in FROZEN_INPUT_RELPATHS
    }
    assert verify_frozen_blob_bytes(config, blobs) == ()
    sample = b'g4-d1a-bytes-only'
    digest = git_blob_sha1(sample)
    expected = hashlib.sha1(
        b'blob ' + str(len(sample)).encode('ascii') + b'\0' + sample
    ).hexdigest()
    assert digest == expected
    result = subprocess.run(
        ['git', 'rev-parse', '--is-inside-work-tree'],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 or 'true' not in result.stdout.lower()


def test_include_exclude_independently_constructed_against_production():
    segments = tuple(
        f'{prefix}_{suffix}'
        for prefix in LEG_PREFIXES
        for suffix in LEG_JOINT_SUFFIXES
    )
    disks = tuple(f'analysis_disk_hex_{index}' for index in range(1, 7))
    pods = ('left_sensor_pod', 'right_sensor_pod')
    camera = 'camera_link'
    hex_arms = tuple(f'hex_{index}_arm' for index in range(1, 7))
    urdf_rotors = tuple(f'hex_{index}_rotor' for index in range(1, 7))
    feet = tuple(f'{prefix}_foot' for prefix in LEG_PREFIXES)
    independent_include = (
        tuple(f'{segment}__{disk}' for segment in segments for disk in disks)
        + tuple(f'{pod}__{segment}' for pod in pods for segment in segments)
        + tuple(f'{segment}__base_link' for segment in segments)
    )
    independent_exclude = (
        tuple(f'{pod}__{disk}' for pod in pods for disk in disks)
        + tuple(
            f'{camera}__{target}'
            for target in disks + segments + pods + ('base_link',)
        )
        + tuple(
            f'{left_prefix}_{left_suffix}__{right_prefix}_{right_suffix}'
            for left_index, left_prefix in enumerate(LEG_PREFIXES)
            for right_prefix in LEG_PREFIXES[left_index + 1:]
            for left_suffix in LEG_JOINT_SUFFIXES
            for right_suffix in LEG_JOINT_SUFFIXES
        )
        + tuple(f'{segment}__{arm}' for segment in segments for arm in hex_arms)
        + tuple(f'{segment}__hex_hub' for segment in segments)
        + tuple(
            f'{segment}__{rotor}' for segment in segments for rotor in urdf_rotors
        )
        + tuple(f'{pod}__{foot}' for pod in pods for foot in feet)
    )
    assert len(segments) == 18
    assert len(disks) == 6
    assert len(independent_include) == 108 + 36 + 18
    assert len(independent_include) == 162
    assert len(independent_exclude) == 12 + 27 + 135 + 108 + 18 + 108 + 12
    assert len(independent_exclude) == 420
    assert independent_include == INCLUDED_PAIR_IDS
    assert independent_exclude == EXCLUDED_PAIR_IDS
    assert set(independent_include).isdisjoint(independent_exclude)
    assert set(EXCLUSION_REASONS) == set(independent_exclude)


def test_reversed_duplicate_unknown_pairs_rejected():
    canonical = 'lf_femur__analysis_disk_hex_1'
    with pytest.raises(InvalidInputError, match='direction'):
        require_evaluable_pair(reversed_pair_id(canonical))
    with pytest.raises(InvalidInputError, match='duplicate pair id'):
        require_evaluable_pairs((canonical, canonical))
    with pytest.raises(InvalidInputError, match='undeclared or unknown pair'):
        require_evaluable_pair('not_a_component__also_fake')
    with pytest.raises(InvalidInputError, match='undeclared or unknown pair'):
        require_evaluable_pair('lf_coxa__lf_femur')


def test_pod_disk_camera_and_pod_foot_rejected():
    with pytest.raises(InvalidInputError, match='excluded pair'):
        require_evaluable_pair(pair_id('left_sensor_pod', 'analysis_disk_hex_1'))
    with pytest.raises(InvalidInputError, match='excluded pair'):
        require_evaluable_pair(pair_id(CAMERA_LINK, 'base_link'))
    with pytest.raises(InvalidInputError, match='excluded pair'):
        require_evaluable_pair(pair_id('left_sensor_pod', 'lf_foot'))
    for pod in SENSOR_PODS:
        for disk in ANALYSIS_DISKS:
            assert pair_id(pod, disk) in EXCLUDED_PAIR_IDS
        for foot in FOOT_LINKS:
            assert pair_id(pod, foot) in EXCLUDED_PAIR_IDS


def test_production_101_path_expected_records(production_result):
    summary = production_result.summary
    assert summary.n_samples_requested == 101
    assert summary.n_samples_valid == 101
    assert summary.n_records_expected == N_RECORDS_EXPECTED_FULL == 16362
    assert summary.n_pair_instances_included == 162
    assert summary.n_pair_instances_excluded == 420
    assert summary.n_records_valid + summary.n_records_undetermined == 16362
    assert len(production_result.records) == summary.n_records_valid
    assert summary.configuration_space_status == CONFIGURATION_SPACE_UNSAMPLED
    assert summary.evaluated_scope == EVALUATED_SCOPE
    assert summary.transition_proof_flag == LIMITATION_SAMPLED_TRANSITION_ONLY
    assert summary.implementation_scope == IMPLEMENTATION_SCOPE
    assert summary.procurement_allowed is False
    assert summary.report_file_generation_allowed is False
    assert summary.cli_registration_allowed is False
    assert summary.gazebo_allowed is False
    assert summary.px4_allowed is False
    assert summary.hardware_assembly_allowed is False
    if summary.n_records_undetermined > 0:
        assert summary.sample_set_status == SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
        assert summary.sample_set_status not in (
            RESULT_SAMPLED_INTERSECTION_DETECTED,
            SAMPLE_SET_NO_INTERSECTION,
        )
    else:
        assert summary.sample_set_status in (
            RESULT_SAMPLED_INTERSECTION_DETECTED,
            SAMPLE_SET_NO_INTERSECTION,
        )
        assert len(production_result.records) == 16362


def test_disk_capsule_intersection_clearance_and_tolerance():
    disks = {
        'analysis_disk_hex_1': HorizontalDisk(
            name='hex_1', center=(0.0, 0.0, 0.0), radius=0.060
        )
    }
    far = {
        'lf_coxa': Capsule('lf_coxa', (2.0, 0.0, 0.0), (2.1, 0.0, 0.0), 0.01)
    }
    hit = {
        'lf_coxa': Capsule('lf_coxa', (0.0, 0.0, -0.05), (0.0, 0.0, 0.05), 0.01)
    }
    boxes = {}
    far_gap = evaluate_declared_pair_gap(
        'lf_coxa__analysis_disk_hex_1', far, disks, boxes
    )
    hit_gap = evaluate_declared_pair_gap(
        'lf_coxa__analysis_disk_hex_1', hit, disks, boxes
    )
    assert classify_signed_gap(far_gap) == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
    assert classify_signed_gap(hit_gap) == RESULT_SAMPLED_INTERSECTION_DETECTED
    assert classify_signed_gap(0.0) is None
    assert classify_signed_gap(APPROVED_SOLVER_TOLERANCE_M) is None
    assert classify_signed_gap(-APPROVED_SOLVER_TOLERANCE_M) is None
    assert classify_signed_gap(APPROVED_SOLVER_TOLERANCE_M * 2) == (
        RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
    )
    assert classify_signed_gap(-APPROVED_SOLVER_TOLERANCE_M * 2) == (
        RESULT_SAMPLED_INTERSECTION_DETECTED
    )


def test_aabb_separation_overlap_contact_and_tolerance():
    left = box_from_center_size((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    separated = box_from_center_size((3.0, 4.0, 0.0), (1.0, 1.0, 1.0))
    overlapped = box_from_center_size((0.20, 0.0, 0.0), (1.0, 1.0, 1.0))
    contact = box_from_center_size((1.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    sep = signed_gap_aabb(left, separated)
    over = signed_gap_aabb(left, overlapped)
    touch = signed_gap_aabb(left, contact)
    assert sep == pytest.approx(math.hypot(2.0, 3.0))
    assert sep > APPROVED_SOLVER_TOLERANCE_M
    assert over < -APPROVED_SOLVER_TOLERANCE_M
    assert touch == pytest.approx(0.0)
    assert classify_signed_gap(sep) == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
    assert classify_signed_gap(over) == RESULT_SAMPLED_INTERSECTION_DETECTED
    assert classify_signed_gap(touch) is None
    sliver = Aabb(minimum=(0.5, -0.5, -0.5), maximum=(1.5, 0.5, 0.5))
    # left max x is 0.5, sliver min x is 0.5: contact, not separation.
    assert signed_gap_aabb(left, sliver) == pytest.approx(0.0)


def test_aabb_false_positive_limitation():
    record = _record(
        evaluated_pair='left_sensor_pod__lf_coxa',
        result_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
        nominal_separation_or_intersection=-0.02,
        limitation_reasons=(LIMITATION_AABB_FALSE_POSITIVE,),
        geometry_source=('aabb_proxy', 'primitive=aabb_proxy', 'aabb_proxy'),
    )
    assert LIMITATION_AABB_FALSE_POSITIVE in record.limitation_reasons
    assert record.proxy_status == PROXY_STATUS_ANALYSIS_ONLY
    capsules = {
        'lf_coxa': Capsule('lf_coxa', (0.0, 0.0, 0.0), (0.05, 0.0, 0.0), 0.02)
    }
    boxes = {
        'left_sensor_pod': box_from_center_size((0.0, 0.0, 0.0), (0.2, 0.2, 0.2))
    }
    gap = evaluate_declared_pair_gap(
        'left_sensor_pod__lf_coxa', capsules, {}, boxes
    )
    assert classify_signed_gap(gap) == RESULT_SAMPLED_INTERSECTION_DETECTED


def test_empty_sample_set_is_invalid_input(config):
    with pytest.raises(InvalidInputError, match='empty sample set'):
        evaluate_configuration_space(config, poses=())


def test_unknown_joint_and_link_are_invalid(config):
    bad = _joints()
    bad['not_a_joint'] = 0.1
    with pytest.raises(InvalidInputError, match='unknown joints'):
        evaluate_configuration_space(config, poses=(bad,))
    with pytest.raises(InvalidInputError, match='unknown'):
        require_evaluable_pair('lf_coxa__mystery_link')


def test_non_finite_values_are_invalid(config):
    bad = _joints()
    bad['lf_coxa_joint'] = math.inf
    with pytest.raises(InvalidInputError, match='finite'):
        evaluate_configuration_space(config, poses=(bad,))
    with pytest.raises(InvalidInputError, match='finite'):
        classify_signed_gap(math.nan)
    with pytest.raises(InvalidInputError, match='sample_id'):
        _record(sample_id='   ')


def test_blank_and_duplicate_sample_ids_are_invalid():
    with pytest.raises(InvalidInputError, match='sample_id'):
        _record(sample_id='')
    left = _record()
    right = _record()
    with pytest.raises(InvalidInputError, match='duplicate sample_id'):
        require_unique_sample_ids((left, right))


def test_missing_runtime_input_is_undetermined_missing(config, tmp_path):
    _copy_frozen(tmp_path)
    (tmp_path / FROZEN_INPUT_RELPATHS[0]).unlink()
    result = evaluate_configuration_space(config, approved_root=tmp_path)
    assert result.summary.sample_set_status == SAMPLE_SET_UNDETERMINED_MISSING_INPUT
    assert result.summary.configuration_space_status == CONFIGURATION_SPACE_UNSAMPLED
    assert result.records == ()
    assert result.summary.n_records_undetermined == N_RECORDS_EXPECTED_FULL
    assert result.summary.sample_set_status not in (
        RESULT_SAMPLED_INTERSECTION_DETECTED,
        SAMPLE_SET_NO_INTERSECTION,
    )


def test_partial_model_invalid_is_undetermined_geometry(config, monkeypatch):
    def boom(*_args, **_kwargs):
        raise GeometryConvergenceError('injected uncertified gap')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate.signed_distance_disk_capsule',
        boom,
    )
    standing = _joints(0.01)
    result = evaluate_configuration_space(config, poses=(standing,))
    assert result.summary.sample_set_status == SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
    assert LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE in result.summary.limitation_reasons
    assert result.summary.sample_set_status not in (
        RESULT_SAMPLED_INTERSECTION_DETECTED,
        SAMPLE_SET_NO_INTERSECTION,
    )


def test_undetermined_status_has_priority(config, tmp_path, production_result):
    _copy_frozen(tmp_path)
    (tmp_path / FROZEN_INPUT_RELPATHS[1]).unlink()
    missing = evaluate_configuration_space(config, approved_root=tmp_path)
    assert missing.summary.sample_set_status == SAMPLE_SET_UNDETERMINED_MISSING_INPUT
    if production_result.summary.n_records_undetermined > 0:
        assert production_result.summary.sample_set_status == (
            SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
        )
    assert missing.summary.configuration_space_status == CONFIGURATION_SPACE_UNSAMPLED
    assert production_result.summary.configuration_space_status == (
        CONFIGURATION_SPACE_UNSAMPLED
    )


def test_included_excluded_coverage_metadata(production_result):
    summary = production_result.summary
    assert tuple(summary.included_pair_ids) == INCLUDED_PAIR_IDS
    assert tuple(summary.excluded_pair_ids) == EXCLUDED_PAIR_IDS
    assert dict(summary.exclusion_reasons) == EXCLUSION_REASONS
    for record in production_result.records:
        assert record.evaluated_pair in INCLUDED_PAIR_IDS
        assert record.evaluated_pair not in EXCLUDED_PAIR_IDS


def test_no_intersection_is_limited_to_included_scope(production_result):
    summary = production_result.summary
    assert summary.evaluated_scope == EVALUATED_SCOPE
    if summary.sample_set_status == SAMPLE_SET_NO_INTERSECTION:
        assert summary.n_records_valid == N_RECORDS_EXPECTED_FULL
        assert all(
            record.result_status == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
            for record in production_result.records
        )
    for record in production_result.records:
        assert record.result_status in (
            RESULT_SAMPLED_INTERSECTION_DETECTED,
            RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
        )


def test_configuration_space_status_always_unsampled(production_result, config, tmp_path):
    assert production_result.summary.configuration_space_status == (
        CONFIGURATION_SPACE_UNSAMPLED
    )
    _copy_frozen(tmp_path)
    (tmp_path / FROZEN_INPUT_RELPATHS[2]).unlink()
    missing = evaluate_configuration_space(config, approved_root=tmp_path)
    assert missing.summary.configuration_space_status == CONFIGURATION_SPACE_UNSAMPLED


def test_no_file_write_report_or_cli_interface():
    for path in _IMPL_PY_FILES:
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assert not node.name.startswith('write_')
                assert not node.name.startswith('save_')
                assert 'cli' not in node.name.lower()
                assert 'report' not in node.name.lower()
            if isinstance(node, ast.Call):
                func = node.func
                name = ''
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in {'dump', 'dumps', 'write_text', 'write_bytes'}:
                    pytest.fail(f'{path.name} contains {name}()')
        assert 'console_scripts' not in source
        assert 'argparse' not in source
        assert 'json.dump' not in source
        assert 'csv.writer' not in source
    yaml_text = _NEW_YAML.read_text(encoding='utf-8')
    assert 'cli_registration_allowed: false' in yaml_text
    assert 'report_file_generation_allowed: false' in yaml_text
    assert 'file_bytes' not in inspect.signature(evaluate_configuration_space).parameters


def test_forbidden_status_words_are_not_serialized(production_result):
    summary = production_result.summary
    statuses = {
        summary.sample_set_status,
        summary.configuration_space_status,
        summary.proxy_status if hasattr(summary, 'proxy_status') else '',
        summary.status,
        summary.implementation_scope,
    }
    statuses.update(record.result_status for record in production_result.records)
    statuses.update(record.proxy_status for record in production_result.records)
    statuses.update(
        record.hardware_validation_status for record in production_result.records
    )
    for word in FORBIDDEN_STATUS_WORDS:
        assert word not in statuses
    source = (
        default_configuration_space_config_path().read_text(encoding='utf-8')
        + '\n'
        + Path(__file__).read_text(encoding='utf-8')
    )
    # Production modules may mention the forbidden list only as a rejection set.
    types_source = _IMPL_PY_FILES[0].read_text(encoding='utf-8')
    assert 'FORBIDDEN_STATUS_WORDS' in types_source


def test_g1_g2_g3_g4_tracked_files_unchanged(config):
    root = default_approved_root()
    for spec in config.frozen_inputs:
        data = (root / spec.relpath).read_bytes()
        assert git_blob_sha1(data) == spec.git_blob_sha1
    contract = root / 'docs' / 'G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md'
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    assert digest == G4_D0_CONTRACT_SHA256
    diff = subprocess.run(
        ['git', 'diff', '--name-only'],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout.strip() == ''
    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard'],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    allowed = {
        'src/arachne_hx6_analysis/config/configuration_space.yaml',
        'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_types.py',
        'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_registry.py',
        'src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_evaluate.py',
        'src/arachne_hx6_analysis/test/test_configuration_space.py',
    }
    assert set(untracked.stdout.split()) <= allowed


def test_path_escape_is_invalid():
    root = default_approved_root()
    with pytest.raises(InvalidInputError, match='escapes'):
        resolve_under_approved_root(root, '../secret.yaml')
    with pytest.raises(InvalidInputError, match='escapes'):
        resolve_under_approved_root(root, '/etc/passwd')


def test_gap_within_tolerance_does_not_build_affirmative_record():
    with pytest.raises(InvalidInputError, match='solver tolerance'):
        _record(nominal_separation_or_intersection=0.0)
    with pytest.raises(InvalidInputError, match='solver tolerance'):
        _record(
            nominal_separation_or_intersection=APPROVED_SOLVER_TOLERANCE_M / 2.0
        )


def test_leg_segments_and_disks_are_the_closed_sets():
    assert len(LEG_SEGMENTS) == 18
    assert len(ANALYSIS_DISKS) == 6
    assert 'lf_foot' not in LEG_SEGMENTS
    assert all(name.startswith('analysis_disk_hex_') for name in ANALYSIS_DISKS)


def test_correct_bytes_do_not_override_tampered_approved_root_files(config, tmp_path):
    _copy_frozen(tmp_path)
    correct = {
        relpath: (tmp_path / relpath).read_bytes()
        for relpath in FROZEN_INPUT_RELPATHS
    }
    assert verify_frozen_blob_bytes(config, correct) == ()
    xacro_relpath = FROZEN_INPUT_RELPATHS[1]
    (tmp_path / xacro_relpath).write_bytes(
        correct[xacro_relpath] + b'\n#tampered-xacro\n'
    )
    standing_relpath = FROZEN_INPUT_RELPATHS[0]
    (tmp_path / standing_relpath).write_bytes(
        correct[standing_relpath] + b'\n#tampered-standing\n'
    )
    assert verify_frozen_blob_bytes(config, correct) == ()
    with pytest.raises(InvalidInputError, match='frozen blob SHA mismatch'):
        evaluate_configuration_space(config, approved_root=tmp_path)
    assert 'file_bytes' not in inspect.signature(
        evaluate_configuration_space
    ).parameters


def test_approved_pair_missing_runtime_model_is_undetermined_geometry(
    config, monkeypatch
):
    standing = _joints(0.01)
    complete = evaluate_configuration_space(config, poses=(standing,))
    assert complete.summary.n_records_valid == N_PAIR_INSTANCES_INCLUDED
    assert complete.summary.sample_set_status not in AFFIRMATIVE_SAMPLE_SET_STATUSES

    def drop_capsule(pose, baseline):
        named = {
            capsule.name: capsule for capsule in _capsules_for_pose(pose, baseline)
        }
        named.pop('lf_coxa')
        return named

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate._capsules_by_name',
        drop_capsule,
    )
    missing = evaluate_configuration_space(config, poses=(standing,))
    assert missing.summary.sample_set_status == SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
    assert missing.summary.sample_set_status not in AFFIRMATIVE_SAMPLE_SET_STATUSES
    assert missing.summary.n_records_valid < complete.summary.n_records_valid
    assert missing.summary.n_records_undetermined > 0


def test_missing_capsule_or_disk_for_approved_pair_is_geometry_model_error():
    disks = {
        'analysis_disk_hex_1': HorizontalDisk(
            name='hex_1', center=(0.0, 0.0, 0.0), radius=0.060
        )
    }
    with pytest.raises(FrozenGeometryModelError, match='missing capsule'):
        evaluate_declared_pair_gap(
            'lf_coxa__analysis_disk_hex_1', {}, disks, {}
        )
    with pytest.raises(FrozenGeometryModelError, match='missing analysis disk'):
        evaluate_declared_pair_gap(
            'lf_coxa__analysis_disk_hex_1',
            {'lf_coxa': Capsule('lf_coxa', (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 0.01)},
            {},
            {},
        )
    with pytest.raises(InvalidInputError, match='undeclared or unknown pair'):
        evaluate_declared_pair_gap('lf_coxa__mystery_link', {}, {}, {})


def test_contradictory_record_gap_status_and_limitations_are_rejected():
    with pytest.raises(InvalidInputError, match='gap < -tolerance'):
        _record(
            result_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
            nominal_separation_or_intersection=0.05,
            limitation_reasons=(LIMITATION_AABB_FALSE_POSITIVE,),
        )
    with pytest.raises(InvalidInputError, match='gap > tolerance'):
        _record(
            result_status=RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
            nominal_separation_or_intersection=-0.05,
        )
    with pytest.raises(InvalidInputError, match='AABB intersection'):
        _record(
            result_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
            nominal_separation_or_intersection=-0.02,
            limitation_reasons=(),
            geometry_source=('aabb_proxy', 'primitive=aabb_proxy', 'aabb_proxy'),
        )
    with pytest.raises(InvalidInputError, match='tibia endpoint'):
        _record(
            sample_id='path:standing_to_analysis_stowed:i=00000:pair=lf_tibia__analysis_disk_hex_1',
            evaluated_pair='lf_tibia__analysis_disk_hex_1',
            result_status=RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
            nominal_separation_or_intersection=0.05,
            geometry_source=('disk_capsule', 'primitive=signed_distance_disk_capsule'),
            limitation_reasons=(),
        )


def test_contradictory_summary_and_result_constructions_are_rejected():
    with pytest.raises(InvalidInputError, match='n_samples_valid'):
        _summary(n_samples_valid=102)
    with pytest.raises(InvalidInputError, match='n_samples_valid'):
        _summary(n_samples_valid=-1)
    with pytest.raises(InvalidInputError, match='affirmative sample_set_status'):
        _summary(
            sample_set_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
            n_samples_valid=101,
            n_records_valid=0,
            n_records_undetermined=N_RECORDS_EXPECTED_FULL,
        )
    clearance = _one_sample_records(
        RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE, 0.05
    )
    hit_summary = _summary(
        sample_set_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
        n_samples_requested=1,
        n_samples_valid=1,
        n_records_expected=N_PAIR_INSTANCES_INCLUDED,
        n_records_valid=N_PAIR_INSTANCES_INCLUDED,
        n_records_undetermined=0,
    )
    with pytest.raises(InvalidInputError, match='recomputed from records'):
        ConfigurationSpaceResult(records=clearance, summary=hit_summary)
    mixed = list(clearance)
    mixed[0] = _record(
        sample_id=clearance[0].sample_id,
        evaluated_pair=clearance[0].evaluated_pair,
        geometry_source=clearance[0].geometry_source,
        result_status=RESULT_SAMPLED_INTERSECTION_DETECTED,
        nominal_separation_or_intersection=-0.02,
        limitation_reasons=_limitations_for(
            clearance[0].evaluated_pair, RESULT_SAMPLED_INTERSECTION_DETECTED
        ),
    )
    no_hit_summary = _summary(
        sample_set_status=SAMPLE_SET_NO_INTERSECTION,
        n_samples_requested=1,
        n_samples_valid=1,
        n_records_expected=N_PAIR_INSTANCES_INCLUDED,
        n_records_valid=N_PAIR_INSTANCES_INCLUDED,
        n_records_undetermined=0,
    )
    with pytest.raises(InvalidInputError, match='recomputed from records'):
        ConfigurationSpaceResult(records=tuple(mixed), summary=no_hit_summary)
    with pytest.raises(InvalidInputError, match='affirmative'):
        _summary(
            sample_set_status=SAMPLE_SET_NO_INTERSECTION,
            n_samples_requested=1,
            n_samples_valid=1,
            n_records_expected=N_PAIR_INSTANCES_INCLUDED,
            n_records_valid=N_PAIR_INSTANCES_INCLUDED - 1,
            n_records_undetermined=1,
        )


def test_production_result_has_16362_records_and_606_aabb_intersections(
    production_result,
):
    records = production_result.records
    summary = production_result.summary
    assert len(records) == 16362
    assert summary.n_records_valid == 16362
    assert summary.n_records_undetermined == 0
    intersections = [
        record
        for record in records
        if record.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED
    ]
    assert len(intersections) == 606
    for record in intersections:
        assert uses_aabb_proxy(record.evaluated_pair)
        assert LIMITATION_AABB_FALSE_POSITIVE in record.limitation_reasons
        assert record.nominal_separation_or_intersection < (
            -APPROVED_SOLVER_TOLERANCE_M
        )
    for record in records:
        if record.result_status == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE:
            assert record.nominal_separation_or_intersection > (
                APPROVED_SOLVER_TOLERANCE_M
            )
        left, right = record.evaluated_pair.split('__')
        if left.endswith('_tibia') or right.endswith('_tibia'):
            assert LIMITATION_TIBIA_FOOT_ENDPOINT in record.limitation_reasons
    assert summary.sample_set_status == RESULT_SAMPLED_INTERSECTION_DETECTED


def _assert_undetermined_geometry(result):
    assert result.summary.sample_set_status == SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
    assert result.summary.sample_set_status not in AFFIRMATIVE_SAMPLE_SET_STATUSES
    assert result.summary.n_records_undetermined > 0


def test_disk_construction_failure_is_undetermined_geometry(config, monkeypatch):
    def boom(*_args, **_kwargs):
        raise InvalidInputError('injected disk construction failure')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate.make_rotor_disks',
        boom,
    )
    dummy = type('Baseline', (), {'rotor_plane_z_m': 0.0, 'first_motor_yaw_rad': 0.0})()
    with pytest.raises(FrozenGeometryModelError, match='analysis disk model'):
        _analysis_disks(dummy)
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)
    assert result.records == ()


def test_static_aabb_construction_failure_is_undetermined_geometry(
    config, monkeypatch
):
    def boom(*_args, **_kwargs):
        raise InvalidInputError('injected AABB construction failure')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate.box_from_center_size',
        boom,
    )
    dummy = type(
        'Baseline',
        (),
        {
            'body_length_m': 0.1,
            'body_width_m': 0.1,
            'body_height_m': 0.1,
            'sensor_pod_y_m': 0.1,
            'sensor_pod_z_m': 0.1,
            'sensor_pod_size_x_m': 0.05,
            'sensor_pod_size_y_m': 0.05,
            'sensor_pod_size_z_m': 0.05,
        },
    )()
    with pytest.raises(FrozenGeometryModelError, match='static AABB model'):
        _static_boxes(dummy)
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)
    assert result.records == ()


def test_capsule_construction_error_is_undetermined_geometry(config, monkeypatch):
    def boom(*_args, **_kwargs):
        raise InvalidInputError('injected capsule construction failure')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate._capsules_for_pose',
        boom,
    )
    with pytest.raises(FrozenGeometryModelError, match='capsule model construction'):
        _capsules_by_name({}, object())
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)
    assert result.records == ()


def test_duplicate_capsule_name_is_undetermined_geometry(config, monkeypatch):
    def dups(*_args, **_kwargs):
        capsule = Capsule('lf_coxa', (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 0.01)
        return (capsule, capsule)

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate._capsules_for_pose',
        dups,
    )
    with pytest.raises(FrozenGeometryModelError, match='duplicate capsule name'):
        _capsules_by_name({}, object())
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)
    assert result.records == ()


def test_missing_foot_endpoint_is_undetermined_geometry(config, monkeypatch):
    def no_feet(*_args, **_kwargs):
        return tuple(
            Capsule(name, (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 0.01)
            for name in LEG_SEGMENTS
        )

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate._capsules_for_pose',
        no_feet,
    )
    with pytest.raises(FrozenGeometryModelError, match='missing foot endpoint'):
        _capsules_by_name({}, object())
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)
    assert result.records == ()


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf])
def test_disk_capsule_nonfinite_gap_is_undetermined_geometry(
    config, monkeypatch, value
):
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate.signed_distance_disk_capsule',
        lambda *_args, **_kwargs: value,
    )
    disks = {
        'analysis_disk_hex_1': HorizontalDisk(
            name='hex_1', center=(0.0, 0.0, 0.0), radius=0.060
        )
    }
    capsules = {
        'lf_coxa': Capsule('lf_coxa', (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 0.01)
    }
    with pytest.raises(FrozenGeometryModelError, match='not finite'):
        evaluate_declared_pair_gap(
            'lf_coxa__analysis_disk_hex_1', capsules, disks, {}
        )
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf])
def test_aabb_nonfinite_gap_is_undetermined_geometry(config, monkeypatch, value):
    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate.signed_gap_aabb',
        lambda *_args, **_kwargs: value,
    )
    capsules = {
        'lf_coxa': Capsule('lf_coxa', (0.0, 0.0, 0.0), (0.05, 0.0, 0.0), 0.02)
    }
    boxes = {
        'left_sensor_pod': box_from_center_size((0.0, 0.0, 0.0), (0.2, 0.2, 0.2))
    }
    with pytest.raises(FrozenGeometryModelError, match='not finite'):
        evaluate_declared_pair_gap(
            'left_sensor_pod__lf_coxa', capsules, {}, boxes
        )
    result = evaluate_configuration_space(config, poses=(_joints(0.01),))
    _assert_undetermined_geometry(result)


def test_imported_module_sha_mismatch_despite_correct_approved_root(
    config, tmp_path, monkeypatch
):
    root = _copy_frozen(tmp_path)
    import arachne_hx6_analysis.geometry as geometry_mod

    tampered = tmp_path / 'tampered_geometry.py'
    tampered.write_bytes(Path(geometry_mod.__file__).read_bytes() + b'\n#split-source\n')
    monkeypatch.setattr(geometry_mod, '__file__', str(tampered))

    def no_eval(*_args, **_kwargs):
        raise AssertionError('evaluation started after imported SHA mismatch')

    monkeypatch.setattr(
        'arachne_hx6_analysis.configuration_space_evaluate._read_frozen_from_root',
        no_eval,
    )
    with pytest.raises(InvalidInputError, match='imported module SHA mismatch'):
        evaluate_configuration_space(config, approved_root=root)


def test_imported_frozen_python_modules_match_without_git(config, monkeypatch):
    def forbid_git(*_args, **_kwargs):
        raise AssertionError('git subprocess invoked')

    monkeypatch.setattr(subprocess, 'run', forbid_git)
    monkeypatch.setattr(subprocess, 'Popen', forbid_git)
    monkeypatch.setattr(subprocess, 'check_output', forbid_git)
    verify_imported_frozen_python_modules(config)


def test_unknown_joint_pair_and_sha_mismatch_remain_invalid_input(config, tmp_path):
    bad = _joints()
    bad['not_a_joint'] = 0.1
    with pytest.raises(InvalidInputError, match='unknown joints'):
        evaluate_configuration_space(config, poses=(bad,))
    with pytest.raises(InvalidInputError, match='undeclared or unknown pair'):
        evaluate_configuration_space(
            config, poses=(_joints(0.01),), pair_ids=('lf_coxa__mystery_link',)
        )
    _copy_frozen(tmp_path)
    (tmp_path / FROZEN_INPUT_RELPATHS[0]).write_bytes(
        (tmp_path / FROZEN_INPUT_RELPATHS[0]).read_bytes() + b'\n#sha\n'
    )
    with pytest.raises(InvalidInputError, match='frozen blob SHA mismatch'):
        evaluate_configuration_space(config, approved_root=tmp_path)


def test_evaluation_loop_does_not_catch_all_invalid_input_error():
    source = inspect.getsource(evaluate_configuration_space)
    assert 'except InvalidInputError' not in source
    assert 'except FrozenGeometryModelError' in source
