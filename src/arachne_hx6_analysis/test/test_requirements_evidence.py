"""G3 requirements, evidence-ledger, and uncertainty-gate tests. No GUI."""

from __future__ import annotations

import csv
import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from arachne_hx6_analysis.architecture import evaluate_architecture, load_architecture_config
from arachne_hx6_analysis.architecture_types import REQUIRED_MASS_LEDGER_ITEMS
from arachne_hx6_analysis.geometry import CONVERGENCE_CERTIFIED, GEOMETRY_SOLVER_TOLERANCE_M
from arachne_hx6_analysis.model import InvalidInputError, STATUS_ANALYSIS_ONLY
from arachne_hx6_analysis.requirements import (
    evaluate_requirements,
    load_requirements_config,
)
from arachne_hx6_analysis.requirements_cli import main as requirements_main
from arachne_hx6_analysis.requirements_report import (
    CSV_NAME,
    JSON_NAME,
    MARKDOWN_NAME,
    REPORT_NAMES,
    write_requirements_reports,
)
from arachne_hx6_analysis.requirements_report_markdown import MD_NULL
from arachne_hx6_analysis.requirements_types import (
    ARM_COUPLING_UNDETERMINED,
    BLOCK_REASON_INCOMPLETE_SPECIFICATION,
    BLOCK_REASON_MISSING_EVIDENCE,
    BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE,
    BLOCK_REASON_NOT_SATISFIED,
    BLOCK_REASON_NO_REQUIRED_EVIDENCE,
    BLOCK_REASON_PLANNING_ASSUMPTION_ONLY,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    FORBIDDEN_G3_STATUS_WORDS,
    GATE_EVIDENCE_COMPLETE_NEXT,
    GATE_UNDETERMINED_EVIDENCE,
    GATE_UNDETERMINED_REQUIREMENTS,
    TRACE_CONSISTENT,
    GEOMETRY_BUDGET_INCOMPLETE,
    G2_MASS_COMPONENT_IDS,
    HARDWARE_SUFFICIENT_LEVELS,
    MASS_LEDGER_INCOMPLETE,
    REQUIREMENT_INCOMPLETE,
    REQUIREMENT_SPECIFIED,
    REQUIRED_UNCERTAINTY_SOURCES,
    ROBUST_GEOMETRY_UNDETERMINED,
    STOW_GATE_UNDETERMINED,
    STOW_HARDWARE_NOT_PERFORMED,
    STOW_POSE_EVIDENCE_UNQUALIFIED,
    STOW_REQUIREMENTS_INCOMPLETE,
)
from arachne_hx6_analysis.uncertainty_budget import combine_allowances

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_REQ_PATH = _PACKAGE_ROOT / 'config' / 'system_requirements.yaml'
_EV_PATH = _PACKAGE_ROOT / 'config' / 'evidence_ledger.yaml'
_UN_PATH = _PACKAGE_ROOT / 'config' / 'geometry_uncertainty_budget.yaml'
_ST_PATH = _PACKAGE_ROOT / 'config' / 'stow_requirements.yaml'
_ARCH_PATH = _PACKAGE_ROOT / 'config' / 'architecture_envelope.yaml'

# Closed-form: official topology quantities * 0.1 / 0.2 kg.
_QTY_SUM = 61
_MASS_LOWER = 0.1
_MASS_UPPER = 0.2
_EXPECTED_TOTAL_LOWER = _QTY_SUM * _MASS_LOWER  # 6.1
_EXPECTED_TOTAL_UPPER = _QTY_SUM * _MASS_UPPER  # 12.2

# Closed-form arm interval used by tests. Do not call the unit under test
# to produce these numbers.
_ARM_EXT = 0.10
_ARM_COUNT = 6
_ARM_LIN_LO, _ARM_LIN_HI = 1.0, 1.2
_ARM_CON_LO, _ARM_CON_HI = 0.05, 0.08
_ARM_WIR_LO, _ARM_WIR_HI = 0.2, 0.3
_ARM_RE_LO, _ARM_RE_HI = 0.10, 0.15
_EXPECTED_ARM_LOWER = _ARM_COUNT * (
    _ARM_EXT * _ARM_LIN_LO + _ARM_CON_LO + _ARM_EXT * _ARM_WIR_LO + _ARM_RE_LO
)  # 1.62
_EXPECTED_ARM_UPPER = _ARM_COUNT * (
    _ARM_EXT * _ARM_LIN_HI + _ARM_CON_HI + _ARM_EXT * _ARM_WIR_HI + _ARM_RE_HI
)  # 2.28

_GEO_ALLOWANCE = 0.001
_EXPECTED_LINEAR_SUM = 9 * _GEO_ALLOWANCE  # 0.009
_EXPECTED_RSS = math.sqrt(9 * (_GEO_ALLOWANCE ** 2))  # 0.003

# Official YAML category freeze. Production counts are derived from lists.
_OFFICIAL_CATEGORY_COUNTS = {
    'SYS-MASS': 4,
    'SYS-GEO': 4,
    'SYS-STOW': 11,
    'SYS-PROP': 5,
    'SYS-POWER': 3,
    'SYS-STRUCT': 6,
    'SYS-THERM': 1,
    'SYS-CTRL': 3,
    'SYS-SENSE': 3,
    'SYS-SAFE': 5,
    'SYS-TRACE': 3,
}
_OFFICIAL_REQUIREMENTS_TOTAL = 48
_OFFICIAL_INCOMPLETE_SPECIFICATION = 25


def _load_official_raw():
    return {
        'requirements': yaml.safe_load(_REQ_PATH.read_text(encoding='utf-8')),
        'evidence': yaml.safe_load(_EV_PATH.read_text(encoding='utf-8')),
        'uncertainty': yaml.safe_load(_UN_PATH.read_text(encoding='utf-8')),
        'stow': yaml.safe_load(_ST_PATH.read_text(encoding='utf-8')),
    }


def _write_bundle(tmp_path, raw, name='bundle'):
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        'requirements': root / 'system_requirements.yaml',
        'evidence': root / 'evidence_ledger.yaml',
        'uncertainty': root / 'geometry_uncertainty_budget.yaml',
        'stow': root / 'stow_requirements.yaml',
    }
    paths['requirements'].write_text(
        yaml.safe_dump(raw['requirements'], sort_keys=False), encoding='utf-8'
    )
    paths['evidence'].write_text(
        yaml.safe_dump(raw['evidence'], sort_keys=False), encoding='utf-8'
    )
    paths['uncertainty'].write_text(
        yaml.safe_dump(raw['uncertainty'], sort_keys=False), encoding='utf-8'
    )
    paths['stow'].write_text(
        yaml.safe_dump(raw['stow'], sort_keys=False), encoding='utf-8'
    )
    return paths


def _load_bundle(paths):
    return load_requirements_config(
        requirements_path=paths['requirements'],
        evidence_path=paths['evidence'],
        uncertainty_path=paths['uncertainty'],
        stow_path=paths['stow'],
    )


def _measured_fields(unit='kg'):
    return {
        'evidence_level': 'MEASURED',
        'status': 'MEASURED',
        'measurement_method': 'bench scale',
        'measurement_equipment': 'calibrated scale',
        'sample_count': 3,
        'measurement_time': '2026-01-01T00:00:00Z',
        'source': 'fixture laboratory',
        'source_date': '2026-01-01',
        'unit': unit,
    }


