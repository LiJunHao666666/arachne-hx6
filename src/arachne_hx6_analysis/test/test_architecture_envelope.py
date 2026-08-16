"""G2 ANALYSIS_ONLY architecture-envelope tests. No GUI."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from arachne_hx6_analysis.architecture import (
    ALLOWED_ARCHITECTURE_GATES,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARM_COUPLING_BASELINE,
    ARM_COUPLING_UNMODELED,
    ARM_EXTENSION_LIMITATION_REASON,
    EVIDENCE_MISSING,
    FORBIDDEN_ARCHITECTURE_STATUS_WORDS,
    GATE_CLEARANCE_MET,
    GATE_CLEARANCE_NOT_MET,
    MASS_LEDGER_INCOMPLETE,
    NOMINAL_GEOMETRY_MET,
    NOMINAL_GEOMETRY_NOT_MET,
    POSE_KIND_ANALYSIS_ONLY,
    REQUIRED_INTERMEDIATE_DIAMETERS_IN,
    REQUIRED_JOINT_NAMES,
    REQUIRED_MASS_LEDGER_ITEMS,
    ROBUST_GATE_UNQUANTIFIED,
    ROBUST_GEOMETRY_UNDETERMINED,
    STOW_POSE_EVIDENCE_UNQUALIFIED,
    STOW_REQUIREMENTS_INCOMPLETE,
    TRANSITION_PROOF_FLAG,
    _g1_baseline_from_xacro,
    evaluate_architecture,
    interpolate_joint_path,
    load_architecture_config,
    load_standing_joints,
    parse_xacro_numeric_properties,
    validate_joint_pose,
)
from arachne_hx6_analysis.architecture_cli import main as architecture_main
from arachne_hx6_analysis.architecture_report import (
    CSV_NAME,
    JSON_NAME,
    MARKDOWN_NAME,
    MD_NULL,
    assert_strict_finite_json,
    write_architecture_reports,
)
from arachne_hx6_analysis.geometry import (
    CONVERGENCE_CERTIFIED,
    GEOMETRY_SOLVER_TOLERANCE_M,
    Capsule,
    HorizontalDisk,
    adjacent_rotor_tip_clearance_m,
    box_from_center_size,
    hex_layout_metrics,
    make_rotor_disks,
    signed_distance_disk_aabb,
    signed_distance_disk_capsule,
    signed_distance_horizontal_disks,
)
from arachne_hx6_analysis.model import (
    INCH_TO_METRE,
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
    adjacent_motor_center_distance_m,
    min_motor_center_radius_m,
)

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PACKAGE_ROOT / 'config' / 'architecture_envelope.yaml'


def _write_mutated_config(tmp_path, mutate):
    raw = yaml.safe_load(_CONFIG_PATH.read_text(encoding='utf-8'))
    mutate(raw)
    path = tmp_path / 'mutated_architecture.yaml'
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding='utf-8')
    return path


@pytest.fixture(scope='module')
def config():
    return load_architecture_config(_CONFIG_PATH)


@pytest.fixture(scope='module')
def result(config):
    return evaluate_architecture(config)


def test_hexarotor_adjacent_center_formula():
    radius_m = 0.30
    rotor_count = 6
    adjacent = adjacent_motor_center_distance_m(radius_m, rotor_count)
    assert adjacent == pytest.approx(2.0 * radius_m * math.sin(math.pi / 6.0))
    assert adjacent == pytest.approx(radius_m)


def test_min_motor_center_radius_formula():
    diameter_m = 0.254
    tip = 0.02
    min_r = min_motor_center_radius_m(diameter_m, tip, 6)
    assert min_r == pytest.approx(
        (diameter_m + tip) / (2.0 * math.sin(math.pi / 6.0))
    )
    assert min_r == pytest.approx(diameter_m + tip)


def _geometry_row(result, diameter_inch, radius_m):
    matches = [
        row for row in result.geometry_candidates
        if abs(row.diameter_inch - diameter_inch) < 1.0e-9
        and abs(row.motor_center_radius_m - radius_m) < 1.0e-12
    ]
    assert len(matches) == 1
    return matches[0]


def test_47_inch_r30_adjacent_tip_clearance_passes(result):
    row = _geometry_row(result, 4.7, 0.30)
    assert row.adjacent_rotor_tip_clearance_m == pytest.approx(
        0.30 - 4.7 * INCH_TO_METRE
    )
    assert row.adjacent_rotor_tip_clearance_m >= 0.02
    assert row.rotor_spacing_gate == GATE_CLEARANCE_MET


def test_12_inch_r30_fails_20mm_tip_clearance(result):
    row = _geometry_row(result, 12.0, 0.30)
    assert row.adjacent_rotor_tip_clearance_m == pytest.approx(0.30 - 0.3048)
    assert row.adjacent_rotor_tip_clearance_m < 0.02
    assert row.rotor_spacing_gate == GATE_CLEARANCE_NOT_MET


def test_15_inch_r30_adjacent_tip_clearance_fails(result):
    row = _geometry_row(result, 15.0, 0.30)
    assert row.adjacent_rotor_tip_clearance_m < 0.02
    assert row.rotor_spacing_gate == GATE_CLEARANCE_NOT_MET


def test_10_inch_r30_tip_clearance_numeric_regression(result):
    row = _geometry_row(result, 10.0, 0.30)
    diameter_m = 10.0 * INCH_TO_METRE
    expected = 0.30 - diameter_m
    assert diameter_m == pytest.approx(0.254)
    assert row.adjacent_rotor_tip_clearance_m == pytest.approx(expected)
    assert row.adjacent_rotor_tip_clearance_m == pytest.approx(0.046)
    metrics = hex_layout_metrics(0.30, diameter_m, 6, 0.02)
    assert metrics['adjacent_rotor_tip_clearance_m'] == pytest.approx(0.046)
    assert adjacent_rotor_tip_clearance_m(0.30, diameter_m, 6) == pytest.approx(
        0.046
    )


def test_disk_aabb_canonical_cases():
    disk = HorizontalDisk('d', (0.0, 0.0, 2.0), 1.0)
    box = box_from_center_size((0.0, 0.0, 0.0), (2.0, 2.0, 2.0))
    assert signed_distance_disk_aabb(disk, box) == pytest.approx(1.0)

    side = HorizontalDisk('s', (3.0, 0.0, 0.0), 1.0)
    assert signed_distance_disk_aabb(side, box) == pytest.approx(1.0)

    hit = HorizontalDisk('h', (0.0, 0.0, 0.0), 1.0)
    assert signed_distance_disk_aabb(hit, box) < 0.0

    corner = HorizontalDisk('c', (3.0, 3.0, 3.0), 0.5)
    xy_signed = math.hypot(2.0, 2.0) - 0.5
    expected = math.hypot(xy_signed, 2.0)
    assert signed_distance_disk_aabb(corner, box) == pytest.approx(expected)


def test_disk_capsule_canonical_cases():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    above = Capsule('above', (0.0, 0.0, 2.0), (0.0, 0.0, 3.0), 0.1)
    assert signed_distance_disk_capsule(disk, above) == pytest.approx(1.9)

    side = Capsule('side', (3.0, 0.0, 0.0), (4.0, 0.0, 0.0), 0.1)
    assert signed_distance_disk_capsule(disk, side) == pytest.approx(1.9)

    pierce = Capsule('pierce', (0.0, 0.0, -1.0), (0.0, 0.0, 1.0), 0.1)
    assert signed_distance_disk_capsule(disk, pierce) == pytest.approx(-0.1)

    other = HorizontalDisk('e', (3.0, 0.0, 0.0), 1.0)
    assert signed_distance_horizontal_disks(disk, other) == pytest.approx(1.0)


def test_eighteen_joint_pose_integrity(config, result):
    assert len(REQUIRED_JOINT_NAMES) == 18
    assert set(result.standing_joints) == set(REQUIRED_JOINT_NAMES)
    assert set(result.analysis_stowed_joints) == set(REQUIRED_JOINT_NAMES)
    assert len(result.analysis_stowed_joints) == 18
    assert config.analysis_stowed_pose_kind == POSE_KIND_ANALYSIS_ONLY
    xacro = parse_xacro_numeric_properties(config.xacro_path)
    limits = {}
    for name in REQUIRED_JOINT_NAMES:
        if name.endswith('_coxa_joint'):
            limits[name] = (xacro['coxa_lower'], xacro['coxa_upper'])
        elif name.endswith('_femur_joint'):
            limits[name] = (xacro['femur_lower'], xacro['femur_upper'])
        else:
            limits[name] = (xacro['tibia_lower'], xacro['tibia_upper'])
    validated = validate_joint_pose(
        result.analysis_stowed_joints, limits, 'analysis_stowed.joints'
    )
    assert validated == dict(result.analysis_stowed_joints)


def test_pose_joint_limit_enforced(config):
    xacro = parse_xacro_numeric_properties(config.xacro_path)
    limits = {
        name: (xacro['coxa_lower'], xacro['coxa_upper'])
        if name.endswith('_coxa_joint')
        else (
            (xacro['femur_lower'], xacro['femur_upper'])
            if name.endswith('_femur_joint')
            else (xacro['tibia_lower'], xacro['tibia_upper'])
        )
        for name in REQUIRED_JOINT_NAMES
    }
    standing = load_standing_joints(config.standing_pose_path)
    bad = dict(standing)
    bad['lf_coxa_joint'] = xacro['coxa_upper'] + 0.01
    with pytest.raises(InvalidInputError, match='lf_coxa_joint'):
        validate_joint_pose(bad, limits, 'analysis_stowed.joints')
    missing = dict(standing)
    missing.pop('rr_tibia_joint')
    with pytest.raises(InvalidInputError, match='missing joints'):
        validate_joint_pose(missing, limits, 'analysis_stowed.joints')
    extra = dict(standing)
    extra['not_a_joint'] = 0.0
    with pytest.raises(InvalidInputError, match='unknown joints'):
        validate_joint_pose(extra, limits, 'analysis_stowed.joints')


def test_path_sample_count_and_endpoints(config, result):
    assert config.sample_count == 101
    path = interpolate_joint_path(
        result.standing_joints, result.analysis_stowed_joints, 101
    )
    assert len(path) == 101
    for name in REQUIRED_JOINT_NAMES:
        assert path[0][name] == pytest.approx(result.standing_joints[name])
        assert path[-1][name] == pytest.approx(
            result.analysis_stowed_joints[name]
        )
    for row in result.geometry_candidates:
        assert row.sampled_leg_sweep.sample_count == 101
        assert row.sampled_leg_sweep.proof_flag == TRANSITION_PROOF_FLAG


def test_worst_clearance_is_repeatable(config, result):
    second = evaluate_architecture(config)
    for left, right in zip(result.geometry_candidates, second.geometry_candidates):
        assert left.sampled_leg_sweep.min_clearance_m == (
            right.sampled_leg_sweep.min_clearance_m
        )
        assert left.sampled_leg_sweep.worst_sample_index == (
            right.sampled_leg_sweep.worst_sample_index
        )
        assert left.sampled_leg_sweep.worst_leg_segment == (
            right.sampled_leg_sweep.worst_leg_segment
        )
        assert left.sampled_leg_sweep.worst_rotor == (
            right.sampled_leg_sweep.worst_rotor
        )
        assert left.adjacent_rotor_tip_clearance_m == (
            right.adjacent_rotor_tip_clearance_m
        )


def test_g1_baseline_matches_xacro(config, result):
    assert result.baseline.consistent is True
    xacro = parse_xacro_numeric_properties(config.xacro_path)
    assert xacro['hex_arm_span'] == pytest.approx(0.30)
    assert config.g1_baseline_yaml['hex_arm_span_m'] == pytest.approx(0.30)
    assert config.g1_baseline_yaml['coxa_length_m'] == pytest.approx(
        xacro['coxa_length']
    )
    assert config.g1_baseline_yaml['body_length_m'] == pytest.approx(
        xacro['body_length']
    )
    assert config.g1_baseline_yaml['sensor_pod_size_x_m'] == pytest.approx(
        xacro['sensor_pod_size_x']
    )
    rotor_z = (
        0.5 * xacro['body_height']
        + xacro['hex_deck_offset']
        + xacro['hex_rotor_z_offset']
    )
    assert config.g1_baseline_yaml['rotor_plane_z_m'] == pytest.approx(rotor_z)


def test_g1_baseline_drift_is_rejected(tmp_path):
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['g1_baseline'].__setitem__('hex_arm_span_m', 0.31),
    )
    mutated = load_architecture_config(path)
    with pytest.raises(InvalidInputError, match='G1 baseline drift'):
        evaluate_architecture(mutated)


def test_unknown_mass_is_null_not_zero(result):
    assert len(result.mass_ledger_items) == len(REQUIRED_MASS_LEDGER_ITEMS)
    for item in result.mass_ledger_items:
        assert item.evidence_status == EVIDENCE_MISSING
        assert item.mass_kg is None
        assert item.mass_kg != 0


def test_missing_evidence_makes_ledger_incomplete(result):
    assert result.mass_ledger_status == MASS_LEDGER_INCOMPLETE
    assert any(
        item.evidence_status == EVIDENCE_MISSING
        for item in result.mass_ledger_items
    )


def test_incomplete_ledger_never_passes_or_procures(result):
    assert result.status == STATUS_ANALYSIS_ONLY
    assert result.procurement_allowed is False
    assert result.overall_architecture_feasibility == STATUS_OVERALL_UNDETERMINED
    assert result.mass_ledger_status == MASS_LEDGER_INCOMPLETE
    for row in result.joint_gate_rows:
        assert row.architecture_gate in ALLOWED_ARCHITECTURE_GATES
        assert row.architecture_gate not in FORBIDDEN_ARCHITECTURE_STATUS_WORDS
        assert row.architecture_gate != 'VIABLE'
        if (
            row.rotor_spacing_gate == GATE_CLEARANCE_MET
            and row.body_clearance_gate == GATE_CLEARANCE_MET
            and row.sensor_pod_clearance_gate == GATE_CLEARANCE_MET
            and row.sampled_leg_sweep_gate == GATE_CLEARANCE_MET
            and row.energy_mass_closure
        ):
            assert row.architecture_gate == ARCH_GATE_UNDETERMINED_MASS_LEDGER
        assert 'mass_ledger_incomplete' in row.rejection_reasons


def test_candidate_row_counts(config, result):
    n_d = len(config.propeller_diameters_in)
    n_r = len(config.motor_center_radii_m)
    assert n_d == 5
    assert n_r == 6
    assert 8.0 in config.propeller_diameters_in
    assert 10.0 in config.propeller_diameters_in
    for required in REQUIRED_INTERMEDIATE_DIAMETERS_IN:
        assert required in config.propeller_diameters_in
    assert len(result.geometry_candidates) == n_d * n_r
    assert len(result.joint_gate_rows) == 3 * 3 * n_d * n_r
    order_d = [row.diameter_inch for row in result.geometry_candidates]
    expected = [
        diameter
        for diameter in config.propeller_diameters_in
        for _radius in config.motor_center_radii_m
    ]
    assert order_d == expected


def test_three_uncertainty_cases_are_emitted(result):
    names = {row.uncertainty_case for row in result.joint_gate_rows}
    assert names == {'conservative', 'nominal', 'optimistic'}
    by_case = {
        name: [
            row for row in result.joint_gate_rows
            if row.uncertainty_case == name
        ]
        for name in ('conservative', 'nominal', 'optimistic')
    }
    for _name, rows in by_case.items():
        assert len(rows) == 90


def test_json_csv_markdown_status_agree(result, tmp_path):
    paths = write_architecture_reports(result, tmp_path)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    csv_rows = list(
        csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines())
    )
    md_text = paths['markdown'].read_text(encoding='utf-8')
    assert payload['status'] == STATUS_ANALYSIS_ONLY
    assert payload['procurement_allowed'] is False
    assert payload['overall_architecture_feasibility'] == (
        STATUS_OVERALL_UNDETERMINED
    )
    assert payload['mass_ledger_status'] == MASS_LEDGER_INCOMPLETE
    assert payload['not_for_procurement'] == STATUS_NOT_FOR_PROCUREMENT
    assert csv_rows
    for item in csv_rows:
        assert item['status'] == STATUS_ANALYSIS_ONLY
        assert item['procurement_allowed'] == 'false'
        assert item['overall_architecture_feasibility'] == (
            STATUS_OVERALL_UNDETERMINED
        )
        assert item['mass_ledger_status'] == MASS_LEDGER_INCOMPLETE
        assert item['architecture_gate'] in ALLOWED_ARCHITECTURE_GATES
    assert f'**{STATUS_ANALYSIS_ONLY}**' in md_text
    assert f'**{STATUS_NOT_FOR_PROCUREMENT}**' in md_text
    assert 'overall_architecture_feasibility: UNDETERMINED' in md_text
    assert 'mass_ledger_status: INCOMPLETE' in md_text
    assert TRANSITION_PROOF_FLAG in md_text
    for item in payload['mass_ledger']['items']:
        assert item['mass_kg'] is None
    for item in csv_rows:
        if item['energy_total_mass_kg'] == '':
            assert item['energy_battery_mass_kg'] == ''
    assert MD_NULL in md_text
    json_rows = payload['joint_gate_rows']
    assert len(json_rows) == len(csv_rows) == len(result.joint_gate_rows)
    for json_row, csv_row, model_row in zip(
        json_rows, csv_rows, result.joint_gate_rows
    ):
        assert json_row['architecture_gate'] == csv_row['architecture_gate']
        assert json_row['architecture_gate'] == model_row.architecture_gate
        assert json_row['energy_mass_closure_status'] == (
            csv_row['energy_mass_closure_status']
        )


def test_illegal_yaml_types_and_structure_rejected(tmp_path):
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['clearance'].__setitem__('min_tip_clearance_m', True),
    )
    with pytest.raises(InvalidInputError, match='clearance.min_tip_clearance_m'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw['leg_sweep'].__setitem__('sample_count', 101.5)
    )
    with pytest.raises(InvalidInputError, match='leg_sweep.sample_count'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw['leg_sweep'].__setitem__('sample_count', 0)
    )
    with pytest.raises(InvalidInputError, match='leg_sweep.sample_count'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw['propeller_diameters_in'].__setitem__(0, 0.0)
    )
    with pytest.raises(InvalidInputError, match='propeller_diameters_in'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw['propeller_diameters_in'].append(10.0)
    )
    with pytest.raises(InvalidInputError, match='duplicate propeller_diameters_in'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw['motor_center_radii_m'].append(0.30)
    )
    with pytest.raises(InvalidInputError, match='duplicate motor_center_radii_m'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path, lambda raw: raw.__setitem__('clearance', [0.02])
    )
    with pytest.raises(InvalidInputError, match='clearance must be a mapping'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['analysis_stowed']['joints'].__setitem__(
            'ghost_joint', 0.1
        ),
    )
    mutated = load_architecture_config(path)
    with pytest.raises(InvalidInputError, match='unknown joints'):
        evaluate_architecture(mutated)
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['mass_ledger']['items'][0].__setitem__('mass_kg', 0),
    )
    with pytest.raises(InvalidInputError, match='mass_kg must be null'):
        load_architecture_config(path)
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['propeller_diameters_in'].__setitem__(1, float('nan')),
    )
    with pytest.raises(InvalidInputError, match='finite'):
        load_architecture_config(path)


def test_all_candidates_have_certified_path_distances(config, result):
    n_d = len(config.propeller_diameters_in)
    n_r = len(config.motor_center_radii_m)
    assert n_d * n_r == 30
    assert config.sample_count == 101
    assert len(result.geometry_candidates) == 30
    solver = result.diagnostic['geometry_solver']
    assert solver['solver_method'] == 'best_first_lipschitz_subdivision'
    assert solver['solver_tolerance_m'] == GEOMETRY_SOLVER_TOLERANCE_M
    assert solver['convergence_status'] == CONVERGENCE_CERTIFIED
    assert solver['certified_error_bound_m'] <= solver['solver_tolerance_m']
    assert solver['evaluations_used'] >= 0
    assert solver['solves_certified'] >= 30 * 101
    for row in result.geometry_candidates:
        sweep = row.sampled_leg_sweep
        assert sweep.sample_count == 101
        assert math.isfinite(sweep.min_clearance_m)
        assert math.isfinite(sweep.start_clearance_m)
        assert math.isfinite(sweep.end_clearance_m)
        assert math.isfinite(row.zero_pose_leg_clearance_m)
    for row in result.joint_gate_rows:
        assert row.sampled_leg_sweep_gate in (
            GATE_CLEARANCE_MET,
            GATE_CLEARANCE_NOT_MET,
        )


def test_cli_geometry_nonconvergence_has_no_traceback(
    tmp_path, capsys, monkeypatch
):
    import arachne_hx6_analysis.geometry as geometry

    monkeypatch.setattr(geometry, 'GEOMETRY_SOLVER_MAX_EVALUATIONS', 1)
    monkeypatch.setattr(geometry, 'GEOMETRY_SOLVER_TOLERANCE_M', 1.0e-18)
    output_dir = tmp_path / 'cli_geom_fail'
    output_dir.mkdir()
    marker = output_dir / 'preexisting.txt'
    marker.write_text('keep', encoding='utf-8')
    rc = architecture_main(
        ['--config', str(_CONFIG_PATH), '--output-dir', str(output_dir)]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert captured.err.count('\n') == 1
    assert 'Traceback' not in captured.err
    assert 'Traceback' not in captured.out
    assert 'File "' not in captured.err
    assert 'CLEARANCE_MET' not in captured.out
    assert not (output_dir / JSON_NAME).exists()
    assert not (output_dir / CSV_NAME).exists()
    assert not (output_dir / MARKDOWN_NAME).exists()
    assert marker.read_text(encoding='utf-8') == 'keep'


def test_official_report_states_fail_closed_distance_rule(result, tmp_path):
    paths = write_architecture_reports(result, tmp_path)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    md_text = paths['markdown'].read_text(encoding='utf-8')
    capsule_eq = next(
        item for item in payload['equations']
        if item['name'] == 'disk_capsule_signed_gap'
    )
    assert 'upper_bound - lower_bound' in capsule_eq['equation']
    assert 'fail-closed' in capsule_eq['equation']
    assert 'upper_bound - lower_bound' in md_text
    assert 'fail-closed' in md_text
    solver = payload['diagnostic']['geometry_solver']
    assert solver['convergence_status'] == CONVERGENCE_CERTIFIED
    for row in payload['joint_gate_rows']:
        assert 'solver_method' not in row
        assert 'certified_error_bound_m' not in row


def test_cli_error_has_no_traceback_and_writes_no_report(tmp_path, capsys):
    config_path = _write_mutated_config(
        tmp_path, lambda raw: raw['leg_sweep'].__setitem__('sample_count', 0)
    )
    output_dir = tmp_path / 'cli_fail_out'
    rc = architecture_main(
        ['--config', str(config_path), '--output-dir', str(output_dir)]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert 'Traceback' not in captured.err
    assert 'Traceback' not in captured.out
    assert 'File "' not in captured.err
    assert not (output_dir / JSON_NAME).exists()
    assert not (output_dir / CSV_NAME).exists()
    assert not (output_dir / MARKDOWN_NAME).exists()


def test_forbidden_status_words_are_not_official_gates(result, tmp_path):
    for row in result.joint_gate_rows:
        assert row.architecture_gate in ALLOWED_ARCHITECTURE_GATES
        for word in FORBIDDEN_ARCHITECTURE_STATUS_WORDS:
            assert row.architecture_gate != word
    paths = write_architecture_reports(result, tmp_path)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    csv_rows = list(
        csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines())
    )
    official_gates = {
        row['architecture_gate'] for row in payload['joint_gate_rows']
    }
    official_gates.update(item['architecture_gate'] for item in csv_rows)
    for word in FORBIDDEN_ARCHITECTURE_STATUS_WORDS:
        assert word not in official_gates
    assert payload['overall_architecture_feasibility'] == (
        STATUS_OVERALL_UNDETERMINED
    )
    assert 'VIABLE' not in {
        payload['overall_architecture_feasibility'],
        payload['mass_ledger_status'],
        payload['status'],
    }


def test_cli_writes_three_artifacts(tmp_path):
    output_dir = tmp_path / 'cli_out'
    rc = architecture_main(
        ['--config', str(_CONFIG_PATH), '--output-dir', str(output_dir)]
    )
    assert rc == 0
    assert (output_dir / JSON_NAME).is_file()
    assert (output_dir / CSV_NAME).is_file()
    assert (output_dir / MARKDOWN_NAME).is_file()
    payload = json.loads((output_dir / JSON_NAME).read_text(encoding='utf-8'))
    assert payload['status'] == STATUS_ANALYSIS_ONLY
    assert payload['overall_architecture_feasibility'] == (
        STATUS_OVERALL_UNDETERMINED
    )


def test_make_rotor_disks_are_filled_and_evenly_spaced():
    disks = make_rotor_disks(0.30, 0.12, 0.068, 6, math.pi / 6.0)
    assert len(disks) == 6
    for disk in disks:
        assert disk.radius == pytest.approx(0.06)
        assert math.hypot(disk.center[0], disk.center[1]) == pytest.approx(0.30)
        assert disk.center[2] == pytest.approx(0.068)
    adjacent = math.hypot(
        disks[0].center[0] - disks[1].center[0],
        disks[0].center[1] - disks[1].center[1],
    )
    assert adjacent == pytest.approx(0.30)


def _walk_finite(value):
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        assert math.isfinite(value)
        return
    if isinstance(value, dict):
        for item in value.values():
            _walk_finite(item)
        return
    if isinstance(value, list):
        for item in value:
            _walk_finite(item)


def test_stow_pose_is_unqualified_analysis_pose(result):
    assert result.stow_pose_evidence_status == STOW_POSE_EVIDENCE_UNQUALIFIED
    assert result.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE
    assert result.stow_pose_is_hardware_validated is False
    req = result.config.stow_requirements.as_dict()
    assert set(req) == {
        'maximum_total_height_m',
        'maximum_leg_below_body_m',
        'maximum_planform_length_m',
        'maximum_planform_width_m',
    }
    assert all(value is None for value in req.values())
    for row in result.geometry_candidates:
        assert math.isfinite(row.standing_total_height_m)
        assert math.isfinite(row.analysis_pose_total_height_m)
        assert math.isfinite(row.height_reduction_m)
        assert math.isfinite(row.height_reduction_ratio)
        assert math.isfinite(row.standing_leg_below_body_m)
        assert math.isfinite(row.analysis_pose_leg_below_body_m)
        assert math.isfinite(row.standing_planform_length_m)
        assert math.isfinite(row.standing_planform_width_m)
        assert math.isfinite(row.analysis_pose_planform_length_m)
        assert math.isfinite(row.analysis_pose_planform_width_m)
        assert math.isfinite(row.rotor_plane_to_lowest_leg_point_m)
        assert row.height_reduction_ratio == pytest.approx(
            row.height_reduction_m / row.standing_total_height_m
        )
        assert row.standing_total_height_m > 0.0


def test_nominal_clearance_does_not_imply_robust_pass(result):
    assert result.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
    assert result.config.geometry_uncertainty_allowance_m is None
    for row in result.geometry_candidates:
        for evidence in (
            row.rotor_spacing_evidence,
            row.body_clearance_evidence,
            row.sensor_pod_clearance_evidence,
            row.sampled_leg_evidence,
        ):
            assert evidence.geometry_uncertainty_allowance_m is None
            assert evidence.robust_clearance_margin_m is None
            assert evidence.robust_gate == ROBUST_GATE_UNQUANTIFIED
            assert evidence.nominal_clearance_margin_m == pytest.approx(
                evidence.nominal_clearance_m - evidence.required_clearance_m
            )
            if evidence.nominal_gate == GATE_CLEARANCE_MET:
                assert evidence.robust_gate != GATE_CLEARANCE_MET
        assert row.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
        assert row.nominal_geometry_status in (
            NOMINAL_GEOMETRY_MET,
            NOMINAL_GEOMETRY_NOT_MET,
        )


def test_arm_radius_mass_coupling_statuses(result):
    for row in result.geometry_candidates:
        if abs(row.motor_center_radius_m - 0.30) <= 1.0e-12:
            assert row.arm_radius_mass_coupling_status == ARM_COUPLING_BASELINE
            assert ARM_EXTENSION_LIMITATION_REASON not in row.limitation_reasons
        else:
            assert row.arm_radius_mass_coupling_status == ARM_COUPLING_UNMODELED
            assert ARM_EXTENSION_LIMITATION_REASON in row.limitation_reasons
    for row in result.joint_gate_rows:
        if abs(row.motor_center_radius_m - 0.30) > 1.0e-12:
            assert row.arm_radius_mass_coupling_status == ARM_COUPLING_UNMODELED
            assert ARM_EXTENSION_LIMITATION_REASON in row.limitation_reasons
            if (
                row.nominal_geometry_status == NOMINAL_GEOMETRY_MET
                and row.energy_mass_closure
            ):
                assert row.architecture_gate in (
                    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
                    'UNDETERMINED_MODEL_LIMITATION',
                )
                assert row.architecture_gate != 'VIABLE'


def test_joint_rows_keep_separate_unknowns(result):
    assert result.mass_ledger_status == MASS_LEDGER_INCOMPLETE
    assert result.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE
    assert result.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
    assert result.overall_architecture_feasibility == STATUS_OVERALL_UNDETERMINED
    for row in result.joint_gate_rows:
        assert row.nominal_geometry_status in (
            NOMINAL_GEOMETRY_MET,
            NOMINAL_GEOMETRY_NOT_MET,
        )
        assert row.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
        assert row.mass_ledger_status == MASS_LEDGER_INCOMPLETE
        assert row.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE
        assert row.arm_radius_mass_coupling_status in (
            ARM_COUPLING_BASELINE,
            ARM_COUPLING_UNMODELED,
        )
        assert row.architecture_gate in ALLOWED_ARCHITECTURE_GATES


def test_rotor_plane_height_derived_formula(config):
    xacro = parse_xacro_numeric_properties(config.xacro_path)
    expected = (
        0.5 * xacro['body_height']
        + xacro['hex_deck_offset']
        + xacro['hex_rotor_z_offset']
    )
    assert expected == pytest.approx(0.068)
    assert config.g1_baseline_yaml['rotor_plane_z_m'] == pytest.approx(expected)
    baseline = _g1_baseline_from_xacro(xacro)
    assert baseline.rotor_plane_z_m == pytest.approx(expected)


def test_xacro_missing_property_fails(tmp_path, config):
    text = config.xacro_path.read_text(encoding='utf-8')
    text = text.replace(
        '<xacro:property name="coxa_length" value="0.060"/>',
        '',
        1,
    )
    path = tmp_path / 'missing.xacro'
    path.write_text(text, encoding='utf-8')
    parsed = parse_xacro_numeric_properties(path)
    with pytest.raises(InvalidInputError, match='xacro missing properties'):
        _g1_baseline_from_xacro(parsed)


def test_xacro_duplicate_property_fails(tmp_path, config):
    text = config.xacro_path.read_text(encoding='utf-8')
    text = text.replace(
        '<xacro:property name="hex_arm_span" value="0.30"/>',
        '<xacro:property name="hex_arm_span" value="0.30"/>\n'
        '  <xacro:property name="hex_arm_span" value="0.31"/>',
        1,
    )
    path = tmp_path / 'dup.xacro'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(InvalidInputError, match='duplicate xacro property'):
        parse_xacro_numeric_properties(path)


def test_xacro_unparseable_expression_fails(tmp_path):
    path = tmp_path / 'bad.xacro'
    path.write_text(
        '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">\n'
        '  <xacro:property name="hex_arm_span" value="0.30"/>\n'
        '  <xacro:property name="broken" value="${no_such_symbol + 1}"/>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    with pytest.raises(InvalidInputError, match='unresolved'):
        parse_xacro_numeric_properties(path)
    path.write_text(
        '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">\n'
        '  <xacro:property name="hex_arm_span" value="not_a_number"/>\n'
        '</robot>\n',
        encoding='utf-8',
    )
    with pytest.raises(InvalidInputError, match='not numeric'):
        parse_xacro_numeric_properties(path)


def test_json_rejects_nan_and_infinity():
    with pytest.raises(InvalidInputError, match='finite'):
        assert_strict_finite_json({'gap': float('nan')})
    with pytest.raises(InvalidInputError, match='finite'):
        assert_strict_finite_json({'gap': float('inf')})


def test_reports_are_finite_and_cross_consistent(result, tmp_path):
    stamp = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    first = write_architecture_reports(result, tmp_path / 'a', generated_at=stamp)
    second = write_architecture_reports(result, tmp_path / 'b', generated_at=stamp)
    json_a = first['json'].read_bytes()
    json_b = second['json'].read_bytes()
    csv_a = first['csv'].read_bytes()
    csv_b = second['csv'].read_bytes()
    md_a = first['markdown'].read_bytes()
    md_b = second['markdown'].read_bytes()
    assert json_a == json_b
    assert csv_a == csv_b
    assert md_a == md_b
    payload = json.loads(json_a.decode('utf-8'))
    _walk_finite(payload)
    assert 'NaN' not in json_a.decode('utf-8')
    assert 'Infinity' not in json_a.decode('utf-8')
    csv_rows = list(csv.DictReader(csv_a.decode('utf-8').splitlines()))
    md_text = md_a.decode('utf-8')
    assert 'UNQUALIFIED_ANALYSIS_POSE' in md_text
    assert 'INCOMPLETE' in md_text
    assert payload['mass_ledger_status'] == MASS_LEDGER_INCOMPLETE
    assert payload['stow_requirements_status'] == STOW_REQUIREMENTS_INCOMPLETE
    assert payload['robust_geometry_status'] == ROBUST_GEOMETRY_UNDETERMINED
    assert payload['overall_architecture_feasibility'] == STATUS_OVERALL_UNDETERMINED
    assert payload['stow_pose_evidence_status'] == STOW_POSE_EVIDENCE_UNQUALIFIED
    assert payload['stow_pose_is_hardware_validated'] is False
    assert len(payload['geometry_candidates']) == len(result.geometry_candidates)
    assert len(payload['joint_gate_rows']) == len(result.joint_gate_rows)
    assert len(csv_rows) == len(result.joint_gate_rows)
    for json_row, csv_row, model_row in zip(
        payload['joint_gate_rows'], csv_rows, result.joint_gate_rows
    ):
        assert json_row['architecture_gate'] == csv_row['architecture_gate']
        assert json_row['architecture_gate'] == model_row.architecture_gate
        assert json_row['nominal_geometry_status'] == (
            csv_row['nominal_geometry_status']
        )
        assert json_row['robust_geometry_status'] == (
            csv_row['robust_geometry_status']
        )
        assert json_row['stow_requirements_status'] == (
            csv_row['stow_requirements_status']
        )
        assert json_row['arm_radius_mass_coupling_status'] == (
            csv_row['arm_radius_mass_coupling_status']
        )
    for word in FORBIDDEN_ARCHITECTURE_STATUS_WORDS:
        assert payload['overall_architecture_feasibility'] != word
        assert payload['status'] != word
        assert payload['mass_ledger_status'] != word
        assert payload['stow_requirements_status'] != word
        assert payload['stow_pose_evidence_status'] != word
        assert payload['robust_geometry_status'] != word
        assert word not in {
            row['architecture_gate'] for row in payload['joint_gate_rows']
        }
        assert word not in {
            row['nominal_geometry_status'] for row in payload['joint_gate_rows']
        }


def test_failed_write_does_not_leave_partial_reports(tmp_path):
    output_dir = tmp_path / 'partial'
    output_dir.mkdir()
    with pytest.raises(InvalidInputError):
        assert_strict_finite_json({'x': float('nan')})
    assert not (output_dir / JSON_NAME).exists()
    assert not (output_dir / CSV_NAME).exists()
    assert not (output_dir / MARKDOWN_NAME).exists()


def test_geometry_uncertainty_key_required(tmp_path):
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['clearance'].pop('geometry_uncertainty_allowance_m'),
    )
    with pytest.raises(InvalidInputError, match='geometry_uncertainty_allowance_m'):
        load_architecture_config(path)


def test_stow_requirements_invented_number_not_needed(tmp_path):
    path = _write_mutated_config(
        tmp_path,
        lambda raw: raw['stow_requirements'].__setitem__(
            'maximum_total_height_m', 0.005
        ),
    )
    loaded = load_architecture_config(path)
    assert loaded.stow_requirements.maximum_total_height_m == pytest.approx(0.005)
    assert loaded.stow_requirements.status() == STOW_REQUIREMENTS_INCOMPLETE
