"""Energy-mass reuse and joint architecture gating.

Combines geometry candidates with G1.5 energy-mass rows. Allowed gates are
only REJECTED_* or UNDETERMINED_*; never a procurement or flight status.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from arachne_hx6_analysis.architecture_types import (
    ALLOWED_ARCHITECTURE_GATES,
    ARCH_GATE_REJECTED_ENERGY_CLOSURE,
    ARCH_GATE_REJECTED_GEOMETRY,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARCH_GATE_UNDETERMINED_MODEL_LIMITATION,
    ARM_COUPLING_UNMODELED,
    ARM_EXTENSION_LIMITATION_REASON,
    FORBIDDEN_ARCHITECTURE_STATUS_WORDS,
    GATE_CLEARANCE_MET,
    GATE_CLEARANCE_NOT_MET,
    MASS_LEDGER_COMPLETE,
    STOW_REQUIREMENTS_INCOMPLETE,
    ArchitectureConfig,
    GeometryCandidate,
    JointGateRow,
)
from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.solver import (
    PropulsionResult,
    apply_uncertainty_case,
    solve_battery_feedback,
)

def _solve_energy_matrix(
    propulsion_config: Any,
    diameters_in: Sequence[float],
) -> dict[tuple[str, str, float], PropulsionResult]:
    cache: dict[tuple[str, str, float], PropulsionResult] = {}
    for case in propulsion_config.uncertainty_cases:
        applied = apply_uncertainty_case(propulsion_config, case)
        for scenario in propulsion_config.mass_scenarios:
            for diameter_inch in diameters_in:
                cache[(case.name, scenario.name, float(diameter_inch))] = (
                    solve_battery_feedback(
                        applied,
                        scenario,
                        float(diameter_inch),
                        uncertainty_case=case.name,
                    )
                )
    return cache


def _combine_joint_gates(
    config: ArchitectureConfig,
    propulsion_config: Any,
    geometry_rows: Sequence[GeometryCandidate],
    energy: Mapping[tuple[str, str, float], PropulsionResult],
    ledger_status: str,
) -> list[JointGateRow]:
    geometry_by = {
        (row.diameter_inch, row.motor_center_radius_m): row
        for row in geometry_rows
    }
    rows: list[JointGateRow] = []
    for case in propulsion_config.uncertainty_cases:
        for scenario in propulsion_config.mass_scenarios:
            for diameter_inch in config.propeller_diameters_in:
                for radius_m in config.motor_center_radii_m:
                    geo = geometry_by[(float(diameter_inch), radius_m)]
                    energy_row = energy[
                        (case.name, scenario.name, float(diameter_inch))
                    ]
                    sweep_gate = (
                        GATE_CLEARANCE_NOT_MET
                        if geo.sampled_leg_sweep.below_threshold
                        else GATE_CLEARANCE_MET
                    )
                    reasons = list(geo.rejection_reasons)
                    limitations = list(geo.limitation_reasons)
                    if not energy_row.energy_mass_closure:
                        reasons.append('energy_mass_closure_infeasible')
                    if ledger_status != MASS_LEDGER_COMPLETE:
                        reasons.append('mass_ledger_incomplete')
                    stow_status = config.stow_requirements.status()
                    if stow_status == STOW_REQUIREMENTS_INCOMPLETE:
                        if 'stow_requirements_incomplete' not in limitations:
                            limitations.append('stow_requirements_incomplete')
                    geometry_fail = (
                        geo.rotor_spacing_gate == GATE_CLEARANCE_NOT_MET
                        or geo.body_clearance_gate == GATE_CLEARANCE_NOT_MET
                        or geo.sensor_pod_clearance_gate == GATE_CLEARANCE_NOT_MET
                        or sweep_gate == GATE_CLEARANCE_NOT_MET
                    )
                    if geometry_fail:
                        arch_gate = ARCH_GATE_REJECTED_GEOMETRY
                    elif not energy_row.energy_mass_closure:
                        arch_gate = ARCH_GATE_REJECTED_ENERGY_CLOSURE
                    elif ledger_status != MASS_LEDGER_COMPLETE:
                        arch_gate = ARCH_GATE_UNDETERMINED_MASS_LEDGER
                    else:
                        arch_gate = ARCH_GATE_UNDETERMINED_MODEL_LIMITATION
                    if (
                        geo.arm_radius_mass_coupling_status
                        == ARM_COUPLING_UNMODELED
                    ):
                        if ARM_EXTENSION_LIMITATION_REASON not in limitations:
                            limitations.append(ARM_EXTENSION_LIMITATION_REASON)
                        if (
                            not geometry_fail
                            and energy_row.energy_mass_closure
                            and arch_gate == ARCH_GATE_UNDETERMINED_MASS_LEDGER
                        ):
                            # Keep the higher-priority mass-ledger gate; the
                            # unmodeled arm-extension mass stays in limitations.
                            pass
                        elif (
                            not geometry_fail
                            and energy_row.energy_mass_closure
                            and ledger_status == MASS_LEDGER_COMPLETE
                        ):
                            arch_gate = ARCH_GATE_UNDETERMINED_MODEL_LIMITATION
                    if arch_gate not in ALLOWED_ARCHITECTURE_GATES:
                        raise InvalidInputError(
                            f'internal architecture_gate {arch_gate!r} is not allowed'
                        )
                    for forbidden in FORBIDDEN_ARCHITECTURE_STATUS_WORDS:
                        if forbidden == arch_gate:
                            raise InvalidInputError(
                                f'forbidden architecture_gate {forbidden}'
                            )
                    rows.append(
                        JointGateRow(
                            uncertainty_case=case.name,
                            scenario_name=scenario.name,
                            diameter_inch=float(diameter_inch),
                            motor_center_radius_m=radius_m,
                            rotor_spacing_gate=geo.rotor_spacing_gate,
                            body_clearance_gate=geo.body_clearance_gate,
                            sensor_pod_clearance_gate=geo.sensor_pod_clearance_gate,
                            sampled_leg_sweep_gate=sweep_gate,
                            nominal_geometry_status=geo.nominal_geometry_status,
                            robust_geometry_status=geo.robust_geometry_status,
                            energy_mass_closure=energy_row.energy_mass_closure,
                            energy_mass_closure_status=(
                                energy_row.energy_mass_closure_status
                            ),
                            mass_ledger_status=ledger_status,
                            stow_requirements_status=stow_status,
                            arm_radius_mass_coupling_status=(
                                geo.arm_radius_mass_coupling_status
                            ),
                            architecture_gate=arch_gate,
                            rejection_reasons=tuple(reasons),
                            limitation_reasons=tuple(limitations),
                            adjacent_motor_center_m=geo.adjacent_motor_center_m,
                            adjacent_rotor_tip_clearance_m=(
                                geo.adjacent_rotor_tip_clearance_m
                            ),
                            min_motor_center_radius_m=geo.min_motor_center_radius_m,
                            rotor_envelope_diameter_m=geo.rotor_envelope_diameter_m,
                            body_clearance_m=geo.body_clearance_m,
                            sensor_pod_clearance_m=geo.sensor_pod_clearance_m,
                            sampled_min_clearance_m=geo.sampled_leg_sweep.min_clearance_m,
                            standing_length_m=geo.standing_envelope['length_m'],
                            standing_width_m=geo.standing_envelope['width_m'],
                            standing_height_m=geo.standing_envelope['height_m'],
                            stowed_length_m=geo.analysis_stowed_envelope['length_m'],
                            stowed_width_m=geo.analysis_stowed_envelope['width_m'],
                            stowed_height_m=geo.analysis_stowed_envelope['height_m'],
                            standing_leg_below_body_m=geo.standing_leg_below_body_m,
                            analysis_pose_leg_below_body_m=(
                                geo.analysis_pose_leg_below_body_m
                            ),
                            height_reduction_m=geo.height_reduction_m,
                            height_reduction_ratio=geo.height_reduction_ratio,
                            rotor_plane_to_lowest_leg_point_m=(
                                geo.rotor_plane_to_lowest_leg_point_m
                            ),
                            energy_total_mass_kg=energy_row.total_mass_kg,
                            energy_battery_mass_kg=energy_row.battery_mass_kg,
                        )
                    )
    return rows