def _complete_synthetic_raw():
    raw = _load_official_raw()
    for req in raw['requirements']['requirements']:
        if req['kind'] == 'quantitative' and all(
            req[key] is None
            for key in ('threshold', 'value', 'range_lower', 'range_upper')
        ):
            req['threshold'] = 1.0
            if not req.get('unit'):
                req['unit'] = '1'
    for item in raw['evidence']['evidence']:
        unit = item.get('unit') or '1'
        item.update(_measured_fields(unit))
        item['lower'] = _MASS_LOWER if unit == 'kg' else 0.0
        item['upper'] = _MASS_UPPER if unit == 'kg' else 0.0
        item['value'] = item['lower']
    for item in raw['evidence']['mass_components']:
        item['mass_lower_kg'] = _MASS_LOWER
        item['mass_upper_kg'] = _MASS_UPPER
    raw['uncertainty']['combination_method'] = 'CONSERVATIVE_LINEAR_SUM'
    raw['uncertainty']['nominal_clearance_margin_m'] = 0.02
    for source in raw['uncertainty']['sources']:
        source['allowance_m'] = _GEO_ALLOWANCE
        source['lower_m'] = None
        source['upper_m'] = None
    arm = raw['uncertainty']['arm_radius_mass_coupling']
    arm['candidate_radius_m'] = 0.40
    arm['extension_length_per_arm_m'] = _ARM_EXT
    arm['linear_mass_lower_kg_per_m'] = _ARM_LIN_LO
    arm['linear_mass_upper_kg_per_m'] = _ARM_LIN_HI
    arm['connector_mass_lower_kg'] = _ARM_CON_LO
    arm['connector_mass_upper_kg'] = _ARM_CON_HI
    arm['wiring_mass_lower_kg_per_m'] = _ARM_WIR_LO
    arm['wiring_mass_upper_kg_per_m'] = _ARM_WIR_HI
    arm['reinforcement_mass_lower_kg'] = _ARM_RE_LO
    arm['reinforcement_mass_upper_kg'] = _ARM_RE_HI
    stow = raw['stow']
    stow['maximum_stowed_length_m'] = 1.0
    stow['maximum_stowed_width_m'] = 0.8
    stow['maximum_stowed_height_m'] = 0.5
    stow['minimum_rotor_to_leg_clearance_m'] = 0.02
    stow['maximum_transition_time_s'] = 10.0
    stow['actuator_torque_lower_nm'] = 1.0
    stow['actuator_torque_upper_nm'] = 2.0
    stow['lock_load_capacity_n'] = 100.0
    stow['lock_stiffness_nm_per_rad'] = 50.0
    stow['position_repeatability_rad'] = 0.01
    stow['power_loss_safe_state'] = 'hold_last_lock'
    stow['landing_deployment_condition'] = 'legs_deployed_before_touchdown'
    stow['flight_lock_verification_method'] = 'limit_switch_and_current'
    stow['emergency_recovery_requirement'] = 'manual_release'
    return raw


@pytest.fixture(scope='module')
def official_config():
    return load_requirements_config(_REQ_PATH, _EV_PATH, _UN_PATH, _ST_PATH)


@pytest.fixture(scope='module')
def official_result(official_config):
    return evaluate_requirements(official_config)


def test_official_ids_are_unique(official_config):
    ids = (
        [item.requirement_id for item in official_config.requirements]
        + [item.test_id for item in official_config.tests]
        + [item.evidence_id for item in official_config.evidence]
    )
    assert len(ids) == len(set(ids))
    assert len({item.component_id for item in official_config.mass_components}) == 19


def test_official_references_exist(official_config):
    evidence_ids = {item.evidence_id for item in official_config.evidence}
    test_ids = {item.test_id for item in official_config.tests}
    req_ids = {item.requirement_id for item in official_config.requirements}
    for req in official_config.requirements:
        assert set(req.required_evidence_ids) <= evidence_ids
        assert set(req.linked_test_ids) <= test_ids
    for item in official_config.evidence:
        assert set(item.linked_requirement_ids) <= req_ids


def test_duplicate_ids_rejected(tmp_path):
    raw = _load_official_raw()
    raw['requirements']['requirements'].append(
        deepcopy(raw['requirements']['requirements'][0])
    )
    paths = _write_bundle(tmp_path, raw, 'dup_req')
    with pytest.raises(InvalidInputError, match='duplicate requirement'):
        _load_bundle(paths)
    raw = _load_official_raw()
    raw['evidence']['evidence'].append(deepcopy(raw['evidence']['evidence'][0]))
    paths = _write_bundle(tmp_path, raw, 'dup_ev')
    with pytest.raises(InvalidInputError, match='duplicate evidence'):
        _load_bundle(paths)
    raw = _load_official_raw()
    raw['evidence']['mass_components'].append(
        deepcopy(raw['evidence']['mass_components'][0])
    )
    paths = _write_bundle(tmp_path, raw, 'dup_comp')
    with pytest.raises(InvalidInputError, match='duplicate component'):
        _load_bundle(paths)


def test_bool_cannot_be_numeric(tmp_path):
    raw = _load_official_raw()
    raw['evidence']['mass_components'][0]['quantity'] = True
    paths = _write_bundle(tmp_path, raw, 'bool_qty')
    with pytest.raises(InvalidInputError, match='quantity'):
        _load_bundle(paths)
    raw = _load_official_raw()
    raw['stow']['maximum_stowed_length_m'] = False
    paths = _write_bundle(tmp_path, raw, 'bool_stow')
    with pytest.raises(InvalidInputError, match='maximum_stowed_length_m'):
        _load_bundle(paths)


def test_nan_and_infinity_rejected(tmp_path):
    raw = _load_official_raw()
    raw['stow']['maximum_stowed_length_m'] = float('nan')
    paths = _write_bundle(tmp_path, raw, 'nan')
    with pytest.raises(InvalidInputError, match='finite'):
        _load_bundle(paths)
    raw = _load_official_raw()
    raw['stow']['maximum_stowed_width_m'] = float('inf')
    paths = _write_bundle(tmp_path, raw, 'inf')
    with pytest.raises(InvalidInputError, match='finite'):
        _load_bundle(paths)


def test_missing_mass_is_not_zero(official_result):
    assert official_result.mass.total_mass_lower_kg is None
    assert official_result.mass.total_mass_upper_kg is None
    assert official_result.mass.mass_ledger_status == MASS_LEDGER_INCOMPLETE
    assert official_result.mass.whole_vehicle_energy_mass_closure_claimed is False
    assert len(official_result.mass.missing_component_ids) == 19
    for item in official_result.mass.components:
        assert item.mass_lower_kg is None
        assert item.mass_upper_kg is None
        assert item.mass_lower_kg != 0
        assert item.evidence_level == EVIDENCE_MISSING


def test_complete_synthetic_mass_interval(tmp_path):
    raw = _complete_synthetic_raw()
    paths = _write_bundle(tmp_path, raw, 'mass_ok')
    result = evaluate_requirements(_load_bundle(paths))
    assert result.mass.total_mass_lower_kg == pytest.approx(_EXPECTED_TOTAL_LOWER)
    assert result.mass.total_mass_upper_kg == pytest.approx(_EXPECTED_TOTAL_UPPER)
    assert result.mass.total_mass_lower_kg == pytest.approx(6.1)
    assert result.mass.total_mass_upper_kg == pytest.approx(12.2)
    assert result.mass.missing_component_ids == ()
    assert tuple(item.component_id for item in result.mass.components) == (
        REQUIRED_MASS_LEDGER_ITEMS
    )


def test_lower_greater_than_upper_rejected(tmp_path):
    raw = _load_official_raw()
    raw['evidence']['mass_components'][0]['mass_lower_kg'] = 2.0
    raw['evidence']['mass_components'][0]['mass_upper_kg'] = 1.0
    paths = _write_bundle(tmp_path, raw, 'lo_gt_hi')
    with pytest.raises(InvalidInputError, match='must be <='):
        _load_bundle(paths)


def test_planning_assumption_cannot_close_hardware_gate(tmp_path):
    raw = _complete_synthetic_raw()
    for item in raw['evidence']['evidence']:
        item['evidence_level'] = EVIDENCE_PLANNING_ASSUMPTION
        item['status'] = EVIDENCE_PLANNING_ASSUMPTION
        item['measurement_method'] = None
        item['measurement_equipment'] = None
        item['sample_count'] = None
        item['measurement_time'] = None
    paths = _write_bundle(tmp_path, raw, 'planning')
    result = evaluate_requirements(_load_bundle(paths))
    assert result.mass.mass_ledger_status == MASS_LEDGER_INCOMPLETE
    assert result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT
    assert result.procurement_allowed is False
    assert result.traceability.requirements_specified == (
        result.traceability.requirements_total
    )
    assert result.traceability.requirements_incomplete_specification == 0
    assert result.traceability.requirements_verified == 0
    assert result.traceability.requirements_satisfied == 0
    assert result.traceability.verified_requirement_ids == ()
    assert result.traceability.satisfied_requirement_ids == ()
    assert result.traceability.sufficient_evidence_requirement_ids == ()
    planning_only = result.traceability.planning_assumption_only_requirement_ids
    assert planning_only == result.traceability.specified_requirement_ids
    assert set(result.traceability.evidence_blocked_requirement_ids) == set(
        result.traceability.specified_requirement_ids
    )
    assert set(result.traceability.all_blocking_requirement_ids) == {
        item.requirement_id for item in result.requirements if item.blocking
    }
    assert BLOCK_REASON_PLANNING_ASSUMPTION_ONLY in (
        result.traceability.blocking_reason_codes
    )


