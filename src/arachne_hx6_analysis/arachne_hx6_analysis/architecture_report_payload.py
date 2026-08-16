"""Official architecture JSON payload construction.

Field names, order, and semantics of the JSON object are part of the G2
report contract. Do not reorder keys or change null/finite rules here.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Any, Sequence

from arachne_hx6_analysis.architecture import (
    ARCH_GATE_REJECTED_ENERGY_CLOSURE,
    ARCH_GATE_REJECTED_GEOMETRY,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARCH_GATE_UNDETERMINED_MODEL_LIMITATION,
    ArchitectureResult,
    GeometryCandidate,
    JointGateRow,
    POSE_KIND_ANALYSIS_ONLY,
    REQUIRED_JOINT_NAMES,
    TRANSITION_PROOF_FLAG,
)
from arachne_hx6_analysis.model import (
    REQUIRED_UNCERTAINTY_CASES,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
)

EQUATIONS = (
    ('inches_to_metres', 'D_m = D_in * 0.0254', 'm'),
    ('adjacent_motor_distance', 'd_adj = 2 * R * sin(pi / n)', 'm'),
    ('adjacent_tip_clearance', 'delta_tip = d_adj - D', 'm'),
    (
        'min_motor_center_radius',
        'R_min = (D + tip_gap) / (2 * sin(pi / n))',
        'm',
    ),
    ('rotor_envelope_diameter', 'D_env = 2 * R + D', 'm'),
    (
        'disk_disk_signed_gap',
        'filled horizontal disks; coplanar gap = center_xy - r1 - r2',
        'm',
    ),
    (
        'disk_aabb_signed_gap',
        'filled horizontal disk versus axis-aligned body / sensor_pod box',
        'm',
    ),
    (
        'disk_capsule_signed_gap',
        'filled horizontal disk versus leg capsule (segment + radius); '
        'unsigned segment-disk distance is returned only when '
        'upper_bound - lower_bound <= geometry_solver_tolerance_m; '
        'reaching the evaluation budget without that certificate is '
        'fail-closed and does not return a distance',
        'm',
    ),
    (
        'linear_joint_path',
        'q(s) = (1-s) * q_standing + s * q_analysis_stowed, s = i/(N-1)',
        'rad',
    ),
)



def build_architecture_json(
    result: ArchitectureResult,
    generated_at: str,
) -> dict[str, Any]:
    """Official architecture snapshot plus an isolated diagnostic block."""
    return {
        'status': STATUS_ANALYSIS_ONLY,
        'procurement_allowed': False,
        'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
        'overall_architecture_feasibility': STATUS_OVERALL_UNDETERMINED,
        'mass_ledger_status': result.mass_ledger_status,
        'stow_requirements_status': result.stow_requirements_status,
        'stow_pose_evidence_status': result.stow_pose_evidence_status,
        'stow_pose_is_hardware_validated': result.stow_pose_is_hardware_validated,
        'robust_geometry_status': result.robust_geometry_status,
        'transition_proof_flag': TRANSITION_PROOF_FLAG,
        'generated_at_utc': generated_at,
        'inputs': _inputs_snapshot(result),
        'g1_baseline_consistency': {
            'consistent': result.baseline.consistent,
            'xacro_path': result.baseline.xacro_path,
            'standing_pose_path': result.baseline.standing_pose_path,
            'comparisons': list(result.baseline.comparisons),
        },
        'poses': {
            'standing': dict(result.standing_joints),
            'zero': {name: 0.0 for name in REQUIRED_JOINT_NAMES},
            'analysis_stowed': {
                'pose_kind': POSE_KIND_ANALYSIS_ONLY,
                'stow_pose_evidence_status': result.stow_pose_evidence_status,
                'stow_requirements_status': result.stow_requirements_status,
                'stow_pose_is_hardware_validated': (
                    result.stow_pose_is_hardware_validated
                ),
                'notes': result.config.analysis_stowed_notes,
                'joints': dict(result.analysis_stowed_joints),
            },
        },
        'stow_requirements': result.config.stow_requirements.as_dict(),
        'equations': [
            {'name': name, 'equation': equation, 'unit': unit}
            for name, equation, unit in EQUATIONS
        ],
        'geometry_candidates': [
            _geometry_candidate_dict(row) for row in result.geometry_candidates
        ],
        'joint_gate_rows': [
            _joint_gate_dict(row) for row in result.joint_gate_rows
        ],
        'joint_gate_summary_by_uncertainty': _gate_summary_by_uncertainty(result),
        'mass_ledger': {
            'status': result.mass_ledger_status,
            'items': [
                {
                    'id': item.item_id,
                    'evidence_status': item.evidence_status,
                    'mass_kg': item.mass_kg,
                    'source_kind': item.source_kind,
                    'notes': item.notes,
                }
                for item in result.mass_ledger_items
            ],
        },
        'rejection_reasons': _unique_reasons(result.joint_gate_rows),
        'limitation_reasons': _unique_limitations(result.joint_gate_rows),
        'unmodeled': list(result.unmodeled),
        'diagnostic': dict(result.diagnostic),
    }



def _inputs_snapshot(result: ArchitectureResult) -> dict[str, Any]:
    config = result.config
    return {
        'status': config.status,
        'procurement_allowed': config.procurement_allowed,
        'notes': config.notes,
        'rotor_count': config.rotor_count,
        'propeller_diameters_in': list(config.propeller_diameters_in),
        'motor_center_radii_m': list(config.motor_center_radii_m),
        'min_tip_clearance_m': config.min_tip_clearance_m,
        'min_body_clearance_m': config.min_body_clearance_m,
        'min_sensor_pod_clearance_m': config.min_sensor_pod_clearance_m,
        'min_leg_clearance_m': config.min_leg_clearance_m,
        'sample_count': config.sample_count,
        'units': {
            'propeller_diameters_in': 'inch (display / input only)',
            'all_computed_lengths': 'metre',
            'joint_angles': 'radian',
            'masses': 'kilogram',
        },
        'propulsion_config_path': str(config.propulsion_config_path),
        'analysis_stowed_pose_kind': config.analysis_stowed_pose_kind,
        'geometry_uncertainty_allowance_m': (
            config.geometry_uncertainty_allowance_m
        ),
        'stow_requirements': config.stow_requirements.as_dict(),
    }


def _geometry_candidate_dict(row: GeometryCandidate) -> dict[str, Any]:
    sweep = row.sampled_leg_sweep
    return {
        'diameter_inch': row.diameter_inch,
        'diameter_m': row.diameter_m,
        'motor_center_radius_m': row.motor_center_radius_m,
        'adjacent_motor_center_m': row.adjacent_motor_center_m,
        'adjacent_rotor_tip_clearance_m': row.adjacent_rotor_tip_clearance_m,
        'min_motor_center_radius_m': row.min_motor_center_radius_m,
        'rotor_envelope_diameter_m': row.rotor_envelope_diameter_m,
        'rotor_spacing_gate': row.rotor_spacing_gate,
        'body_clearance_m': row.body_clearance_m,
        'body_clearance_gate': row.body_clearance_gate,
        'body_worst_rotor': row.body_worst_rotor,
        'sensor_pod_clearance_m': row.sensor_pod_clearance_m,
        'sensor_pod_clearance_gate': row.sensor_pod_clearance_gate,
        'sensor_pod_worst_rotor': row.sensor_pod_worst_rotor,
        'sampled_leg_sweep': {
            'sample_count': sweep.sample_count,
            'min_clearance_m': sweep.min_clearance_m,
            'worst_sample_index': sweep.worst_sample_index,
            'worst_path_fraction': sweep.worst_path_fraction,
            'worst_leg_segment': sweep.worst_leg_segment,
            'worst_rotor': sweep.worst_rotor,
            'below_threshold': sweep.below_threshold,
            'start_clearance_m': sweep.start_clearance_m,
            'end_clearance_m': sweep.end_clearance_m,
            'proof_flag': sweep.proof_flag,
        },
        'zero_pose_leg_clearance_m': row.zero_pose_leg_clearance_m,
        'standing_envelope_m': dict(row.standing_envelope),
        'zero_envelope_m': dict(row.zero_envelope),
        'analysis_stowed_envelope_m': dict(row.analysis_stowed_envelope),
        'rotor_spacing_clearance': row.rotor_spacing_evidence.as_dict(),
        'body_clearance': row.body_clearance_evidence.as_dict(),
        'sensor_pod_clearance': row.sensor_pod_clearance_evidence.as_dict(),
        'sampled_leg_clearance': row.sampled_leg_evidence.as_dict(),
        'nominal_geometry_status': row.nominal_geometry_status,
        'robust_geometry_status': row.robust_geometry_status,
        'arm_radius_mass_coupling_status': row.arm_radius_mass_coupling_status,
        'standing_total_height_m': row.standing_total_height_m,
        'analysis_pose_total_height_m': row.analysis_pose_total_height_m,
        'height_reduction_m': row.height_reduction_m,
        'height_reduction_ratio': row.height_reduction_ratio,
        'standing_leg_below_body_m': row.standing_leg_below_body_m,
        'analysis_pose_leg_below_body_m': row.analysis_pose_leg_below_body_m,
        'standing_planform_length_m': row.standing_planform_length_m,
        'standing_planform_width_m': row.standing_planform_width_m,
        'analysis_pose_planform_length_m': row.analysis_pose_planform_length_m,
        'analysis_pose_planform_width_m': row.analysis_pose_planform_width_m,
        'standing_rotor_plane_to_lowest_leg_point_m': (
            row.standing_rotor_plane_to_lowest_leg_point_m
        ),
        'rotor_plane_to_lowest_leg_point_m': (
            row.rotor_plane_to_lowest_leg_point_m
        ),
        'rejection_reasons': list(row.rejection_reasons),
        'limitation_reasons': list(row.limitation_reasons),
    }


def _joint_gate_dict(row: JointGateRow) -> dict[str, Any]:
    return {
        'uncertainty_case': row.uncertainty_case,
        'scenario_name': row.scenario_name,
        'diameter_inch': row.diameter_inch,
        'motor_center_radius_m': row.motor_center_radius_m,
        'rotor_spacing_gate': row.rotor_spacing_gate,
        'body_clearance_gate': row.body_clearance_gate,
        'sensor_pod_clearance_gate': row.sensor_pod_clearance_gate,
        'sampled_leg_sweep_gate': row.sampled_leg_sweep_gate,
        'nominal_geometry_status': row.nominal_geometry_status,
        'robust_geometry_status': row.robust_geometry_status,
        'energy_mass_closure': row.energy_mass_closure,
        'energy_mass_closure_status': row.energy_mass_closure_status,
        'mass_ledger_status': row.mass_ledger_status,
        'stow_requirements_status': row.stow_requirements_status,
        'arm_radius_mass_coupling_status': row.arm_radius_mass_coupling_status,
        'architecture_gate': row.architecture_gate,
        'rejection_reasons': list(row.rejection_reasons),
        'limitation_reasons': list(row.limitation_reasons),
        'adjacent_motor_center_m': row.adjacent_motor_center_m,
        'adjacent_rotor_tip_clearance_m': row.adjacent_rotor_tip_clearance_m,
        'min_motor_center_radius_m': row.min_motor_center_radius_m,
        'rotor_envelope_diameter_m': row.rotor_envelope_diameter_m,
        'body_clearance_m': row.body_clearance_m,
        'sensor_pod_clearance_m': row.sensor_pod_clearance_m,
        'sampled_min_clearance_m': row.sampled_min_clearance_m,
        'standing_length_m': row.standing_length_m,
        'standing_width_m': row.standing_width_m,
        'standing_height_m': row.standing_height_m,
        'stowed_length_m': row.stowed_length_m,
        'stowed_width_m': row.stowed_width_m,
        'stowed_height_m': row.stowed_height_m,
        'standing_leg_below_body_m': row.standing_leg_below_body_m,
        'analysis_pose_leg_below_body_m': row.analysis_pose_leg_below_body_m,
        'height_reduction_m': row.height_reduction_m,
        'height_reduction_ratio': row.height_reduction_ratio,
        'rotor_plane_to_lowest_leg_point_m': row.rotor_plane_to_lowest_leg_point_m,
        'energy_total_mass_kg': row.energy_total_mass_kg,
        'energy_battery_mass_kg': row.energy_battery_mass_kg,
    }


def _gate_summary_by_uncertainty(result: ArchitectureResult) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name in REQUIRED_UNCERTAINTY_CASES:
        rows = [
            row for row in result.joint_gate_rows
            if row.uncertainty_case == name
        ]
        counts = {
            ARCH_GATE_REJECTED_GEOMETRY: 0,
            ARCH_GATE_REJECTED_ENERGY_CLOSURE: 0,
            ARCH_GATE_UNDETERMINED_MASS_LEDGER: 0,
            ARCH_GATE_UNDETERMINED_MODEL_LIMITATION: 0,
        }
        for row in rows:
            counts[row.architecture_gate] = counts.get(row.architecture_gate, 0) + 1
        summary[name] = {'rows': len(rows), **counts}
    return summary


def _unique_limitations(rows: Sequence[JointGateRow]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for reason in row.limitation_reasons:
            if reason not in seen:
                seen.append(reason)
    return seen


def _unique_reasons(rows: Sequence[JointGateRow]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for reason in row.rejection_reasons:
            if reason not in seen:
                seen.append(reason)
    return seen
