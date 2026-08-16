"""CSV serialization of joint-gate rows.

Column names, order, and cell formatting are part of the official report
contract. Unknown masses stay empty cells, never zero.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import csv
from io import StringIO
import math
from typing import Any

from arachne_hx6_analysis.architecture import (
    STOW_POSE_EVIDENCE_UNQUALIFIED,
    TRANSITION_PROOF_FLAG,
    ArchitectureResult,
)
from arachne_hx6_analysis.model import (
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
)

def _csv_cell(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidInputError(f'CSV value is not finite: {value!r}')
        if abs(value) < 1.0e-3 and value != 0.0:
            return repr(value)
        return f'{value:.8f}'.rstrip('0').rstrip('.')
    if isinstance(value, (list, tuple)):
        return ','.join(str(item) for item in value)
    return str(value)


def render_architecture_csv(result: ArchitectureResult) -> str:
    fieldnames = [
        'status',
        'not_for_procurement',
        'procurement_allowed',
        'overall_architecture_feasibility',
        'mass_ledger_status',
        'stow_requirements_status',
        'stow_pose_evidence_status',
        'robust_geometry_status',
        'uncertainty_case',
        'scenario_name',
        'diameter_inch',
        'diameter_m',
        'motor_center_radius_m',
        'adjacent_motor_center_m',
        'adjacent_rotor_tip_clearance_m',
        'min_motor_center_radius_m',
        'rotor_envelope_diameter_m',
        'rotor_spacing_gate',
        'body_clearance_m',
        'body_clearance_gate',
        'sensor_pod_clearance_m',
        'sensor_pod_clearance_gate',
        'sampled_min_clearance_m',
        'sampled_leg_sweep_gate',
        'nominal_geometry_status',
        'energy_mass_closure',
        'energy_mass_closure_status',
        'energy_total_mass_kg',
        'energy_battery_mass_kg',
        'arm_radius_mass_coupling_status',
        'architecture_gate',
        'standing_length_m',
        'standing_width_m',
        'standing_height_m',
        'stowed_length_m',
        'stowed_width_m',
        'stowed_height_m',
        'standing_leg_below_body_m',
        'analysis_pose_leg_below_body_m',
        'height_reduction_m',
        'height_reduction_ratio',
        'rotor_plane_to_lowest_leg_point_m',
        'rejection_reasons',
        'limitation_reasons',
        'transition_proof_flag',
    ]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    for row in result.joint_gate_rows:
        writer.writerow({
            'status': STATUS_ANALYSIS_ONLY,
            'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
            'procurement_allowed': _csv_cell(False),
            'overall_architecture_feasibility': STATUS_OVERALL_UNDETERMINED,
            'mass_ledger_status': row.mass_ledger_status,
            'stow_requirements_status': row.stow_requirements_status,
            'stow_pose_evidence_status': STOW_POSE_EVIDENCE_UNQUALIFIED,
            'robust_geometry_status': row.robust_geometry_status,
            'uncertainty_case': row.uncertainty_case,
            'scenario_name': row.scenario_name,
            'diameter_inch': f'{row.diameter_inch:.4f}',
            'diameter_m': f'{inches_to_metres_safe(row.diameter_inch):.6f}',
            'motor_center_radius_m': _csv_cell(row.motor_center_radius_m),
            'adjacent_motor_center_m': _csv_cell(row.adjacent_motor_center_m),
            'adjacent_rotor_tip_clearance_m': _csv_cell(
                row.adjacent_rotor_tip_clearance_m
            ),
            'min_motor_center_radius_m': _csv_cell(row.min_motor_center_radius_m),
            'rotor_envelope_diameter_m': _csv_cell(row.rotor_envelope_diameter_m),
            'rotor_spacing_gate': row.rotor_spacing_gate,
            'body_clearance_m': _csv_cell(row.body_clearance_m),
            'body_clearance_gate': row.body_clearance_gate,
            'sensor_pod_clearance_m': _csv_cell(row.sensor_pod_clearance_m),
            'sensor_pod_clearance_gate': row.sensor_pod_clearance_gate,
            'sampled_min_clearance_m': _csv_cell(row.sampled_min_clearance_m),
            'sampled_leg_sweep_gate': row.sampled_leg_sweep_gate,
            'nominal_geometry_status': row.nominal_geometry_status,
            'energy_mass_closure': _csv_cell(row.energy_mass_closure),
            'energy_mass_closure_status': row.energy_mass_closure_status,
            'energy_total_mass_kg': _csv_cell(row.energy_total_mass_kg),
            'energy_battery_mass_kg': _csv_cell(row.energy_battery_mass_kg),
            'arm_radius_mass_coupling_status': row.arm_radius_mass_coupling_status,
            'architecture_gate': row.architecture_gate,
            'standing_length_m': _csv_cell(row.standing_length_m),
            'standing_width_m': _csv_cell(row.standing_width_m),
            'standing_height_m': _csv_cell(row.standing_height_m),
            'stowed_length_m': _csv_cell(row.stowed_length_m),
            'stowed_width_m': _csv_cell(row.stowed_width_m),
            'stowed_height_m': _csv_cell(row.stowed_height_m),
            'standing_leg_below_body_m': _csv_cell(row.standing_leg_below_body_m),
            'analysis_pose_leg_below_body_m': _csv_cell(
                row.analysis_pose_leg_below_body_m
            ),
            'height_reduction_m': _csv_cell(row.height_reduction_m),
            'height_reduction_ratio': _csv_cell(row.height_reduction_ratio),
            'rotor_plane_to_lowest_leg_point_m': _csv_cell(
                row.rotor_plane_to_lowest_leg_point_m
            ),
            'rejection_reasons': ','.join(row.rejection_reasons),
            'limitation_reasons': ','.join(row.limitation_reasons),
            'transition_proof_flag': TRANSITION_PROOF_FLAG,
        })
    return buf.getvalue()


def inches_to_metres_safe(diameter_inch: float) -> float:
    from arachne_hx6_analysis.model import inches_to_metres
    return inches_to_metres(diameter_inch)