def test_incomplete_measured_metadata_rejected(tmp_path):
    raw = _load_official_raw()
    item = raw['evidence']['evidence'][0]
    item['evidence_level'] = 'MEASURED'
    item['status'] = 'MEASURED'
    item['lower'] = 1.0
    item['upper'] = 1.0
    item['unit'] = 'kg'
    paths = _write_bundle(tmp_path, raw, 'bad_measured')
    with pytest.raises(InvalidInputError, match='MEASURED'):
        _load_bundle(paths)


def test_geometry_missing_source_keeps_total_null(official_result):
    assert official_result.geometry_uncertainty_budget_status == (
        GEOMETRY_BUDGET_INCOMPLETE
    )
    assert official_result.uncertainty.total_geometry_uncertainty_allowance_m is None
    assert official_result.uncertainty.robust_clearance_margin_m is None
    assert official_result.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
    assert set(official_result.uncertainty.missing_source_ids) == set(
        REQUIRED_UNCERTAINTY_SOURCES
    )


def test_nominal_clearance_is_not_robust_pass(tmp_path):
    raw = _complete_synthetic_raw()
    paths = _write_bundle(tmp_path, raw, 'robust')
    result = evaluate_requirements(_load_bundle(paths))
    assert result.uncertainty.total_geometry_uncertainty_allowance_m == pytest.approx(
        _EXPECTED_LINEAR_SUM
    )
    assert result.uncertainty.robust_clearance_margin_m == pytest.approx(0.011)
    assert result.robust_geometry_status == ROBUST_GEOMETRY_UNDETERMINED
    text = json.dumps(result.robust_geometry_status)
    assert 'ROBUST_CLEARANCE_MET' not in text
    assert 'CLEARANCE_MET' not in result.robust_geometry_status


def test_stow_missing_requirements_cannot_pass(official_result):
    assert official_result.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE
    assert official_result.stow.stow_pose_evidence_status == (
        STOW_POSE_EVIDENCE_UNQUALIFIED
    )
    assert official_result.stow.stow_hardware_validation_status == (
        STOW_HARDWARE_NOT_PERFORMED
    )
    assert official_result.stow.stow_gate == STOW_GATE_UNDETERMINED
    assert official_result.stow.stow_gate != 'STOWED_PASS'


def test_arm_extension_missing_evidence_is_null(official_result):
    assert official_result.arm_radius_mass_coupling_status == ARM_COUPLING_UNDETERMINED
    assert official_result.arm_coupling.arm_extension_mass_lower_kg is None
    assert official_result.arm_coupling.arm_extension_mass_upper_kg is None


def test_complete_synthetic_arm_interval(tmp_path):
    raw = _complete_synthetic_raw()
    paths = _write_bundle(tmp_path, raw, 'arm_ok')
    result = evaluate_requirements(_load_bundle(paths))
    assert result.arm_coupling.arm_extension_mass_lower_kg == pytest.approx(
        _EXPECTED_ARM_LOWER
    )
    assert result.arm_coupling.arm_extension_mass_upper_kg == pytest.approx(
        _EXPECTED_ARM_UPPER
    )
    assert result.arm_coupling.arm_extension_mass_lower_kg == pytest.approx(1.62)
    assert result.arm_coupling.arm_extension_mass_upper_kg == pytest.approx(2.28)


def test_broken_traceability_reference_rejected(tmp_path):
    raw = _load_official_raw()
    raw['requirements']['requirements'][0]['required_evidence_ids'].append(
        'EV-DOES-NOT-EXIST'
    )
    paths = _write_bundle(tmp_path, raw, 'broken')
    with pytest.raises(InvalidInputError, match='broken traceability'):
        evaluate_requirements(_load_bundle(paths))


def test_orphan_evidence_is_reported(tmp_path):
    raw = _load_official_raw()
    raw['evidence']['evidence'].append(
        {
            'evidence_id': 'EV-ORPHAN-001',
            'component_id': 'analysis_process',
            'parameter': 'orphan',
            'evidence_level': 'MISSING',
            'value': None,
            'lower': None,
            'upper': None,
            'unit': None,
            'source': None,
            'source_date': None,
            'measurement_method': None,
            'sample_count': None,
            'uncertainty': None,
            'linked_requirement_ids': [],
            'status': 'MISSING',
            'notes': 'Intentionally unlinked from required_evidence_ids.',
        }
    )
    paths = _write_bundle(tmp_path, raw, 'orphan')
    result = evaluate_requirements(_load_bundle(paths))
    assert 'EV-ORPHAN-001' in result.traceability.orphan_evidence_ids


def test_blocking_requirement_without_evidence_is_blocker(official_result):
    assert official_result.traceability.blocker_ids
    assert 'SYS-MASS-002' in official_result.traceability.blocker_ids
    assert official_result.traceability.incomplete_blocking_requirement_ids
    assert 'SYS-MASS-002' in official_result.traceability.incomplete_blocking_requirement_ids


