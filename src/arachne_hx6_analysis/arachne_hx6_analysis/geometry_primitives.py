"""G2 geometric data types and closed-form distances.

Axis-aligned boxes, filled horizontal rotor disks, capsules, hex layout,
and disk-disk / disk-AABB signed distances. No certified iterative solver.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from arachne_hx6_analysis.model import (
    InvalidInputError,
    adjacent_motor_center_distance_m,
    min_motor_center_radius_m,
    rotor_envelope_diameter_m,
)

Vec3 = tuple[float, float, float]

_EPS = 1.0e-15



@dataclass(frozen=True)
class Aabb:
    """Axis-aligned box in metres, stored as min and max corners."""

    minimum: Vec3
    maximum: Vec3

    @property
    def center(self) -> Vec3:
        return (
            0.5 * (self.minimum[0] + self.maximum[0]),
            0.5 * (self.minimum[1] + self.maximum[1]),
            0.5 * (self.minimum[2] + self.maximum[2]),
        )

    @property
    def size(self) -> Vec3:
        return (
            self.maximum[0] - self.minimum[0],
            self.maximum[1] - self.minimum[1],
            self.maximum[2] - self.minimum[2],
        )


@dataclass(frozen=True)
class HorizontalDisk:
    """Filled horizontal rotor disk. Zero thickness, non-zero area."""

    name: str
    center: Vec3
    radius: float


@dataclass(frozen=True)
class Capsule:
    """Line segment with a finite radius. Conservative collision proxy."""

    name: str
    a: Vec3
    b: Vec3
    radius: float



def _require_finite_vec3(value: Sequence[float], name: str) -> Vec3:
    if len(value) != 3:
        raise InvalidInputError(f'{name} must have 3 components')
    coords: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise InvalidInputError(
                f'{name}[{index}] must be a real number, got {item!r}'
            )
        number = float(item)
        if not math.isfinite(number):
            raise InvalidInputError(f'{name}[{index}] must be finite')
        coords.append(number)
    return (coords[0], coords[1], coords[2])


def _clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _hypot3(a: Vec3) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _matmul(r: tuple[Vec3, Vec3, Vec3], v: Vec3) -> Vec3:
    return (
        r[0][0] * v[0] + r[0][1] * v[1] + r[0][2] * v[2],
        r[1][0] * v[0] + r[1][1] * v[1] + r[1][2] * v[2],
        r[2][0] * v[0] + r[2][1] * v[1] + r[2][2] * v[2],
    )


def _matmul3(
    a: tuple[Vec3, Vec3, Vec3],
    b: tuple[Vec3, Vec3, Vec3],
) -> tuple[Vec3, Vec3, Vec3]:
    rows: list[Vec3] = []
    for i in range(3):
        rows.append(
            (
                a[i][0] * b[0][0] + a[i][1] * b[1][0] + a[i][2] * b[2][0],
                a[i][0] * b[0][1] + a[i][1] * b[1][1] + a[i][2] * b[2][1],
                a[i][0] * b[0][2] + a[i][1] * b[1][2] + a[i][2] * b[2][2],
            )
        )
    return (rows[0], rows[1], rows[2])


def rot_z(angle_rad: float) -> tuple[Vec3, Vec3, Vec3]:
    """Right-handed rotation about +Z."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (
        (c, -s, 0.0),
        (s, c, 0.0),
        (0.0, 0.0, 1.0),
    )


