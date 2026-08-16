"""Coxa / femur / tibia capsule kinematics matching G1 leg.xacro.

Rigid transforms and conservative capsule proxies. Joint chain: coxa about
hip Z, femur then tibia about +Y, positive femur/tibia distal-down.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from arachne_hx6_analysis.geometry_primitives import (
    Capsule,
    Vec3,
    _add,
    _matmul,
    _matmul3,
    rot_y,
    rot_z,
)
from arachne_hx6_analysis.model import InvalidInputError

@dataclass(frozen=True)
class Transform:
    """Rigid transform: p_world = R * p_local + t."""

    rotation: tuple[Vec3, Vec3, Vec3]
    translation: Vec3

    def apply(self, point: Vec3) -> Vec3:
        return _add(_matmul(self.rotation, point), self.translation)

    def compose(self, other: 'Transform') -> 'Transform':
        return Transform(
            rotation=_matmul3(self.rotation, other.rotation),
            translation=_add(self.translation, _matmul(self.rotation, other.translation)),
        )


def identity_transform() -> Transform:
    return Transform(
        rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        translation=(0.0, 0.0, 0.0),
    )


@dataclass(frozen=True)
class LegMount:
    """G1 hexapod hip mount in base_link."""

    prefix: str
    x_m: float
    y_m: float
    z_m: float
    yaw_rad: float


@dataclass(frozen=True)
class LegSegmentLengths:
    coxa_m: float
    femur_m: float
    tibia_m: float


@dataclass(frozen=True)
class LegSegmentRadii:
    coxa_m: float
    femur_m: float
    tibia_m: float
    foot_m: float


def box_cross_section_capsule_radius_m(width_m: float, height_m: float) -> float:
    """Circumscribed-circle radius of a rectangular cross-section."""
    if width_m <= 0.0 or height_m <= 0.0:
        raise InvalidInputError('box cross-section sizes must be > 0')
    return 0.5 * math.hypot(width_m, height_m)


def leg_segment_capsules(
    mount: LegMount,
    lengths: LegSegmentLengths,
    radii: LegSegmentRadii,
    coxa_rad: float,
    femur_rad: float,
    tibia_rad: float,
) -> tuple[Capsule, ...]:
    """World-frame capsules for coxa, femur, tibia, and a foot sphere.

    Joint chain matches G1 ``leg.xacro``: coxa about hip Z, femur then tibia
    about +Y, with positive femur/tibia sending the distal segment downward.
    """
    hip = Transform(rotation=rot_z(mount.yaw_rad), translation=(mount.x_m, mount.y_m, mount.z_m))
    coxa_joint = hip.compose(
        Transform(rotation=rot_z(coxa_rad), translation=(0.0, 0.0, 0.0))
    )
    coxa_a = coxa_joint.translation
    coxa_b = coxa_joint.apply((lengths.coxa_m, 0.0, 0.0))
    femur_joint = coxa_joint.compose(
        Transform(rotation=rot_y(femur_rad), translation=(lengths.coxa_m, 0.0, 0.0))
    )
    femur_a = femur_joint.translation
    femur_b = femur_joint.apply((lengths.femur_m, 0.0, 0.0))
    tibia_joint = femur_joint.compose(
        Transform(rotation=rot_y(tibia_rad), translation=(lengths.femur_m, 0.0, 0.0))
    )
    tibia_a = tibia_joint.translation
    tibia_b = tibia_joint.apply((lengths.tibia_m, 0.0, 0.0))
    return (
        Capsule(
            name=f'{mount.prefix}_coxa',
            a=coxa_a,
            b=coxa_b,
            radius=radii.coxa_m,
        ),
        Capsule(
            name=f'{mount.prefix}_femur',
            a=femur_a,
            b=femur_b,
            radius=radii.femur_m,
        ),
        Capsule(
            name=f'{mount.prefix}_tibia',
            a=tibia_a,
            b=tibia_b,
            radius=radii.tibia_m,
        ),
        Capsule(
            name=f'{mount.prefix}_foot',
            a=tibia_b,
            b=tibia_b,
            radius=radii.foot_m,
        ),
    )