def test_cli_illegal_input_exits_1_without_partial_report(tmp_path, capsys):
    raw = _load_official_raw()
    raw['stow']['maximum_stowed_length_m'] = True
    paths = _write_bundle(tmp_path, raw, 'cli_bad')
    output_dir = tmp_path / 'cli_fail_out'
    rc = requirements_main(
        [
            '--requirements-config', str(paths['requirements']),
            '--evidence-config', str(paths['evidence']),
            '--uncertainty-config', str(paths['uncertainty']),
            '--stow-config', str(paths['stow']),
            '--output-dir', str(output_dir),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith('ERROR:')
    assert captured.err.count('\n') == 1
    assert 'Traceback' not in captured.err
    assert 'Traceback' not in captured.out
    assert 'File "' not in captured.err
    assert not (output_dir / JSON_NAME).exists()
    assert not (output_dir / CSV_NAME).exists()
    assert not (output_dir / MARKDOWN_NAME).exists()


def test_json_csv_markdown_status_agree(official_result, tmp_path):
    paths = write_requirements_reports(official_result, tmp_path)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    csv_rows = list(csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines()))
    md_text = paths['markdown'].read_text(encoding='utf-8')
    assert payload['status'] == STATUS_ANALYSIS_ONLY
    assert payload['procurement_allowed'] is False
    assert payload['overall_system_readiness'] == 'UNDETERMINED'
    assert payload['readiness_gate'] == official_result.readiness_gate
    assert payload['mass_ledger_status'] == official_result.mass_ledger_status
    assert payload['total_mass_lower_kg'] is None
    assert payload['total_mass_upper_kg'] is None
    assert csv_rows
    for row in csv_rows:
        assert row['status'] == STATUS_ANALYSIS_ONLY
        assert row['procurement_allowed'] == 'false'
        assert row['overall_system_readiness'] == 'UNDETERMINED'
        assert row['mass_ledger_status'] == official_result.mass_ledger_status
        assert row['total_mass_lower_kg'] == ''
        assert row['total_mass_upper_kg'] == ''
    assert f'**{STATUS_ANALYSIS_ONLY}**' in md_text
    assert '**NOT_FOR_PROCUREMENT**' in md_text
    assert 'overall_system_readiness: UNDETERMINED' in md_text
    assert MD_NULL in md_text
    assert len(csv_rows) == len(payload['requirements']) == len(official_result.requirements)
    _assert_report_set_contract(official_result, payload, csv_rows, md_text)


def test_official_procurement_allowed_false(official_result):
    assert official_result.procurement_allowed is False
    assert official_result.status == STATUS_ANALYSIS_ONLY
    assert official_result.overall_system_readiness == 'UNDETERMINED'
    assert official_result.readiness_gate == GATE_UNDETERMINED_REQUIREMENTS
    assert official_result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT


def test_official_reports_forbid_status_words(official_result, tmp_path):
    paths = write_requirements_reports(official_result, tmp_path)
    blob = (
        paths['json'].read_text(encoding='utf-8')
        + paths['csv'].read_text(encoding='utf-8')
        + paths['markdown'].read_text(encoding='utf-8')
    )
    for word in FORBIDDEN_G3_STATUS_WORDS:
        assert word not in blob


def test_official_report_has_no_synthetic_fixture(official_result, tmp_path):
    paths = write_requirements_reports(official_result, tmp_path)
    blob = (
        paths['json'].read_text(encoding='utf-8')
        + paths['csv'].read_text(encoding='utf-8')
        + paths['markdown'].read_text(encoding='utf-8')
    ).lower()
    assert 'synthetic' not in blob
    assert 'fixture laboratory' not in blob


def test_g2_candidate_and_certified_solver_counts_unchanged():
    config = load_architecture_config(_ARCH_PATH)
    result = evaluate_architecture(config)
    assert len(result.geometry_candidates) == 30
    assert len(result.joint_gate_rows) == 270
    solver = result.diagnostic['geometry_solver']
    assert solver['solves_certified'] == 18151
    assert solver['evaluations_used'] == 17
    assert solver['certified_error_bound_m'] <= 1.0e-9
    assert solver['certified_error_bound_m'] <= GEOMETRY_SOLVER_TOLERANCE_M
    assert solver['convergence_status'] == CONVERGENCE_CERTIFIED
    gates = {row.architecture_gate for row in result.joint_gate_rows}
    assert gates == {
        'REJECTED_GEOMETRY',
        'REJECTED_ENERGY_CLOSURE',
        'UNDETERMINED_MASS_LEDGER',
    }


def test_rss_combination_closed_form():
    allowances = [_GEO_ALLOWANCE] * 9
    assert combine_allowances(allowances, 'RSS') == pytest.approx(_EXPECTED_RSS)
    assert combine_allowances(allowances, 'CONSERVATIVE_LINEAR_SUM') == pytest.approx(
        _EXPECTED_LINEAR_SUM
    )


def test_g2_mass_component_ids_reused(official_config):
    assert tuple(
        item.component_id for item in official_config.mass_components
    ) == G2_MASS_COMPONENT_IDS


def test_official_requirement_counts(official_result):
    by_cat = {}
    for item in official_result.requirements:
        by_cat[item.category] = by_cat.get(item.category, 0) + 1
    assert official_result.traceability.requirements_total == (
        _OFFICIAL_REQUIREMENTS_TOTAL
    )
    assert by_cat == _OFFICIAL_CATEGORY_COUNTS
    assert sum(by_cat.values()) == _OFFICIAL_REQUIREMENTS_TOTAL
    assert any(item.status == REQUIREMENT_INCOMPLETE for item in official_result.requirements)
    assert any(item.status == REQUIREMENT_SPECIFIED for item in official_result.requirements)


def test_complete_synthetic_reaches_next_analysis_only(tmp_path):
    raw = _complete_synthetic_raw()
    paths = _write_bundle(tmp_path, raw, 'complete')
    result = evaluate_requirements(_load_bundle(paths))
    assert result.readiness_gate == GATE_EVIDENCE_COMPLETE_NEXT
    assert result.procurement_allowed is False
    assert result.overall_system_readiness == 'UNDETERMINED'
    assert result.status == STATUS_ANALYSIS_ONLY
    assert result.traceability.requirements_incomplete_specification == 0
    assert result.traceability.requirements_specified == (
        result.traceability.requirements_total
    )
    assert result.traceability.requirements_specified == len(
        result.traceability.specified_requirement_ids
    )
    assert result.traceability.requirements_verified == len(
        result.traceability.verified_requirement_ids
    )
    assert result.traceability.requirements_verified >= 1
    assert result.traceability.requirements_satisfied == 0
    assert result.traceability.satisfied_requirement_ids == ()
    assert result.traceability.evidence_blocked_requirement_ids == ()
    assert result.traceability.incomplete_blocking_requirement_ids == ()
    assert result.traceability.all_blocking_requirement_ids == ()
    assert set(result.traceability.sufficient_evidence_requirement_ids) == set(
        result.traceability.specified_requirement_ids
    )
    assert set(result.traceability.unsatisfied_blocking_requirement_ids) == {
        item.requirement_id for item in result.requirements if item.blocking
    }
    assert result.traceability.blocking_reason_codes == (
        BLOCK_REASON_NOT_SATISFIED,
    )
    reports = write_requirements_reports(result, tmp_path / 'complete_out')
    blob = reports['json'].read_text(encoding='utf-8')
    for word in FORBIDDEN_G3_STATUS_WORDS:
        assert word not in blob


def test_report_stable_except_timestamp(official_result, tmp_path):
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = write_requirements_reports(
        official_result, tmp_path / 'a', generated_at=stamp
    )
    second = write_requirements_reports(
        official_result, tmp_path / 'b', generated_at=stamp
    )
    assert first['json'].read_text(encoding='utf-8') == second['json'].read_text(
        encoding='utf-8'
    )
    assert first['csv'].read_text(encoding='utf-8') == second['csv'].read_text(
        encoding='utf-8'
    )
    assert first['markdown'].read_text(encoding='utf-8') == second['markdown'].read_text(
        encoding='utf-8'
    )


def _independent_requirement_sets(result):
    evidence = {item.evidence_id: item for item in result.evidence}
    specified = tuple(
        sorted(
            item.requirement_id
            for item in result.requirements
            if item.status == REQUIREMENT_SPECIFIED
        )
    )
    incomplete = tuple(
        sorted(
            item.requirement_id
            for item in result.requirements
            if item.status == REQUIREMENT_INCOMPLETE
        )
    )
    incomplete_blocking = tuple(
        sorted(
            item.requirement_id
            for item in result.requirements
            if item.status == REQUIREMENT_INCOMPLETE and item.blocking
        )
    )
    missing_evidence = []
    planning_only = []
    mixed_insufficient = []
    sufficient = []
    no_required = []
    evidence_blocked = []
    reason_codes = set()
    reasons = []
    for item in result.requirements:
        if item.status == REQUIREMENT_INCOMPLETE:
            if item.blocking:
                reason_codes.add(BLOCK_REASON_INCOMPLETE_SPECIFICATION)
                reasons.append(
                    (item.requirement_id, BLOCK_REASON_INCOMPLETE_SPECIFICATION)
                )
            continue
        if item.status != REQUIREMENT_SPECIFIED:
            continue
        if not item.required_evidence_ids:
            reason = BLOCK_REASON_NO_REQUIRED_EVIDENCE
            no_required.append(item.requirement_id)
        else:
            levels = [
                evidence[evidence_id].evidence_level
                for evidence_id in item.required_evidence_ids
            ]
            sufficient_now = bool(levels) and all(
                level in HARDWARE_SUFFICIENT_LEVELS for level in levels
            )
            if sufficient_now:
                sufficient.append(item.requirement_id)
                reason = None
            elif all(level == EVIDENCE_MISSING for level in levels):
                reason = BLOCK_REASON_MISSING_EVIDENCE
                missing_evidence.append(item.requirement_id)
            elif all(
                level == EVIDENCE_PLANNING_ASSUMPTION for level in levels
            ):
                reason = BLOCK_REASON_PLANNING_ASSUMPTION_ONLY
                planning_only.append(item.requirement_id)
            else:
                reason = BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE
                mixed_insufficient.append(item.requirement_id)
        if item.blocking and reason is not None:
            evidence_blocked.append(item.requirement_id)
            reason_codes.add(reason)
            reasons.append((item.requirement_id, reason))
    verified = []
    for item in result.requirements:
        if item.status != REQUIREMENT_SPECIFIED or not item.required_evidence_ids:
            continue
        levels = [
            evidence[evidence_id].evidence_level
            for evidence_id in item.required_evidence_ids
        ]
        if any(
            level in (EVIDENCE_MISSING, EVIDENCE_PLANNING_ASSUMPTION)
            for level in levels
        ):
            continue
        if all(level in HARDWARE_SUFFICIENT_LEVELS for level in levels):
            verified.append(item.requirement_id)
    verified_ids = tuple(sorted(verified))
    unsatisfied_blocking = tuple(
        sorted(
            item.requirement_id
            for item in result.requirements
            if item.blocking
            and item.requirement_id in verified_ids
        )
    )
    for req_id in unsatisfied_blocking:
        reason_codes.add(BLOCK_REASON_NOT_SATISFIED)
        reasons.append((req_id, BLOCK_REASON_NOT_SATISFIED))
    nonblocking_unverified = tuple(
        sorted(
            item.requirement_id
            for item in result.requirements
            if not item.blocking and item.requirement_id not in verified_ids
        )
    )
    evidence_blocked_ids = tuple(sorted(set(evidence_blocked)))
    all_blocking = tuple(sorted(set(incomplete_blocking) | set(evidence_blocked_ids)))
    return {
        'specified': specified,
        'incomplete': incomplete,
        'incomplete_blocking': incomplete_blocking,
        'missing_evidence': tuple(sorted(set(missing_evidence))),
        'planning_assumption_only': tuple(sorted(set(planning_only))),
        'mixed_insufficient': tuple(sorted(set(mixed_insufficient))),
        'sufficient': tuple(sorted(set(sufficient))),
        'no_required_evidence': tuple(sorted(set(no_required))),
        'evidence_blocked': evidence_blocked_ids,
        'all_blocking': all_blocking,
        'nonblocking_unverified': nonblocking_unverified,
        'unsatisfied_blocking': unsatisfied_blocking,
        'reason_codes': tuple(sorted(reason_codes)),
        'blocking_requirement_reasons': tuple(sorted(reasons)),
        'verified': verified_ids,
        'satisfied': (),
    }


def _csv_flag_ids(rows, flag):
    return tuple(
        sorted(row['requirement_id'] for row in rows if row[flag] == 'true')
    )


def _assert_report_set_contract(result, payload, csv_rows, md_text):
    trace = result.traceability
    independent = _independent_requirement_sets(result)
    contract_keys = (
        'requirements_total',
        'requirements_specified',
        'requirements_incomplete_specification',
        'requirements_verified',
        'requirements_satisfied',
        'specified_requirement_ids',
        'incomplete_specification_requirement_ids',
        'verified_requirement_ids',
        'satisfied_requirement_ids',
        'missing_evidence_requirement_ids',
        'planning_assumption_only_requirement_ids',
        'mixed_insufficient_evidence_requirement_ids',
        'sufficient_evidence_requirement_ids',
        'evidence_blocked_requirement_ids',
        'incomplete_blocking_requirement_ids',
        'all_blocking_requirement_ids',
        'nonblocking_unverified_requirement_ids',
        'unsatisfied_blocking_requirement_ids',
        'blocking_reason_codes',
        'blocking_requirement_reasons',
    )
    for key in contract_keys:
        assert payload[key] == payload['traceability'][key]
    assert 'requirements_complete' not in payload
    assert 'requirements_incomplete' not in payload
    assert 'blocking_requirements_incomplete' not in payload
    assert 'requirements_complete' not in payload['traceability']
    assert 'requirements_incomplete' not in payload['traceability']
    assert 'blocking_requirements_incomplete' not in payload['traceability']
    assert '- requirements_complete:' not in md_text
    assert '- requirements_incomplete:' not in md_text
    assert '- blocking_requirements_incomplete:' not in md_text
    assert payload['requirements_total'] == trace.requirements_total
    assert payload['requirements_specified'] == len(trace.specified_requirement_ids)
    assert payload['requirements_incomplete_specification'] == len(
        trace.incomplete_specification_requirement_ids
    )
    assert payload['requirements_verified'] == len(trace.verified_requirement_ids)
    assert payload['requirements_satisfied'] == len(trace.satisfied_requirement_ids)
    assert payload['specified_requirement_ids'] == list(independent['specified'])
    assert payload['incomplete_specification_requirement_ids'] == list(
        independent['incomplete']
    )
    assert payload['verified_requirement_ids'] == list(independent['verified'])
    assert payload['satisfied_requirement_ids'] == list(independent['satisfied'])
    assert payload['missing_evidence_requirement_ids'] == list(
        independent['missing_evidence']
    )
    assert payload['planning_assumption_only_requirement_ids'] == list(
        independent['planning_assumption_only']
    )
    assert payload['mixed_insufficient_evidence_requirement_ids'] == list(
        independent['mixed_insufficient']
    )
    assert payload['sufficient_evidence_requirement_ids'] == list(
        independent['sufficient']
    )
    assert payload['evidence_blocked_requirement_ids'] == list(
        independent['evidence_blocked']
    )
    assert payload['incomplete_blocking_requirement_ids'] == list(
        independent['incomplete_blocking']
    )
    assert payload['all_blocking_requirement_ids'] == list(independent['all_blocking'])
    assert payload['nonblocking_unverified_requirement_ids'] == list(
        independent['nonblocking_unverified']
    )
    assert payload['unsatisfied_blocking_requirement_ids'] == list(
        independent['unsatisfied_blocking']
    )
    assert payload['blocking_reason_codes'] == list(independent['reason_codes'])
    assert payload['blocking_requirement_reasons'] == [
        {'requirement_id': req_id, 'reason_code': code}
        for req_id, code in independent['blocking_requirement_reasons']
    ]
    assert payload['blocker_ids'] == payload['all_blocking_requirement_ids']
    assert csv_rows
    for row in csv_rows:
        assert int(row['requirements_total']) == payload['requirements_total']
        assert int(row['requirements_specified']) == payload['requirements_specified']
        assert int(row['requirements_incomplete_specification']) == (
            payload['requirements_incomplete_specification']
        )
        assert int(row['requirements_verified']) == payload['requirements_verified']
        assert int(row['requirements_satisfied']) == payload['requirements_satisfied']
        assert row['blocking_reason_codes'] == ','.join(payload['blocking_reason_codes'])
    assert _csv_flag_ids(csv_rows, 'is_specified') == independent['specified']
    assert _csv_flag_ids(csv_rows, 'is_incomplete_specification') == independent['incomplete']
    assert _csv_flag_ids(csv_rows, 'is_verified') == independent['verified']
    assert _csv_flag_ids(csv_rows, 'is_satisfied') == independent['satisfied']
    assert _csv_flag_ids(csv_rows, 'is_missing_evidence') == independent[
        'missing_evidence'
    ]
    assert _csv_flag_ids(csv_rows, 'is_planning_assumption_only') == independent[
        'planning_assumption_only'
    ]
    assert _csv_flag_ids(csv_rows, 'is_mixed_insufficient_evidence') == independent[
        'mixed_insufficient'
    ]
    assert _csv_flag_ids(csv_rows, 'is_sufficient_evidence') == independent[
        'sufficient'
    ]
    assert _csv_flag_ids(csv_rows, 'is_evidence_blocked') == independent['evidence_blocked']
    assert _csv_flag_ids(csv_rows, 'is_incomplete_blocking') == independent['incomplete_blocking']
    assert _csv_flag_ids(csv_rows, 'is_all_blocking') == independent['all_blocking']
    assert _csv_flag_ids(csv_rows, 'is_nonblocking_unverified') == independent[
        'nonblocking_unverified'
    ]
    assert _csv_flag_ids(csv_rows, 'is_unsatisfied_blocking') == independent[
        'unsatisfied_blocking'
    ]
    csv_reasons = tuple(
        sorted(
            (row['requirement_id'], row['requirement_blocking_reason_code'])
            for row in csv_rows
            if row['requirement_blocking_reason_code']
        )
    )
    assert csv_reasons == independent['blocking_requirement_reasons']
    for req_id in independent['specified']:
        assert f'`{req_id}`' in md_text
    for req_id in independent['incomplete']:
        assert f'`{req_id}`' in md_text
    for req_id in independent['all_blocking']:
        assert f'`{req_id}`' in md_text
    assert f'requirements_total: {payload["requirements_total"]}' in md_text
    assert f'requirements_specified: {payload["requirements_specified"]}' in md_text
    assert (
        f'requirements_incomplete_specification: '
        f'{payload["requirements_incomplete_specification"]}'
    ) in md_text
    assert f'requirements_verified: {payload["requirements_verified"]}' in md_text
    assert f'requirements_satisfied: {payload["requirements_satisfied"]}' in md_text
    assert 'missing_evidence_requirement_ids:' in md_text
    assert 'planning_assumption_only_requirement_ids:' in md_text
    assert 'mixed_insufficient_evidence_requirement_ids:' in md_text
    assert 'sufficient_evidence_requirement_ids:' in md_text
    assert 'nonblocking_unverified_requirement_ids:' in md_text
    assert 'unsatisfied_blocking_requirement_ids:' in md_text


def test_official_requirement_set_semantics(official_result, tmp_path):
    trace = official_result.traceability
    independent = _independent_requirement_sets(official_result)
    req_by_id = {item.requirement_id: item for item in official_result.requirements}
    assert trace.requirements_total == _OFFICIAL_REQUIREMENTS_TOTAL
    assert trace.requirements_specified + trace.requirements_incomplete_specification == (
        trace.requirements_total
    )
    assert trace.requirements_specified == len(trace.specified_requirement_ids)
    assert trace.requirements_incomplete_specification == len(
        trace.incomplete_specification_requirement_ids
    )
    assert trace.requirements_verified == len(trace.verified_requirement_ids)
    assert trace.requirements_satisfied == len(trace.satisfied_requirement_ids)
    assert len(trace.incomplete_blocking_requirement_ids) == len(
        set(trace.incomplete_blocking_requirement_ids)
    )
    assert len(trace.evidence_blocked_requirement_ids) == len(
        set(trace.evidence_blocked_requirement_ids)
    )
    assert len(trace.all_blocking_requirement_ids) == len(set(trace.all_blocking_requirement_ids))
    assert len(trace.blocker_ids) == len(set(trace.blocker_ids))
    assert trace.specified_requirement_ids == independent['specified']
    assert trace.incomplete_specification_requirement_ids == independent['incomplete']
    assert trace.incomplete_blocking_requirement_ids == independent['incomplete_blocking']
    assert trace.evidence_blocked_requirement_ids == independent['evidence_blocked']
    assert trace.all_blocking_requirement_ids == independent['all_blocking']
    assert trace.blocker_ids == independent['all_blocking']
    assert trace.blocking_reason_codes == independent['reason_codes']
    assert trace.verified_requirement_ids == independent['verified']
    assert trace.satisfied_requirement_ids == independent['satisfied']
    assert set(trace.incomplete_blocking_requirement_ids) <= set(
        trace.incomplete_specification_requirement_ids
    )
    assert set(trace.evidence_blocked_requirement_ids) <= set(
        trace.specified_requirement_ids
    )
    assert set(trace.all_blocking_requirement_ids) == (
        set(trace.incomplete_blocking_requirement_ids)
        | set(trace.evidence_blocked_requirement_ids)
    )
    assert trace.requirements_incomplete_specification == (
        _OFFICIAL_INCOMPLETE_SPECIFICATION
    )
    assert trace.requirements_specified == (
        _OFFICIAL_REQUIREMENTS_TOTAL - _OFFICIAL_INCOMPLETE_SPECIFICATION
    )
    assert len(trace.incomplete_blocking_requirement_ids) == (
        _OFFICIAL_INCOMPLETE_SPECIFICATION
    )
    official_blocking_ids = tuple(
        sorted(
            item.requirement_id
            for item in official_result.requirements
            if item.blocking
        )
    )
    assert trace.all_blocking_requirement_ids == official_blocking_ids
    assert trace.missing_evidence_requirement_ids == independent['missing_evidence']
    assert trace.planning_assumption_only_requirement_ids == independent[
        'planning_assumption_only'
    ]
    assert trace.mixed_insufficient_evidence_requirement_ids == independent[
        'mixed_insufficient'
    ]
    assert trace.sufficient_evidence_requirement_ids == independent['sufficient']
    assert trace.nonblocking_unverified_requirement_ids == independent[
        'nonblocking_unverified'
    ]
    assert trace.unsatisfied_blocking_requirement_ids == independent[
        'unsatisfied_blocking'
    ]
    assert trace.blocking_requirement_reasons == independent[
        'blocking_requirement_reasons'
    ]
    assert trace.sufficient_evidence_requirement_ids == ()
    assert trace.nonblocking_unverified_requirement_ids == ()
    assert set(trace.evidence_blocked_requirement_ids) == set(
        independent['missing_evidence']
    ) | set(independent['planning_assumption_only']) | set(
        independent['mixed_insufficient']
    ) | set(independent['no_required_evidence'])
    blocking_unverified = [
        item
        for item in official_result.requirements
        if item.blocking and item.requirement_id not in trace.satisfied_requirement_ids
    ]
    reason_ids = {req_id for req_id, _code in trace.blocking_requirement_reasons}
    assert {item.requirement_id for item in blocking_unverified} == reason_ids
    excluded = [
        item.requirement_id
        for item in official_result.requirements
        if item.requirement_id not in trace.all_blocking_requirement_ids
    ]
    for req_id in excluded:
        assert req_by_id[req_id].blocking is False
    assert trace.requirements_verified == 0
    assert trace.requirements_satisfied == 0
    assert trace.verified_requirement_ids == ()
    assert trace.satisfied_requirement_ids == ()
    assert BLOCK_REASON_INCOMPLETE_SPECIFICATION in trace.blocking_reason_codes
    assert BLOCK_REASON_MISSING_EVIDENCE in trace.blocking_reason_codes
    assert BLOCK_REASON_PLANNING_ASSUMPTION_ONLY in trace.blocking_reason_codes
    assert BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE in trace.blocking_reason_codes
    for req_id in trace.all_blocking_requirement_ids:
        assert req_by_id[req_id].blocking is True
    for req_id in trace.specified_requirement_ids:
        assert req_by_id[req_id].status == REQUIREMENT_SPECIFIED
    for req_id in trace.incomplete_specification_requirement_ids:
        assert req_by_id[req_id].status == REQUIREMENT_INCOMPLETE
    hardware_levels = {
        item.evidence_level
        for item in official_result.evidence
        if item.evidence_level in HARDWARE_SUFFICIENT_LEVELS
    }
    assert hardware_levels == set()
    assert official_result.status == STATUS_ANALYSIS_ONLY
    assert official_result.procurement_allowed is False
    assert official_result.overall_system_readiness == 'UNDETERMINED'
    assert official_result.readiness_gate == GATE_UNDETERMINED_REQUIREMENTS
    paths = write_requirements_reports(official_result, tmp_path / 'set_semantics')
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    csv_rows = list(csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines()))
    md_text = paths['markdown'].read_text(encoding='utf-8')
    _assert_report_set_contract(official_result, payload, csv_rows, md_text)
    blob = (
        paths['json'].read_text(encoding='utf-8')
        + paths['csv'].read_text(encoding='utf-8')
        + paths['markdown'].read_text(encoding='utf-8')
    )
    for word in FORBIDDEN_G3_STATUS_WORDS:
        assert word not in blob


