"""Leg joint-pose validation, linear path sampling, and capsule kinematics.

Joint names and limits come from the G1 baseline. Capsules reuse the
geometry façade; this module does not reimplement forward kinematics.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from arachne_hx6_analysis.architecture_types import (
    REQUIRED_JOINT_NAMES,
    G1Baseline,
)
from arachne_hx6_analysis.geometry import (
    Capsule,
    LegSegmentLengths,
    LegSegmentRadii,
    box_cross_section_capsule_radius_m,
    leg_segment_capsules,
)
from arachne_hx6_analysis.inputs import as_float
from arachne_hx6_analysis.model import InvalidInputError

def validate_joint_pose(
    joints: Mapping[str, float],
    limits: Mapping[str, tuple[float, float]],
    path: str,
) -> dict[str, float]:
    """Require exactly the 18 G1 revolute joints, each strictly inside limits."""
    if not isinstance(joints, Mapping):
        raise InvalidInputError(f'{path} must be a mapping')
    names = list(joints.keys())
    if len(names) != len(set(names)):
        raise InvalidInputError(f'{path} has duplicate joint names')
    required = set(REQUIRED_JOINT_NAMES)
    got = set(names)
    missing = sorted(required - got)
    extra = sorted(got - required)
    if missing:
        raise InvalidInputError(f'{path} missing joints: {missing}')
    if extra:
        raise InvalidInputError(f'{path} unknown joints: {extra}')
    if len(names) != 18:
        raise InvalidInputError(
            f'{path} must contain exactly 18 joints, got {len(names)}'
        )
    validated: dict[str, float] = {}
    for name in REQUIRED_JOINT_NAMES:
        value = as_float(joints[name], f'{path}.{name}')
        lower, upper = limits[name]
        if not (lower < value < upper):
            raise InvalidInputError(
                f'{path}.{name}={value} is outside URDF limits ({lower}, {upper})'
            )
        validated[name] = value
    return validated


def interpolate_joint_path(
    start: Mapping[str, float],
    end: Mapping[str, float],
    sample_count: int,
) -> tuple[dict[str, float], ...]:
    """Linear joint-space samples, including both endpoints."""
    if (
        not isinstance(sample_count, int)
        or isinstance(sample_count, bool)
        or sample_count < 2
    ):
        raise InvalidInputError(
            f'sample_count must be an integer >= 2, got {sample_count!r}'
        )
    denom = float(sample_count - 1)
    poses: list[dict[str, float]] = []
    for index in range(sample_count):
        fraction = float(index) / denom
        pose = {
            name: (1.0 - fraction) * start[name] + fraction * end[name]
            for name in REQUIRED_JOINT_NAMES
        }
        poses.append(pose)
    return tuple(poses)



def _segment_lengths(baseline: G1Baseline) -> LegSegmentLengths:
    return LegSegmentLengths(
        coxa_m=baseline.coxa_length_m,
        femur_m=baseline.femur_length_m,
        tibia_m=baseline.tibia_length_m,
    )


def _segment_radii(baseline: G1Baseline) -> LegSegmentRadii:
    return LegSegmentRadii(
        coxa_m=baseline.coxa_radius_m,
        femur_m=box_cross_section_capsule_radius_m(
            baseline.femur_width_m, baseline.femur_height_m
        ),
        tibia_m=box_cross_section_capsule_radius_m(
            baseline.tibia_width_m, baseline.tibia_height_m
        ),
        foot_m=baseline.foot_radius_m,
    )


def _capsules_for_pose(
    pose: Mapping[str, float],
    baseline: G1Baseline,
) -> tuple[Capsule, ...]:
    lengths = _segment_lengths(baseline)
    radii = _segment_radii(baseline)
    capsules: list[Capsule] = []
    for mount in baseline.mounts:
        capsules.extend(
            leg_segment_capsules(
                mount,
                lengths,
                radii,
                pose[f'{mount.prefix}_coxa_joint'],
                pose[f'{mount.prefix}_femur_joint'],
                pose[f'{mount.prefix}_tibia_joint'],
            )
        )
    return tuple(capsules)
