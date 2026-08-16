"""G2 parameterized architecture-envelope analysis.

Reuses G1.5 public energy-mass solvers. Does not copy propulsion formulas.
Does not modify G1 URDF, standing pose, or joint names.

This module is the public orchestration façade. Specialized work lives in
architecture_types, architecture_baseline, architecture_kinematics,
architecture_mass, architecture_candidates, and architecture_gates.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from arachne_hx6_analysis.architecture_baseline import (
    _compare_g1_baseline,
    _g1_baseline_from_xacro,
    load_standing_joints,
    parse_xacro_numeric_properties,
)
from arachne_hx6_analysis.architecture_candidates import _evaluate_geometry_candidate
from arachne_hx6_analysis.architecture_gates import (
    _combine_joint_gates,
    _solve_energy_matrix,
)
from arachne_hx6_analysis.architecture_kinematics import (
    _capsules_for_pose,
    interpolate_joint_path,
    validate_joint_pose,
)
from arachne_hx6_analysis.architecture_mass import (
    _mass_ledger_status,
    _parse_mass_ledger,
)
from arachne_hx6_analysis.architecture_types import (
    ALLOWED_ARCHITECTURE_GATES,
    ALLOWED_EVIDENCE_STATUS,
    ARCH_GATE_REJECTED_ENERGY_CLOSURE,
    ARCH_GATE_REJECTED_GEOMETRY,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARCH_GATE_UNDETERMINED_MODEL_LIMITATION,
    ARM_COUPLING_BASELINE,
    ARM_COUPLING_UNMODELED,
    ARM_EXTENSION_LIMITATION_REASON,
    BASELINE_MOTOR_CENTER_RADIUS_M,
    EVIDENCE_MEASURED,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_PLACEHOLDER,
    EVIDENCE_VENDOR_DECLARED,
    FORBIDDEN_ARCHITECTURE_STATUS_WORDS,
    G1_BASELINE_XACRO_KEYS,
    GATE_CLEARANCE_MET,
    GATE_CLEARANCE_NOT_MET,
    LEG_JOINT_SUFFIXES,
    LEG_PREFIXES,
    MASS_LEDGER_COMPLETE,
    MASS_LEDGER_INCOMPLETE,
    NOMINAL_GEOMETRY_MET,
    NOMINAL_GEOMETRY_NOT_MET,
    POSE_KIND_ANALYSIS_ONLY,
    REQUIRED_INTERMEDIATE_DIAMETERS_IN,
    REQUIRED_JOINT_NAMES,
    REQUIRED_MASS_LEDGER_ITEMS,
    REQUIRED_STOW_REQUIREMENT_KEYS,
    ROBUST_GATE_UNQUANTIFIED,
    ROBUST_GEOMETRY_UNDETERMINED,
    STOW_POSE_EVIDENCE_UNQUALIFIED,
    STOW_REQUIREMENTS_INCOMPLETE,
    TRANSITION_PROOF_FLAG,
    ArchitectureConfig,
    ArchitectureResult,
    BaselineCheck,
    ClearanceEvidence,
    G1Baseline,
    GeometryCandidate,
    JointGateRow,
    MassLedgerItem,
    StowRequirements,
    SweepResult,
)
from arachne_hx6_analysis.geometry import (
    box_from_center_size,
    capsule_aabb,
    collect_geometry_solver_diagnostics,
)
from arachne_hx6_analysis.inputs import (
    as_bool,
    as_float,
    as_int,
    as_list,
    as_mapping,
    as_optional_non_negative_float,
    as_str,
    optional_str,
    require_key,
)
from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    STATUS_OVERALL_UNDETERMINED,
    InvalidInputError,
    inches_to_metres,
)
from arachne_hx6_analysis.solver import load_analysis_config

def default_architecture_config_path() -> Path:
    """Installed share config, then source-tree fallback."""
    try:
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory('arachne_hx6_analysis'))
        candidate = share / 'config' / 'architecture_envelope.yaml'
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    return (
        Path(__file__).resolve().parent.parent
        / 'config'
        / 'architecture_envelope.yaml'
    )


def resolve_description_file(relpath: str) -> Path:
    """G1 description file from install share or the source tree."""
    try:
        from ament_index_python.packages import get_package_share_directory
        candidate = (
            Path(get_package_share_directory('arachne_hx6_description'))
            / relpath
        )
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    fallback = (
        Path(__file__).resolve().parents[2]
        / 'arachne_hx6_description'
        / relpath
    )
    if fallback.is_file():
        return fallback
    raise InvalidInputError(f'G1 description file not found: {relpath}')


def load_architecture_config(path: str | Path) -> ArchitectureConfig:
    """Parse architecture_envelope.yaml and validate it."""
    config_path = Path(path)
    if not config_path.is_file():
        raise InvalidInputError(f'config file not found: {config_path}')
    try:
        raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {config_path}: {exc}') from exc
    try:
        config = _parse_architecture_config(raw, config_path)
    except InvalidInputError:
        raise
    except KeyError as exc:
        raise InvalidInputError(f'config missing key: {exc}') from exc
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f'invalid config value: {exc}') from exc
    config.validate()
    return config



def evaluate_architecture(
    config: ArchitectureConfig,
) -> ArchitectureResult:
    """Run the offline architecture envelope. Never a procurement result."""
    config.validate()
    xacro_values = parse_xacro_numeric_properties(config.xacro_path)
    baseline_model = _g1_baseline_from_xacro(xacro_values)
    baseline_check = _compare_g1_baseline(config, baseline_model, xacro_values)
    if not baseline_check.consistent:
        drifted = [
            item['field']
            for item in baseline_check.comparisons
            if not item['match']
        ]
        raise InvalidInputError(
            'G1 baseline drift between YAML and Xacro/URDF: ' + ', '.join(drifted)
        )
    standing = validate_joint_pose(
        load_standing_joints(config.standing_pose_path),
        baseline_model.joint_limits,
        'standing_pose',
    )
    stowed = validate_joint_pose(
        config.analysis_stowed_joints,
        baseline_model.joint_limits,
        'analysis_stowed.joints',
    )
    zero_pose = {name: 0.0 for name in REQUIRED_JOINT_NAMES}
    validate_joint_pose(zero_pose, baseline_model.joint_limits, 'zero_pose')
    path_poses = interpolate_joint_path(standing, stowed, config.sample_count)
    path_capsules = tuple(
        _capsules_for_pose(pose, baseline_model) for pose in path_poses
    )
    path_capsule_boxes = tuple(
        tuple(capsule_aabb(capsule) for capsule in capsules)
        for capsules in path_capsules
    )
    zero_capsules = _capsules_for_pose(zero_pose, baseline_model)
    standing_capsules = path_capsules[0]
    stowed_capsules = path_capsules[-1]
    body_box = box_from_center_size(
        (0.0, 0.0, 0.0),
        (
            baseline_model.body_length_m,
            baseline_model.body_width_m,
            baseline_model.body_height_m,
        ),
    )
    left_pod = box_from_center_size(
        (0.0, baseline_model.sensor_pod_y_m, baseline_model.sensor_pod_z_m),
        (
            baseline_model.sensor_pod_size_x_m,
            baseline_model.sensor_pod_size_y_m,
            baseline_model.sensor_pod_size_z_m,
        ),
    )
    right_pod = box_from_center_size(
        (0.0, -baseline_model.sensor_pod_y_m, baseline_model.sensor_pod_z_m),
        (
            baseline_model.sensor_pod_size_x_m,
            baseline_model.sensor_pod_size_y_m,
            baseline_model.sensor_pod_size_z_m,
        ),
    )
    camera_box = box_from_center_size(
        (baseline_model.camera_x_m, 0.0, baseline_model.camera_z_m),
        (
            baseline_model.camera_size_x_m,
            baseline_model.camera_size_y_m,
            baseline_model.camera_size_z_m,
        ),
    )
    propulsion = load_analysis_config(config.propulsion_config_path)
    energy = _solve_energy_matrix(propulsion, config.propeller_diameters_in)
    geometry_rows = []
    with collect_geometry_solver_diagnostics() as geometry_solver:
        for diameter_inch in config.propeller_diameters_in:
            diameter_m = inches_to_metres(diameter_inch)
            for radius_m in config.motor_center_radii_m:
                geometry_rows.append(
                    _evaluate_geometry_candidate(
                        config,
                        baseline_model,
                        diameter_inch,
                        diameter_m,
                        radius_m,
                        body_box,
                        left_pod,
                        right_pod,
                        camera_box,
                        path_capsules,
                        path_capsule_boxes,
                        standing_capsules,
                        zero_capsules,
                        stowed_capsules,
                    )
                )
    ledger_status = _mass_ledger_status(config.mass_ledger_items)
    joint_rows = _combine_joint_gates(
        config, propulsion, geometry_rows, energy, ledger_status
    )
    return ArchitectureResult(
        status=STATUS_ANALYSIS_ONLY,
        procurement_allowed=False,
        overall_architecture_feasibility=STATUS_OVERALL_UNDETERMINED,
        mass_ledger_status=ledger_status,
        stow_requirements_status=config.stow_requirements.status(),
        stow_pose_evidence_status=STOW_POSE_EVIDENCE_UNQUALIFIED,
        stow_pose_is_hardware_validated=False,
        robust_geometry_status=ROBUST_GEOMETRY_UNDETERMINED,
        transition_proof_flag=TRANSITION_PROOF_FLAG,
        config=config,
        baseline=baseline_check,
        standing_joints=standing,
        analysis_stowed_joints=stowed,
        mass_ledger_items=config.mass_ledger_items,
        geometry_candidates=tuple(geometry_rows),
        joint_gate_rows=tuple(joint_rows),
        unmodeled=_unmodeled_factors(),
        diagnostic={
            'energy_rows_solved': len(energy),
            'geometry_candidate_count': len(geometry_rows),
            'joint_gate_row_count': len(joint_rows),
            'path_sample_count': config.sample_count,
            'zero_pose_included_in_named_poses': True,
            'g1_urdf_modified': False,
            'analysis_stowed_written_to_standing_pose': False,
            'stow_pose_is_hardware_validated': False,
            'geometry_is_nominal_ideal_size_only': True,
            'geometry_uncertainty_allowance_m': (
                config.geometry_uncertainty_allowance_m
            ),
            'geometry_solver': geometry_solver.as_dict(),
        },
    )



def _parse_architecture_config(
    raw: Any,
    config_path: Path,
) -> ArchitectureConfig:
    root = as_mapping(raw, 'config root')
    geometry = as_mapping(require_key(root, 'geometry', ''), 'geometry')
    clearance = as_mapping(require_key(root, 'clearance', ''), 'clearance')
    sweep = as_mapping(require_key(root, 'leg_sweep', ''), 'leg_sweep')
    stowed = as_mapping(
        require_key(root, 'analysis_stowed', ''), 'analysis_stowed'
    )
    stow_req_raw = as_mapping(
        require_key(root, 'stow_requirements', ''), 'stow_requirements'
    )
    baseline_raw = as_mapping(
        require_key(root, 'g1_baseline', ''), 'g1_baseline'
    )
    ledger_raw = as_mapping(
        require_key(root, 'mass_ledger', ''), 'mass_ledger'
    )
    sources = as_mapping(require_key(root, 'g1_sources', ''), 'g1_sources')
    propulsion = as_mapping(require_key(root, 'propulsion', ''), 'propulsion')
    diameters = tuple(
        as_float(value, f'propeller_diameters_in[{index}]')
        for index, value in enumerate(
            as_list(
                require_key(root, 'propeller_diameters_in', ''),
                'propeller_diameters_in',
            )
        )
    )
    radii = tuple(
        as_float(value, f'motor_center_radii_m[{index}]')
        for index, value in enumerate(
            as_list(
                require_key(root, 'motor_center_radii_m', ''),
                'motor_center_radii_m',
            )
        )
    )
    stowed_joints_raw = as_mapping(
        require_key(stowed, 'joints', 'analysis_stowed'),
        'analysis_stowed.joints',
    )
    stowed_joints = {
        as_str(name, 'analysis_stowed.joints key'): as_float(
            value, f'analysis_stowed.joints.{name}'
        )
        for name, value in stowed_joints_raw.items()
    }
    baseline_yaml = {
        key: as_float(require_key(baseline_raw, key, 'g1_baseline'), f'g1_baseline.{key}')
        for key, _xacro in G1_BASELINE_XACRO_KEYS
    }
    baseline_yaml['rotor_plane_z_m'] = as_float(
        require_key(baseline_raw, 'rotor_plane_z_m', 'g1_baseline'),
        'g1_baseline.rotor_plane_z_m',
    )
    baseline_yaml['sensor_pod_y_m'] = as_float(
        require_key(baseline_raw, 'sensor_pod_y_m', 'g1_baseline'),
        'g1_baseline.sensor_pod_y_m',
    )
    xacro_rel = as_str(
        require_key(sources, 'xacro_relpath', 'g1_sources'),
        'g1_sources.xacro_relpath',
    )
    standing_rel = as_str(
        require_key(sources, 'standing_pose_relpath', 'g1_sources'),
        'g1_sources.standing_pose_relpath',
    )
    propulsion_rel = as_str(
        require_key(propulsion, 'config_relpath', 'propulsion'),
        'propulsion.config_relpath',
    )
    propulsion_path = (config_path.parent / propulsion_rel).resolve()
    return ArchitectureConfig(
        status=as_str(require_key(root, 'status', ''), 'status'),
        procurement_allowed=as_bool(
            require_key(root, 'procurement_allowed', ''),
            'procurement_allowed',
        ),
        notes=optional_str(root.get('notes', ''), 'notes'),
        rotor_count=as_int(
            require_key(geometry, 'rotor_count', 'geometry'),
            'geometry.rotor_count',
        ),
        propeller_diameters_in=diameters,
        motor_center_radii_m=radii,
        min_tip_clearance_m=as_float(
            require_key(clearance, 'min_tip_clearance_m', 'clearance'),
            'clearance.min_tip_clearance_m',
        ),
        min_body_clearance_m=as_float(
            require_key(clearance, 'min_body_clearance_m', 'clearance'),
            'clearance.min_body_clearance_m',
        ),
        min_sensor_pod_clearance_m=as_float(
            require_key(
                clearance, 'min_sensor_pod_clearance_m', 'clearance'
            ),
            'clearance.min_sensor_pod_clearance_m',
        ),
        min_leg_clearance_m=as_float(
            require_key(clearance, 'min_leg_clearance_m', 'clearance'),
            'clearance.min_leg_clearance_m',
        ),
        geometry_uncertainty_allowance_m=as_optional_non_negative_float(
            require_key(
                clearance, 'geometry_uncertainty_allowance_m', 'clearance'
            ),
            'clearance.geometry_uncertainty_allowance_m',
        ),
        sample_count=as_int(
            require_key(sweep, 'sample_count', 'leg_sweep'),
            'leg_sweep.sample_count',
        ),
        analysis_stowed_pose_kind=as_str(
            require_key(stowed, 'pose_kind', 'analysis_stowed'),
            'analysis_stowed.pose_kind',
        ),
        analysis_stowed_notes=optional_str(
            stowed.get('notes', ''), 'analysis_stowed.notes'
        ),
        analysis_stowed_joints=stowed_joints,
        stow_requirements=_parse_stow_requirements(stow_req_raw),
        g1_baseline_yaml=baseline_yaml,
        mass_ledger_items=_parse_mass_ledger(ledger_raw),
        propulsion_config_path=propulsion_path,
        xacro_path=resolve_description_file(xacro_rel),
        standing_pose_path=resolve_description_file(standing_rel),
        raw=root,
    )



def _parse_stow_requirements(raw: Mapping[str, Any]) -> StowRequirements:
    values: dict[str, float | None] = {}
    extra = sorted(set(raw) - set(REQUIRED_STOW_REQUIREMENT_KEYS))
    if extra:
        raise InvalidInputError(f'stow_requirements unknown keys: {extra}')
    for key in REQUIRED_STOW_REQUIREMENT_KEYS:
        values[key] = as_optional_non_negative_float(
            require_key(raw, key, 'stow_requirements'),
            f'stow_requirements.{key}',
        )
    return StowRequirements(
        maximum_total_height_m=values['maximum_total_height_m'],
        maximum_leg_below_body_m=values['maximum_leg_below_body_m'],
        maximum_planform_length_m=values['maximum_planform_length_m'],
        maximum_planform_width_m=values['maximum_planform_width_m'],
    )



def _unmodeled_factors() -> tuple[str, ...]:
    return (
        'Rotor disks are zero-thickness filled circles; blade thickness, '
        'coning, flapping, and guards are omitted.',
        'Leg collisions use capsule / line-plus-radius proxies, not CAD solids.',
        'Standing to analysis_stowed uses linear joint-space sampling only. '
        + TRANSITION_PROOF_FLAG,
        'Zero pose is reported as a named pose, not a continuous walk from standing.',
        'No aero interaction, downwash, or rotor-rotor coupling.',
        'No structural deflection, vibration, or folding-mechanism kinematics.',
        'G1.5 energy-mass closure is reused; it is not whole-vehicle mass closure.',
        'Energy-mass closure does not include arm-extension, fastener, harness, '
        'or reinforcement mass when motor_center_radius_m != 0.30 m.',
        'G1 URDF placeholder masses are not a parts mass ledger.',
        'No motor, ESC, propeller, or battery hardware data.',
        'analysis_stowed is ANALYSIS_POSE_ONLY / UNQUALIFIED_ANALYSIS_POSE. '
        'It only proves that one analysis path can be computed. It does not '
        'prove flight-stow requirements, locking, or mechanical realizability.',
        'stow_requirements are unspecified (all null); status is INCOMPLETE.',
        'Geometry uses ideal nominal sizes. geometry_uncertainty_allowance_m '
        'is null; robust clearance is UNDETERMINED.',
        'Candidate radii and diameters are planning values; G1 hex_arm_span is unchanged.',
        'Results are ANALYSIS_ONLY and must not be used for procurement.',
    )
