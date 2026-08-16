"""Nominal geometry candidate evaluation, sampled leg sweep, and envelopes.

Clearance gates and certified disk-capsule distances are computed here.
Robust geometry remains UNDETERMINED when the uncertainty allowance is null.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import math
from typing import Sequence

from arachne_hx6_analysis.architecture_types import (
    ARM_COUPLING_BASELINE,
    ARM_COUPLING_UNMODELED,
    ARM_EXTENSION_LIMITATION_REASON,
    BASELINE_MOTOR_CENTER_RADIUS_M,
    GATE_CLEARANCE_MET,
    GATE_CLEARANCE_NOT_MET,
    NOMINAL_GEOMETRY_MET,
    NOMINAL_GEOMETRY_NOT_MET,
    ROBUST_GATE_UNQUANTIFIED,
    ROBUST_GEOMETRY_UNDETERMINED,
    TRANSITION_PROOF_FLAG,
    ArchitectureConfig,
    ClearanceEvidence,
    G1Baseline,
    GeometryCandidate,
    SweepResult,
    _BASELINE_ABS_TOL,
    _GATE_EPS,
)
from arachne_hx6_analysis.geometry import (
    Aabb,
    Capsule,
    HorizontalDisk,
    aabb_extents,
    capsule_aabb,
    hex_layout_metrics,
    horizontal_disk_aabb,
    make_rotor_disks,
    min_disk_box_clearance_m,
    min_disk_capsule_clearance_m,
    signed_distance_disk_capsule,
    union_aabb,
)
from arachne_hx6_analysis.model import InvalidInputError

def _gate(value_m: float, threshold_m: float) -> str:
    if not math.isfinite(value_m) or not math.isfinite(threshold_m):
        raise InvalidInputError('clearance gate inputs must be finite')
    if value_m + _GATE_EPS >= threshold_m:
        return GATE_CLEARANCE_MET
    return GATE_CLEARANCE_NOT_MET


def _clearance_evidence(
    nominal_clearance_m: float,
    required_clearance_m: float,
    allowance_m: float | None,
) -> ClearanceEvidence:
    if not math.isfinite(nominal_clearance_m) or not math.isfinite(
        required_clearance_m
    ):
        raise InvalidInputError('clearance values must be finite')
    margin = nominal_clearance_m - required_clearance_m
    nominal_gate = _gate(nominal_clearance_m, required_clearance_m)
    if allowance_m is None:
        return ClearanceEvidence(
            nominal_clearance_m=nominal_clearance_m,
            required_clearance_m=required_clearance_m,
            nominal_clearance_margin_m=margin,
            geometry_uncertainty_allowance_m=None,
            robust_clearance_margin_m=None,
            nominal_gate=nominal_gate,
            robust_gate=ROBUST_GATE_UNQUANTIFIED,
        )
    if not math.isfinite(allowance_m) or allowance_m < 0.0:
        raise InvalidInputError(
            'geometry_uncertainty_allowance_m must be null or finite >= 0, '
            f'got {allowance_m}'
        )
    robust_margin = nominal_clearance_m - required_clearance_m - allowance_m
    robust_gate = (
        GATE_CLEARANCE_MET
        if robust_margin + _GATE_EPS >= 0.0
        else GATE_CLEARANCE_NOT_MET
    )
    return ClearanceEvidence(
        nominal_clearance_m=nominal_clearance_m,
        required_clearance_m=required_clearance_m,
        nominal_clearance_margin_m=margin,
        geometry_uncertainty_allowance_m=allowance_m,
        robust_clearance_margin_m=robust_margin,
        nominal_gate=nominal_gate,
        robust_gate=robust_gate,
    )


def _arm_coupling_status(radius_m: float) -> str:
    if abs(radius_m - BASELINE_MOTOR_CENTER_RADIUS_M) <= _BASELINE_ABS_TOL:
        return ARM_COUPLING_BASELINE
    return ARM_COUPLING_UNMODELED


def _lowest_capsule_z_m(capsules: Sequence[Capsule]) -> float:
    lowest = min(
        min(capsule.a[2], capsule.b[2]) - capsule.radius for capsule in capsules
    )
    if not math.isfinite(lowest):
        raise InvalidInputError('lowest capsule z is not finite')
    return lowest


def _nominal_geometry_status(*gates: str) -> str:
    if any(gate == GATE_CLEARANCE_NOT_MET for gate in gates):
        return NOMINAL_GEOMETRY_NOT_MET
    if all(gate == GATE_CLEARANCE_MET for gate in gates):
        return NOMINAL_GEOMETRY_MET
    raise InvalidInputError(f'unexpected nominal gates: {gates}')


def _evaluate_geometry_candidate(
    config: ArchitectureConfig,
    baseline: G1Baseline,
    diameter_inch: float,
    diameter_m: float,
    radius_m: float,
    body_box: Aabb,
    left_pod: Aabb,
    right_pod: Aabb,
    camera_box: Aabb,
    path_capsules: Sequence[Sequence[Capsule]],
    path_capsule_boxes: Sequence[Sequence[Aabb]],
    standing_capsules: Sequence[Capsule],
    zero_capsules: Sequence[Capsule],
    stowed_capsules: Sequence[Capsule],
) -> GeometryCandidate:
    metrics = hex_layout_metrics(
        radius_m, diameter_m, config.rotor_count, config.min_tip_clearance_m
    )
    disks = make_rotor_disks(
        radius_m,
        diameter_m,
        baseline.rotor_plane_z_m,
        config.rotor_count,
        baseline.first_motor_yaw_rad,
    )
    spacing_gate = _gate(
        metrics['adjacent_rotor_tip_clearance_m'], config.min_tip_clearance_m
    )
    body_gap, body_rotor = min_disk_box_clearance_m(disks, body_box)
    body_gate = _gate(body_gap, config.min_body_clearance_m)
    left_gap, left_rotor = min_disk_box_clearance_m(disks, left_pod)
    right_gap, right_rotor = min_disk_box_clearance_m(disks, right_pod)
    if left_gap <= right_gap:
        pod_gap, pod_rotor = left_gap, left_rotor
    else:
        pod_gap, pod_rotor = right_gap, right_rotor
    pod_gate = _gate(pod_gap, config.min_sensor_pod_clearance_m)
    sweep = _evaluate_sweep(config, disks, path_capsules, path_capsule_boxes)
    sweep_gate = (
        GATE_CLEARANCE_NOT_MET if sweep.below_threshold else GATE_CLEARANCE_MET
    )
    zero_gap, _zero_disk, _zero_seg = min_disk_capsule_clearance_m(
        disks, zero_capsules
    )
    standing_env = _envelope(disks, standing_capsules, body_box, left_pod, right_pod, camera_box)
    zero_env = _envelope(disks, zero_capsules, body_box, left_pod, right_pod, camera_box)
    stowed_env = _envelope(disks, stowed_capsules, body_box, left_pod, right_pod, camera_box)
    allowance = config.geometry_uncertainty_allowance_m
    spacing_evidence = _clearance_evidence(
        metrics['adjacent_rotor_tip_clearance_m'],
        config.min_tip_clearance_m,
        allowance,
    )
    body_evidence = _clearance_evidence(
        body_gap, config.min_body_clearance_m, allowance
    )
    pod_evidence = _clearance_evidence(
        pod_gap, config.min_sensor_pod_clearance_m, allowance
    )
    sweep_evidence = _clearance_evidence(
        sweep.min_clearance_m, config.min_leg_clearance_m, allowance
    )
    nominal_status = _nominal_geometry_status(
        spacing_gate, body_gate, pod_gate, sweep_gate
    )
    standing_lowest = _lowest_capsule_z_m(standing_capsules)
    analysis_lowest = _lowest_capsule_z_m(stowed_capsules)
    standing_height = standing_env['height_m']
    analysis_height = stowed_env['height_m']
    if not math.isfinite(standing_height) or standing_height <= 0.0:
        raise InvalidInputError(
            f'standing_total_height_m must be finite and > 0, got {standing_height}'
        )
    height_reduction = standing_height - analysis_height
    height_ratio = height_reduction / standing_height
    arm_status = _arm_coupling_status(radius_m)
    reasons: list[str] = []
    limitations: list[str] = []
    if spacing_gate == GATE_CLEARANCE_NOT_MET:
        reasons.append(
            'adjacent_rotor_tip_clearance_below_min_tip_clearance'
        )
    if body_gate == GATE_CLEARANCE_NOT_MET:
        reasons.append('rotor_disk_body_clearance_below_threshold')
    if pod_gate == GATE_CLEARANCE_NOT_MET:
        reasons.append('rotor_disk_sensor_pod_clearance_below_threshold')
    if sweep.below_threshold:
        reasons.append('sampled_leg_sweep_clearance_below_threshold')
    if arm_status == ARM_COUPLING_UNMODELED:
        limitations.append(ARM_EXTENSION_LIMITATION_REASON)
    limitations.append('geometry_uncertainty_allowance_unquantified')
    limitations.append('stow_pose_unqualified_analysis_pose')
    limitations.append('stow_requirements_incomplete')
    return GeometryCandidate(
        diameter_inch=float(diameter_inch),
        diameter_m=diameter_m,
        motor_center_radius_m=radius_m,
        adjacent_motor_center_m=metrics['adjacent_motor_center_m'],
        adjacent_rotor_tip_clearance_m=metrics['adjacent_rotor_tip_clearance_m'],
        min_motor_center_radius_m=metrics['min_motor_center_radius_m'],
        rotor_envelope_diameter_m=metrics['rotor_envelope_diameter_m'],
        rotor_spacing_gate=spacing_gate,
        body_clearance_m=body_gap,
        body_clearance_gate=body_gate,
        body_worst_rotor=body_rotor,
        sensor_pod_clearance_m=pod_gap,
        sensor_pod_clearance_gate=pod_gate,
        sensor_pod_worst_rotor=pod_rotor,
        sampled_leg_sweep=sweep,
        zero_pose_leg_clearance_m=zero_gap,
        standing_envelope=standing_env,
        zero_envelope=zero_env,
        analysis_stowed_envelope=stowed_env,
        rotor_spacing_evidence=spacing_evidence,
        body_clearance_evidence=body_evidence,
        sensor_pod_clearance_evidence=pod_evidence,
        sampled_leg_evidence=sweep_evidence,
        nominal_geometry_status=nominal_status,
        robust_geometry_status=ROBUST_GEOMETRY_UNDETERMINED,
        arm_radius_mass_coupling_status=arm_status,
        standing_total_height_m=standing_height,
        analysis_pose_total_height_m=analysis_height,
        height_reduction_m=height_reduction,
        height_reduction_ratio=height_ratio,
        standing_leg_below_body_m=body_box.minimum[2] - standing_lowest,
        analysis_pose_leg_below_body_m=body_box.minimum[2] - analysis_lowest,
        standing_planform_length_m=standing_env['length_m'],
        standing_planform_width_m=standing_env['width_m'],
        analysis_pose_planform_length_m=stowed_env['length_m'],
        analysis_pose_planform_width_m=stowed_env['width_m'],
        standing_rotor_plane_to_lowest_leg_point_m=(
            baseline.rotor_plane_z_m - standing_lowest
        ),
        rotor_plane_to_lowest_leg_point_m=(
            baseline.rotor_plane_z_m - analysis_lowest
        ),
        rejection_reasons=tuple(reasons),
        limitation_reasons=tuple(limitations),
    )


def _evaluate_sweep(
    config: ArchitectureConfig,
    disks: Sequence[HorizontalDisk],
    path_capsules: Sequence[Sequence[Capsule]],
    path_capsule_boxes: Sequence[Sequence[Aabb]],
) -> SweepResult:
    best_gap = float('inf')
    best_index = 0
    best_segment = ''
    best_rotor = ''
    start_gap = None
    end_gap = None
    disk_boxes = [horizontal_disk_aabb(disk) for disk in disks]
    for index, capsules in enumerate(path_capsules):
        gap, rotor, segment = _min_disk_capsule_with_aabb(
            disks, disk_boxes, capsules, path_capsule_boxes[index]
        )
        if index == 0:
            start_gap = gap
        if index == len(path_capsules) - 1:
            end_gap = gap
        if gap < best_gap:
            best_gap = gap
            best_index = index
            best_segment = segment
            best_rotor = rotor
    denom = float(config.sample_count - 1)
    return SweepResult(
        sample_count=config.sample_count,
        min_clearance_m=best_gap,
        worst_sample_index=best_index,
        worst_path_fraction=float(best_index) / denom,
        worst_leg_segment=best_segment,
        worst_rotor=best_rotor,
        below_threshold=best_gap + _GATE_EPS < config.min_leg_clearance_m,
        start_clearance_m=float(start_gap),
        end_clearance_m=float(end_gap),
        proof_flag=TRANSITION_PROOF_FLAG,
    )


def _aabb_unsigned_separation(left: Aabb, right: Aabb) -> float:
    dx = max(0.0, left.minimum[0] - right.maximum[0], right.minimum[0] - left.maximum[0])
    dy = max(0.0, left.minimum[1] - right.maximum[1], right.minimum[1] - left.maximum[1])
    dz = max(0.0, left.minimum[2] - right.maximum[2], right.minimum[2] - left.maximum[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _min_disk_capsule_with_aabb(
    disks: Sequence[HorizontalDisk],
    disk_boxes: Sequence[Aabb],
    capsules: Sequence[Capsule],
    capsule_boxes: Sequence[Aabb],
) -> tuple[float, str, str]:
    pairs: list[tuple[float, HorizontalDisk, Capsule]] = []
    for disk, disk_box in zip(disks, disk_boxes):
        for capsule, cap_box in zip(capsules, capsule_boxes):
            sep = _aabb_unsigned_separation(disk_box, cap_box)
            pairs.append((sep, disk, capsule))
    pairs.sort(key=lambda item: item[0])
    best = float('inf')
    best_disk = pairs[0][1].name
    best_capsule = pairs[0][2].name
    for sep, disk, capsule in pairs:
        if sep >= best:
            continue
        gap = signed_distance_disk_capsule(disk, capsule)
        if gap < best:
            best = gap
            best_disk = disk.name
            best_capsule = capsule.name
    return best, best_disk, best_capsule


def _envelope(
    disks: Sequence[HorizontalDisk],
    capsules: Sequence[Capsule],
    *boxes: Aabb,
) -> dict[str, float]:
    parts = [box for box in boxes]
    parts.extend(horizontal_disk_aabb(disk) for disk in disks)
    parts.extend(capsule_aabb(capsule) for capsule in capsules)
    return aabb_extents(union_aabb(parts))