def rot_y(angle_rad: float) -> tuple[Vec3, Vec3, Vec3]:
    """Right-handed rotation about +Y. +angle sends +X toward -Z."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (
        (c, 0.0, s),
        (0.0, 1.0, 0.0),
        (-s, 0.0, c),
    )


def box_from_center_size(center: Sequence[float], size: Sequence[float]) -> Aabb:
    """Build an AABB from a center and full side lengths."""
    c = _require_finite_vec3(center, 'center')
    s = _require_finite_vec3(size, 'size')
    if s[0] <= 0.0 or s[1] <= 0.0 or s[2] <= 0.0:
        raise InvalidInputError('box size components must be > 0')
    half = (0.5 * s[0], 0.5 * s[1], 0.5 * s[2])
    return Aabb(
        minimum=(c[0] - half[0], c[1] - half[1], c[2] - half[2]),
        maximum=(c[0] + half[0], c[1] + half[1], c[2] + half[2]),
    )


def union_aabb(boxes: Sequence[Aabb]) -> Aabb:
    """Axis-aligned union of one or more boxes."""
    if not boxes:
        raise InvalidInputError('union_aabb requires at least one box')
    xmin = min(box.minimum[0] for box in boxes)
    ymin = min(box.minimum[1] for box in boxes)
    zmin = min(box.minimum[2] for box in boxes)
    xmax = max(box.maximum[0] for box in boxes)
    ymax = max(box.maximum[1] for box in boxes)
    zmax = max(box.maximum[2] for box in boxes)
    return Aabb(minimum=(xmin, ymin, zmin), maximum=(xmax, ymax, zmax))


def aabb_extents(box: Aabb) -> dict[str, float]:
    """Length = X, width = Y, height = Z, in metres."""
    size = box.size
    return {
        'length_m': size[0],
        'width_m': size[1],
        'height_m': size[2],
        'min_x_m': box.minimum[0],
        'max_x_m': box.maximum[0],
        'min_y_m': box.minimum[1],
        'max_y_m': box.maximum[1],
        'min_z_m': box.minimum[2],
        'max_z_m': box.maximum[2],
    }


def horizontal_disk_aabb(disk: HorizontalDisk) -> Aabb:
    """AABB of a filled horizontal disk (zero thickness)."""
    cx, cy, cz = disk.center
    r = disk.radius
    return Aabb(
        minimum=(cx - r, cy - r, cz),
        maximum=(cx + r, cy + r, cz),
    )


def capsule_aabb(capsule: Capsule) -> Aabb:
    """AABB of a capsule: segment AABB expanded by radius."""
    r = capsule.radius
    xmin = min(capsule.a[0], capsule.b[0]) - r
    ymin = min(capsule.a[1], capsule.b[1]) - r
    zmin = min(capsule.a[2], capsule.b[2]) - r
    xmax = max(capsule.a[0], capsule.b[0]) + r
    ymax = max(capsule.a[1], capsule.b[1]) + r
    zmax = max(capsule.a[2], capsule.b[2]) + r
    return Aabb(minimum=(xmin, ymin, zmin), maximum=(xmax, ymax, zmax))


def motor_yaw_angles_rad(
    rotor_count: int,
    first_yaw_rad: float = math.pi / 6.0,
) -> tuple[float, ...]:
    """Evenly spaced X-hex yaw angles. G1 first arm is +30 deg."""
    if not isinstance(rotor_count, int) or isinstance(rotor_count, bool):
        raise InvalidInputError(
            f'rotor_count must be an integer, got {rotor_count!r}'
        )
    if rotor_count < 2:
        raise InvalidInputError(
            f'rotor_count must be an integer >= 2, got {rotor_count}'
        )
    step = 2.0 * math.pi / float(rotor_count)
    return tuple(first_yaw_rad + step * float(index) for index in range(rotor_count))


def hexarotor_disk_centers(
    motor_center_radius_m: float,
    rotor_plane_z_m: float,
    rotor_count: int,
    first_yaw_rad: float = math.pi / 6.0,
) -> tuple[Vec3, ...]:
    """Motor / disk centers on a common horizontal circle."""
    if not isinstance(motor_center_radius_m, (int, float)) or isinstance(
        motor_center_radius_m, bool
    ):
        raise InvalidInputError(
            'motor_center_radius_m must be a real number, '
            f'got {motor_center_radius_m!r}'
        )
    if not math.isfinite(motor_center_radius_m) or motor_center_radius_m <= 0.0:
        raise InvalidInputError(
            'motor_center_radius_m must be finite and > 0, '
            f'got {motor_center_radius_m}'
        )
    if not isinstance(rotor_plane_z_m, (int, float)) or isinstance(
        rotor_plane_z_m, bool
    ):
        raise InvalidInputError(
            f'rotor_plane_z_m must be a real number, got {rotor_plane_z_m!r}'
        )
    if not math.isfinite(rotor_plane_z_m):
        raise InvalidInputError(
            f'rotor_plane_z_m must be finite, got {rotor_plane_z_m}'
        )
    yaws = motor_yaw_angles_rad(rotor_count, first_yaw_rad)
    return tuple(
        (
            motor_center_radius_m * math.cos(yaw),
            motor_center_radius_m * math.sin(yaw),
            rotor_plane_z_m,
        )
        for yaw in yaws
    )


def make_rotor_disks(
    motor_center_radius_m: float,
    diameter_m: float,
    rotor_plane_z_m: float,
    rotor_count: int,
    first_yaw_rad: float = math.pi / 6.0,
) -> tuple[HorizontalDisk, ...]:
    """Six (or n) filled rotor disks of equal diameter."""
    if not isinstance(diameter_m, (int, float)) or isinstance(diameter_m, bool):
        raise InvalidInputError(
            f'diameter_m must be a real number, got {diameter_m!r}'
        )
    if not math.isfinite(diameter_m) or diameter_m <= 0.0:
        raise InvalidInputError(
            f'diameter_m must be finite and > 0, got {diameter_m}'
        )
    radius = 0.5 * diameter_m
    centers = hexarotor_disk_centers(
        motor_center_radius_m, rotor_plane_z_m, rotor_count, first_yaw_rad
    )
    return tuple(
        HorizontalDisk(name=f'hex_{index + 1}', center=center, radius=radius)
        for index, center in enumerate(centers)
    )


def adjacent_rotor_tip_clearance_m(
    motor_center_radius_m: float,
    diameter_m: float,
    rotor_count: int,
) -> float:
    """Net gap between adjacent equal disks: d_adj - D. Negative = overlap."""
    adjacent = adjacent_motor_center_distance_m(motor_center_radius_m, rotor_count)
    if not isinstance(diameter_m, (int, float)) or isinstance(diameter_m, bool):
        raise InvalidInputError(
            f'diameter_m must be a real number, got {diameter_m!r}'
        )
    if not math.isfinite(diameter_m) or diameter_m <= 0.0:
        raise InvalidInputError(
            f'diameter_m must be finite and > 0, got {diameter_m}'
        )
    return adjacent - diameter_m


def signed_distance_horizontal_disks(
    a: HorizontalDisk,
    b: HorizontalDisk,
) -> float:
    """Signed gap between two filled horizontal disks.

    Positive: separated. Zero: touching. Negative: overlapping.
    Coplanar disks reduce to XY center distance minus both radii. If the
    planes differ, overlapping XY projections separate only along Z.
    """
    dx = a.center[0] - b.center[0]
    dy = a.center[1] - b.center[1]
    dz = a.center[2] - b.center[2]
    xy = math.hypot(dx, dy)
    xy_signed = xy - a.radius - b.radius
    z_abs = abs(dz)
    if xy_signed > 0.0 and z_abs > 0.0:
        return math.hypot(xy_signed, z_abs)
    if xy_signed > 0.0:
        return xy_signed
    if z_abs > 0.0:
        return z_abs
    return xy_signed


def min_pairwise_disk_clearance_m(disks: Sequence[HorizontalDisk]) -> float:
    """Minimum signed clearance over unique disk pairs."""
    if len(disks) < 2:
        raise InvalidInputError('need at least two disks')
    best = float('inf')
    for i, left in enumerate(disks):
        for right in disks[i + 1:]:
            gap = signed_distance_horizontal_disks(left, right)
            if gap < best:
                best = gap
    return best


def _xy_signed_distance_circle_aabb(
    cx: float,
    cy: float,
    radius: float,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
) -> float:
    """Signed distance from a filled 2D disk to an axis-aligned rectangle."""
    qx = _clamp(cx, xmin, xmax)
    qy = _clamp(cy, ymin, ymax)
    dx = cx - qx
    dy = cy - qy
    outside = math.hypot(dx, dy)
    if outside > 0.0:
        return outside - radius
    inset_x = min(cx - xmin, xmax - cx)
    inset_y = min(cy - ymin, ymax - cy)
    return -(radius + min(inset_x, inset_y))


def signed_distance_disk_aabb(disk: HorizontalDisk, box: Aabb) -> float:
    """Signed distance from a filled horizontal disk to an AABB.

    Positive: separated. Negative: the disk set intersects the box.
    """
    cx, cy, cz = disk.center
    xmin, ymin, zmin = box.minimum
    xmax, ymax, zmax = box.maximum
    xy_signed = _xy_signed_distance_circle_aabb(
        cx, cy, disk.radius, xmin, xmax, ymin, ymax
    )
    if cz < zmin:
        z_signed = zmin - cz
    elif cz > zmax:
        z_signed = cz - zmax
    else:
        z_signed = -min(cz - zmin, zmax - cz)
    if xy_signed > 0.0 and z_signed > 0.0:
        return math.hypot(xy_signed, z_signed)
    if xy_signed > 0.0:
        return xy_signed
    if z_signed > 0.0:
        return z_signed
    return max(xy_signed, z_signed)


def point_to_horizontal_disk_distance(point: Vec3, disk: HorizontalDisk) -> float:
    """Unsigned distance from a point to a filled horizontal disk."""
    dz = point[2] - disk.center[2]
    d_xy = math.hypot(point[0] - disk.center[0], point[1] - disk.center[1])
    if d_xy <= disk.radius:
        return abs(dz)
    return math.hypot(d_xy - disk.radius, dz)


def _point_to_disk_closest(point: Vec3, disk: HorizontalDisk) -> Vec3:
    cx, cy, cz = disk.center
    dx = point[0] - cx
    dy = point[1] - cy
    rho = math.hypot(dx, dy)
    if rho <= disk.radius:
        return (point[0], point[1], cz)
    scale = disk.radius / rho
    return (cx + dx * scale, cy + dy * scale, cz)



def min_disk_box_clearance_m(
    disks: Sequence[HorizontalDisk],
    box: Aabb,
) -> tuple[float, str]:
    """Minimum signed disk-AABB gap and the disk name that attains it."""
    if not disks:
        raise InvalidInputError('need at least one disk')
    best_name = disks[0].name
    best_gap = signed_distance_disk_aabb(disks[0], box)
    for disk in disks[1:]:
        gap = signed_distance_disk_aabb(disk, box)
        if gap < best_gap:
            best_gap = gap
            best_name = disk.name
    return best_gap, best_name



def hex_layout_metrics(
    motor_center_radius_m: float,
    diameter_m: float,
    rotor_count: int,
    min_tip_clearance_m: float,
) -> dict[str, float]:
    """Derived hexarotor spacing numbers reused from G1.5 public formulas."""
    adjacent = adjacent_motor_center_distance_m(motor_center_radius_m, rotor_count)
    tip = adjacent_rotor_tip_clearance_m(
        motor_center_radius_m, diameter_m, rotor_count
    )
    min_r = min_motor_center_radius_m(
        diameter_m, min_tip_clearance_m, rotor_count
    )
    envelope = rotor_envelope_diameter_m(motor_center_radius_m, diameter_m)
    return {
        'adjacent_motor_center_m': adjacent,
        'adjacent_rotor_tip_clearance_m': tip,
        'min_motor_center_radius_m': min_r,
        'rotor_envelope_diameter_m': envelope,
    }