def test_sys_stow_011_is_mixed_insufficient_and_evidence_blocked(official_result):
    req_by_id = {item.requirement_id: item for item in official_result.requirements}
    evidence = {item.evidence_id: item for item in official_result.evidence}
    req = req_by_id['SYS-STOW-011']
    assert req.blocking is True
    assert req.status == REQUIREMENT_SPECIFIED
    assert req.kind == 'qualitative'
    levels = {
        evidence[evidence_id].evidence_level
        for evidence_id in req.required_evidence_ids
    }
    assert levels == {EVIDENCE_MISSING, EVIDENCE_PLANNING_ASSUMPTION}
    trace = official_result.traceability
    assert 'SYS-STOW-011' in trace.mixed_insufficient_evidence_requirement_ids
    assert 'SYS-STOW-011' in trace.evidence_blocked_requirement_ids
    assert 'SYS-STOW-011' in trace.all_blocking_requirement_ids
    assert 'SYS-STOW-011' not in trace.missing_evidence_requirement_ids
    assert 'SYS-STOW-011' not in trace.planning_assumption_only_requirement_ids
    assert 'SYS-STOW-011' not in trace.sufficient_evidence_requirement_ids
    assert 'SYS-STOW-011' not in trace.verified_requirement_ids
    assert 'SYS-STOW-011' not in trace.satisfied_requirement_ids
    reason_by_id = dict(trace.blocking_requirement_reasons)
    assert reason_by_id['SYS-STOW-011'] == BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE


def test_planning_assumption_only_is_evidence_blocked(official_result):
    trace = official_result.traceability
    assert trace.planning_assumption_only_requirement_ids
    for req_id in trace.planning_assumption_only_requirement_ids:
        assert req_id in trace.specified_requirement_ids
        assert req_id in trace.evidence_blocked_requirement_ids
        assert req_id in trace.all_blocking_requirement_ids
        assert req_id not in trace.verified_requirement_ids
        assert req_id not in trace.satisfied_requirement_ids
    reason_by_id = dict(trace.blocking_requirement_reasons)
    for req_id in trace.planning_assumption_only_requirement_ids:
        assert reason_by_id[req_id] == BLOCK_REASON_PLANNING_ASSUMPTION_ONLY


def test_g3_does_not_unlock_procurement(official_result):
    assert official_result.procurement_allowed is False
    assert official_result.status == STATUS_ANALYSIS_ONLY
    assert official_result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT
    req_by_id = {
        item.requirement_id: item for item in official_result.requirements
    }
    assert 'does not automatically allow procurement' in req_by_id[
        'SYS-SAFE-004'
    ].description
    assert 'must not connect directly' in req_by_id['SYS-SAFE-001'].description


def _req_by_id(raw, requirement_id):
    for item in raw['requirements']['requirements']:
        if item['requirement_id'] == requirement_id:
            return item
    raise AssertionError(requirement_id)


def _evidence_by_id(raw, evidence_id):
    for item in raw['evidence']['evidence']:
        if item['evidence_id'] == evidence_id:
            return item
    raise AssertionError(evidence_id)


def _test_by_id(raw, test_id):
    for item in raw['requirements']['tests']:
        if item['test_id'] == test_id:
            return item
    raise AssertionError(test_id)


def test_requirement_to_evidence_missing_reverse_link(tmp_path):
    raw = _load_official_raw()
    req = raw['requirements']['requirements'][0]
    evidence_id = req['required_evidence_ids'][0]
    item = _evidence_by_id(raw, evidence_id)
    item['linked_requirement_ids'] = [
        req_id
        for req_id in item['linked_requirement_ids']
        if req_id != req['requirement_id']
    ]
    paths = _write_bundle(tmp_path, raw, 'req_ev_reverse')
    with pytest.raises(InvalidInputError, match='inconsistent bidirectional'):
        evaluate_requirements(_load_bundle(paths))


def test_evidence_to_requirement_missing_forward_link(tmp_path):
    raw = _load_official_raw()
    item = raw['evidence']['evidence'][0]
    req_id = item['linked_requirement_ids'][0]
    req = _req_by_id(raw, req_id)
    req['required_evidence_ids'] = [
        evidence_id
        for evidence_id in req['required_evidence_ids']
        if evidence_id != item['evidence_id']
    ]
    paths = _write_bundle(tmp_path, raw, 'ev_req_forward')
    with pytest.raises(InvalidInputError, match='inconsistent bidirectional'):
        evaluate_requirements(_load_bundle(paths))


def test_requirement_to_test_missing_reverse_link(tmp_path):
    raw = _load_official_raw()
    req = next(
        item
        for item in raw['requirements']['requirements']
        if item['linked_test_ids']
    )
    test_id = req['linked_test_ids'][0]
    test = _test_by_id(raw, test_id)
    test['linked_requirement_ids'] = [
        req_id
        for req_id in test['linked_requirement_ids']
        if req_id != req['requirement_id']
    ]
    paths = _write_bundle(tmp_path, raw, 'req_test_reverse')
    with pytest.raises(InvalidInputError, match='inconsistent bidirectional'):
        evaluate_requirements(_load_bundle(paths))


def test_test_to_requirement_missing_forward_link(tmp_path):
    raw = _load_official_raw()
    test = raw['requirements']['tests'][0]
    req_id = test['linked_requirement_ids'][0]
    req = _req_by_id(raw, req_id)
    req['linked_test_ids'] = [
        test_id
        for test_id in req['linked_test_ids']
        if test_id != test['test_id']
    ]
    paths = _write_bundle(tmp_path, raw, 'test_req_forward')
    with pytest.raises(InvalidInputError, match='inconsistent bidirectional'):
        evaluate_requirements(_load_bundle(paths))


def test_orphan_evidence_blocks_next_analysis_gate(tmp_path):
    raw = _complete_synthetic_raw()
    orphan = {
        'evidence_id': 'EV-ORPHAN-GATE-001',
        'component_id': 'analysis_process',
        'parameter': 'orphan',
        'value': 1.0,
        'lower': 1.0,
        'upper': 1.0,
        'uncertainty': None,
        'linked_requirement_ids': [],
        'notes': 'Intentionally unlinked from required_evidence_ids.',
    }
    orphan.update(_measured_fields('1'))
    raw['evidence']['evidence'].append(orphan)
    paths = _write_bundle(tmp_path, raw, 'orphan_ev_gate')
    result = evaluate_requirements(_load_bundle(paths))
    assert 'EV-ORPHAN-GATE-001' in result.traceability.orphan_evidence_ids
    assert result.traceability.traceability_status != TRACE_CONSISTENT
    assert result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT
    assert result.readiness_gate == GATE_UNDETERMINED_EVIDENCE
    reasons = ' '.join(result.blocking_reasons)
    assert 'orphan_evidence:EV-ORPHAN-GATE-001' in reasons
    assert 'traceability_incomplete:' in reasons


def test_orphan_test_blocks_next_analysis_gate(tmp_path):
    raw = _complete_synthetic_raw()
    raw['requirements']['tests'].append(
        {
            'test_id': 'TEST-ORPHAN-GATE-001',
            'title': 'Orphan test',
            'method': 'none',
            'linked_requirement_ids': [],
            'status': 'NOT_PERFORMED',
            'notes': 'Intentionally unlinked from linked_test_ids.',
        }
    )
    paths = _write_bundle(tmp_path, raw, 'orphan_test_gate')
    result = evaluate_requirements(_load_bundle(paths))
    assert 'TEST-ORPHAN-GATE-001' in result.traceability.orphan_test_ids
    assert result.traceability.traceability_status != TRACE_CONSISTENT
    assert result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT
    assert result.readiness_gate == GATE_UNDETERMINED_EVIDENCE
    reasons = ' '.join(result.blocking_reasons)
    assert 'orphan_test:TEST-ORPHAN-GATE-001' in reasons
    assert 'traceability_incomplete:' in reasons


def test_official_yaml_bidirectional_links_consistent(official_config):
    evidence = {item.evidence_id: item for item in official_config.evidence}
    tests = {item.test_id: item for item in official_config.tests}
    requirements = {
        item.requirement_id: item for item in official_config.requirements
    }
    for req in official_config.requirements:
        for evidence_id in req.required_evidence_ids:
            assert req.requirement_id in evidence[evidence_id].linked_requirement_ids
        for test_id in req.linked_test_ids:
            assert req.requirement_id in tests[test_id].linked_requirement_ids
    for item in official_config.evidence:
        for req_id in item.linked_requirement_ids:
            assert item.evidence_id in requirements[req_id].required_evidence_ids
    for test in official_config.tests:
        for req_id in test.linked_requirement_ids:
            assert test.test_id in requirements[req_id].linked_test_ids
    result = evaluate_requirements(official_config)
    assert result.traceability.orphan_evidence_ids == ()
    assert result.traceability.orphan_test_ids == ()
    assert result.traceability.broken_reference_ids == ()


def _set_mass_020_level(raw, fields):
    item = _evidence_by_id(raw, 'EV-MASS-020')
    item.update(fields)
    return item


def test_vendor_declared_without_quantitative_value_rejected(tmp_path):
    raw = _load_official_raw()
    _set_mass_020_level(
        raw,
        {
            'evidence_level': 'VENDOR_DECLARED',
            'status': 'VENDOR_DECLARED',
            'vendor': 'Acme',
            'model': 'X1',
            'source': 'datasheet',
            'source_date': '2026-01-01',
            'value': None,
            'lower': None,
            'upper': None,
        },
    )
    paths = _write_bundle(tmp_path, raw, 'vendor_no_qty')
    with pytest.raises(InvalidInputError, match='quantitative requirement evidence'):
        _load_bundle(paths)


def test_measured_without_quantitative_value_rejected(tmp_path):
    raw = _load_official_raw()
    _set_mass_020_level(
        raw,
        {
            **_measured_fields('m'),
            'value': None,
            'lower': None,
            'upper': None,
        },
    )
    paths = _write_bundle(tmp_path, raw, 'measured_no_qty')
    with pytest.raises(InvalidInputError, match='quantitative requirement evidence'):
        _load_bundle(paths)


def test_test_validated_without_quantitative_value_rejected(tmp_path):
    raw = _load_official_raw()
    _set_mass_020_level(
        raw,
        {
            'evidence_level': 'TEST_VALIDATED',
            'status': 'TEST_VALIDATED',
            'test_id': 'TEST-MASS-002',
            'test_conditions': 'laboratory',
            'raw_result': 'recorded',
            'verdict': 'recorded',
            'source': 'test log',
            'value': None,
            'lower': None,
            'upper': None,
        },
    )
    paths = _write_bundle(tmp_path, raw, 'validated_no_qty')
    with pytest.raises(InvalidInputError, match='quantitative requirement evidence'):
        _load_bundle(paths)


def test_vendor_declared_finite_value_accepted(tmp_path):
    raw = _load_official_raw()
    _set_mass_020_level(
        raw,
        {
            'evidence_level': 'VENDOR_DECLARED',
            'status': 'VENDOR_DECLARED',
            'vendor': 'Acme',
            'model': 'X1',
            'source': 'datasheet',
            'source_date': '2026-01-01',
            'value': 0.01,
            'lower': None,
            'upper': None,
            'unit': 'm',
        },
    )
    result = evaluate_requirements(_load_bundle(_write_bundle(tmp_path, raw, 'vendor_value')))
    item = next(
        record for record in result.evidence if record.evidence_id == 'EV-MASS-020'
    )
    assert item.value == pytest.approx(0.01)
    assert item.unit == 'm'
    assert result.procurement_allowed is False


def test_vendor_declared_finite_interval_accepted(tmp_path):
    raw = _load_official_raw()
    _set_mass_020_level(
        raw,
        {
            'evidence_level': 'VENDOR_DECLARED',
            'status': 'VENDOR_DECLARED',
            'vendor': 'Acme',
            'model': 'X1',
            'source': 'datasheet',
            'source_date': '2026-01-01',
            'value': None,
            'lower': 0.0,
            'upper': 0.1,
            'unit': 'm',
        },
    )
    result = evaluate_requirements(_load_bundle(_write_bundle(tmp_path, raw, 'vendor_interval')))
    item = next(
        record for record in result.evidence if record.evidence_id == 'EV-MASS-020'
    )
    assert item.lower == pytest.approx(0.0)
    assert item.upper == pytest.approx(0.1)
    assert item.unit == 'm'


def test_qualitative_vendor_declared_without_numeric_content_accepted(tmp_path):
    raw = _load_official_raw()
    item = _evidence_by_id(raw, 'EV-PROC-002')
    item.update(
        {
            'evidence_level': 'VENDOR_DECLARED',
            'status': 'VENDOR_DECLARED',
            'vendor': 'Acme',
            'model': 'process-note',
            'source': 'charter',
            'source_date': '2026-01-01',
            'value': None,
            'lower': None,
            'upper': None,
            'unit': None,
        }
    )
    result = evaluate_requirements(_load_bundle(_write_bundle(tmp_path, raw, 'qual_vendor')))
    loaded = next(
        record for record in result.evidence if record.evidence_id == 'EV-PROC-002'
    )
    assert loaded.value is None
    assert loaded.lower is None
    assert loaded.upper is None
    assert result.readiness_gate != GATE_EVIDENCE_COMPLETE_NEXT


@pytest.mark.parametrize('blank', ['', '   '])
def test_empty_requirement_id_rejected(tmp_path, blank):
    raw = _load_official_raw()
    raw['requirements']['requirements'][0]['requirement_id'] = blank
    label = 'empty' if blank == '' else 'whitespace'
    paths = _write_bundle(tmp_path, raw, f'req_id_{label}')
    with pytest.raises(InvalidInputError, match='requirement_id'):
        _load_bundle(paths)


@pytest.mark.parametrize('blank', ['', '   '])
def test_empty_test_id_rejected(tmp_path, blank):
    raw = _load_official_raw()
    raw['requirements']['tests'][0]['test_id'] = blank
    label = 'empty' if blank == '' else 'whitespace'
    paths = _write_bundle(tmp_path, raw, f'test_id_{label}')
    with pytest.raises(InvalidInputError, match='test_id'):
        _load_bundle(paths)


@pytest.mark.parametrize('blank', ['', '   '])
def test_empty_evidence_id_rejected(tmp_path, blank):
    raw = _load_official_raw()
    raw['evidence']['evidence'][0]['evidence_id'] = blank
    label = 'empty' if blank == '' else 'whitespace'
    paths = _write_bundle(tmp_path, raw, f'ev_id_{label}')
    with pytest.raises(InvalidInputError, match='evidence_id'):
        _load_bundle(paths)


@pytest.mark.parametrize('blank', ['', '   '])
def test_empty_mass_component_id_rejected(tmp_path, blank):
    raw = _load_official_raw()
    raw['evidence']['mass_components'][0]['component_id'] = blank
    label = 'empty' if blank == '' else 'whitespace'
    paths = _write_bundle(tmp_path, raw, f'mass_id_{label}')
    with pytest.raises(InvalidInputError, match='component_id'):
        _load_bundle(paths)


@pytest.mark.parametrize('blank', ['', '   '])
def test_empty_uncertainty_source_id_rejected(tmp_path, blank):
    raw = _load_official_raw()
    raw['uncertainty']['sources'][0]['source_id'] = blank
    label = 'empty' if blank == '' else 'whitespace'
    paths = _write_bundle(tmp_path, raw, f'source_id_{label}')
    with pytest.raises(InvalidInputError, match='source_id'):
        _load_bundle(paths)


def _inject_replace_failure(monkeypatch, fail_on):
    real_replace = __import__('os').replace
    state = {'n': 0}

    def wrapper(src, dst):
        state['n'] += 1
        if state['n'] == fail_on:
            raise OSError(f'injected os.replace failure on call {fail_on}')
        return real_replace(src, dst)

    monkeypatch.setattr(
        'arachne_hx6_analysis.requirements_report.os.replace', wrapper
    )
    return state


def _report_bytes(directory):
    return {
        name: (directory / name).read_bytes() if (directory / name).exists() else None
        for name in REPORT_NAMES
    }


def _assert_no_g3_temp_dirs(directory):
    leftovers = [
        path
        for path in directory.iterdir()
        if path.name.startswith('.arachne_g3_')
    ]
    assert leftovers == []


def test_report_second_replace_fails_on_empty_dir(
    official_result, tmp_path, monkeypatch
):
    out = tmp_path / 'empty_second'
    out.mkdir()
    _inject_replace_failure(monkeypatch, 2)
    with pytest.raises(OSError, match='injected os.replace failure on call 2'):
        write_requirements_reports(official_result, out)
    for name in REPORT_NAMES:
        assert not (out / name).exists()
    _assert_no_g3_temp_dirs(out)


def test_report_third_replace_fails_on_empty_dir(
    official_result, tmp_path, monkeypatch
):
    out = tmp_path / 'empty_third'
    out.mkdir()
    _inject_replace_failure(monkeypatch, 3)
    with pytest.raises(OSError, match='injected os.replace failure on call 3'):
        write_requirements_reports(official_result, out)
    for name in REPORT_NAMES:
        assert not (out / name).exists()
    _assert_no_g3_temp_dirs(out)


def test_report_second_replace_fails_restores_previous(
    official_result, tmp_path, monkeypatch
):
    out = tmp_path / 'prev_second'
    old_stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_stamp = datetime(2026, 2, 1, tzinfo=timezone.utc)
    write_requirements_reports(official_result, out, generated_at=old_stamp)
    before = _report_bytes(out)
    assert all(payload is not None for payload in before.values())
    _inject_replace_failure(monkeypatch, 2)
    with pytest.raises(OSError, match='injected os.replace failure on call 2'):
        write_requirements_reports(official_result, out, generated_at=new_stamp)
    assert _report_bytes(out) == before
    _assert_no_g3_temp_dirs(out)


def test_report_third_replace_fails_restores_previous(
    official_result, tmp_path, monkeypatch
):
    out = tmp_path / 'prev_third'
    old_stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_stamp = datetime(2026, 2, 1, tzinfo=timezone.utc)
    write_requirements_reports(official_result, out, generated_at=old_stamp)
    before = _report_bytes(out)
    _inject_replace_failure(monkeypatch, 3)
    with pytest.raises(OSError, match='injected os.replace failure on call 3'):
        write_requirements_reports(official_result, out, generated_at=new_stamp)
    assert _report_bytes(out) == before
    _assert_no_g3_temp_dirs(out)


def test_report_success_trio_consistent_and_temps_cleaned(official_result, tmp_path):
    out = tmp_path / 'success_trio'
    stamp = datetime(2026, 3, 1, tzinfo=timezone.utc)
    paths = write_requirements_reports(official_result, out, generated_at=stamp)
    payload = json.loads(paths['json'].read_text(encoding='utf-8'))
    csv_rows = list(csv.DictReader(paths['csv'].read_text(encoding='utf-8').splitlines()))
    md_text = paths['markdown'].read_text(encoding='utf-8')
    _assert_report_set_contract(official_result, payload, csv_rows, md_text)
    assert payload['procurement_allowed'] is False
    assert payload['overall_system_readiness'] == 'UNDETERMINED'
    _assert_no_g3_temp_dirs(out)
