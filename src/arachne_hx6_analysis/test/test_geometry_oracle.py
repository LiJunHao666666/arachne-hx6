"""Independent geometry oracles for G2. Do not copy production expected values."""

from __future__ import annotations

import math
import random

import pytest

from arachne_hx6_analysis.geometry import (
    CONVERGENCE_CERTIFIED,
    GEOMETRY_SOLVER_TOLERANCE_M,
    Capsule,
    HorizontalDisk,
    LegMount,
    LegSegmentLengths,
    LegSegmentRadii,
    adjacent_rotor_tip_clearance_m,
    box_from_center_size,
    capsule_aabb,
    hexarotor_disk_centers,
    horizontal_disk_aabb,
    leg_segment_capsules,
    make_rotor_disks,
    motor_yaw_angles_rad,
    signed_distance_disk_aabb,
    signed_distance_disk_capsule,
    solve_segment_to_horizontal_disk_distance,
    union_aabb,
)
from arachne_hx6_analysis.model import (
    AnalysisError,
    GeometryConvergenceError,
    InvalidInputError,
)

ABS_TOL = 1.0e-6
CANONICAL_TOL = 1.0e-12
ORACLE_SAMPLES = 4001
RNG_SEED = 20260815


def _oracle_point_to_disk(point, center, radius):
    """Closest-point oracle: project onto the filled disk in the plane z=cz."""
    cx, cy, cz = center
    dx = point[0] - cx
    dy = point[1] - cy
    rho = math.hypot(dx, dy)
    if rho <= radius:
        closest = (cx + dx, cy + dy, cz)
    else:
        scale = radius / rho
        closest = (cx + dx * scale, cy + dy * scale, cz)
    return math.dist(point, closest)


def _oracle_segment_to_disk(a, b, center, radius, samples=ORACLE_SAMPLES):
    """Dense parameter sampling plus the plane-hit sample."""
    best = float('inf')
    denom = float(samples - 1)
    for index in range(samples):
        t = float(index) / denom
        point = (
            a[0] + t * (b[0] - a[0]),
            a[1] + t * (b[1] - a[1]),
            a[2] + t * (b[2] - a[2]),
        )
        best = min(best, _oracle_point_to_disk(point, center, radius))
    dz = b[2] - a[2]
    if abs(dz) > 1.0e-15:
        t_plane = (center[2] - a[2]) / dz
        if 0.0 <= t_plane <= 1.0:
            point = (
                a[0] + t_plane * (b[0] - a[0]),
                a[1] + t_plane * (b[1] - a[1]),
                a[2] + t_plane * (b[2] - a[2]),
            )
            best = min(best, _oracle_point_to_disk(point, center, radius))
    return best


def _sampling_error_bound(a, b, samples=ORACLE_SAMPLES):
    length = math.dist(a, b)
    return length / (2.0 * float(samples - 1)) + 1.0e-12


def _assert_finite(value):
    assert isinstance(value, float)
    assert math.isfinite(value)
    assert not math.isnan(value)


def _assert_certified(solved):
    _assert_finite(solved.distance_m)
    _assert_finite(solved.lower_bound_m)
    _assert_finite(solved.upper_bound_m)
    _assert_finite(solved.certified_error_bound_m)
    assert solved.convergence_status == CONVERGENCE_CERTIFIED
    assert solved.upper_bound_m - solved.lower_bound_m <= (
        solved.solver_tolerance_m
    )
    assert solved.certified_error_bound_m == pytest.approx(
        solved.upper_bound_m - solved.lower_bound_m, abs=0.0
    )
    assert solved.certified_error_bound_m <= solved.solver_tolerance_m
    assert solved.distance_m == pytest.approx(solved.upper_bound_m, abs=0.0)
    assert solved.evaluations_used >= 0


def _compare_segment_disk(a, b, disk, extra_tol=0.0, tol=None):
    solved = solve_segment_to_horizontal_disk_distance(a, b, disk, tol=tol)
    _assert_certified(solved)
    actual = signed_distance_disk_capsule(
        disk, Capsule('seg', a, b, 0.0)
    )
    _assert_finite(actual)
    assert actual == pytest.approx(solved.distance_m, abs=0.0)
    sampled = _oracle_segment_to_disk(a, b, disk.center, disk.radius)
    bound = _sampling_error_bound(a, b) + extra_tol
    assert actual <= sampled + ABS_TOL
    assert sampled - actual <= bound + ABS_TOL
    return actual


def _oracle_signed_circle_rect(cx, cy, radius, xmin, xmax, ymin, ymax):
    """Independent 9-region signed distance from a filled circle to a rectangle."""
    if xmin <= cx <= xmax and ymin <= cy <= ymax:
        inset = min(cx - xmin, xmax - cx, cy - ymin, ymax - cy)
        return -(radius + inset)
    if xmin <= cx <= xmax:
        if cy < ymin:
            return (ymin - cy) - radius
        return (cy - ymax) - radius
    if ymin <= cy <= ymax:
        if cx < xmin:
            return (xmin - cx) - radius
        return (cx - xmax) - radius
    if cx < xmin and cy < ymin:
        return math.hypot(xmin - cx, ymin - cy) - radius
    if cx > xmax and cy < ymin:
        return math.hypot(cx - xmax, ymin - cy) - radius
    if cx < xmin and cy > ymax:
        return math.hypot(xmin - cx, cy - ymax) - radius
    return math.hypot(cx - xmax, cy - ymax) - radius


def _oracle_signed_disk_aabb(disk, box):
    """Product-set combination written independently of production code."""
    cx, cy, cz = disk.center
    xmin, ymin, zmin = box.minimum
    xmax, ymax, zmax = box.maximum
    xy = _oracle_signed_circle_rect(cx, cy, disk.radius, xmin, xmax, ymin, ymax)
    if cz < zmin:
        z_signed = zmin - cz
    elif cz > zmax:
        z_signed = cz - zmax
    else:
        z_signed = -min(cz - zmin, zmax - cz)
    if xy > 0.0 and z_signed > 0.0:
        return math.hypot(xy, z_signed)
    if xy > 0.0:
        return xy
    if z_signed > 0.0:
        return z_signed
    return max(xy, z_signed)


def _oracle_point_aabb_unsigned(point, box):
    dx = max(box.minimum[0] - point[0], 0.0, point[0] - box.maximum[0])
    dy = max(box.minimum[1] - point[1], 0.0, point[1] - box.maximum[1])
    dz = max(box.minimum[2] - point[2], 0.0, point[2] - box.maximum[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _oracle_disk_aabb_sampled_unsigned(disk, box, rings=48, rays=96):
    """Upper bound via polar samples of the filled disk."""
    cx, cy, cz = disk.center
    best = _oracle_point_aabb_unsigned((cx, cy, cz), box)
    for ring in range(rings + 1):
        rho = disk.radius * float(ring) / float(rings)
        count = 1 if ring == 0 else rays
        for ray in range(count):
            ang = 2.0 * math.pi * float(ray) / float(count)
            point = (cx + rho * math.cos(ang), cy + rho * math.sin(ang), cz)
            best = min(best, _oracle_point_aabb_unsigned(point, box))
    return best


def _matmul3(left, right):
    rows = []
    for i in range(3):
        rows.append(
            (
                left[i][0] * right[0][0]
                + left[i][1] * right[1][0]
                + left[i][2] * right[2][0],
                left[i][0] * right[0][1]
                + left[i][1] * right[1][1]
                + left[i][2] * right[2][1],
                left[i][0] * right[0][2]
                + left[i][1] * right[1][2]
                + left[i][2] * right[2][2],
            )
        )
    return (rows[0], rows[1], rows[2])


def _rot_z(angle):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (cosine, -sine, 0.0),
        (sine, cosine, 0.0),
        (0.0, 0.0, 1.0),
    )


def _rot_y(angle):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (cosine, 0.0, sine),
        (0.0, 1.0, 0.0),
        (-sine, 0.0, cosine),
    )


def _oracle_fk_points(mount, lengths, coxa, femur, tibia):
    """Independent 4x3 FK using T = Trans * RotZ(yaw+coxa) * RotY(femur) * RotY(tibia)."""
    hip = (mount.x_m, mount.y_m, mount.z_m)
    rotation = _rot_z(mount.yaw_rad + coxa)
    coxa_end = (
        hip[0] + rotation[0][0] * lengths.coxa_m,
        hip[1] + rotation[1][0] * lengths.coxa_m,
        hip[2] + rotation[2][0] * lengths.coxa_m,
    )
    rotation = _matmul3(rotation, _rot_y(femur))
    femur_end = (
        coxa_end[0] + rotation[0][0] * lengths.femur_m,
        coxa_end[1] + rotation[1][0] * lengths.femur_m,
        coxa_end[2] + rotation[2][0] * lengths.femur_m,
    )
    rotation = _matmul3(rotation, _rot_y(tibia))
    tibia_end = (
        femur_end[0] + rotation[0][0] * lengths.tibia_m,
        femur_end[1] + rotation[1][0] * lengths.tibia_m,
        femur_end[2] + rotation[2][0] * lengths.tibia_m,
    )
    return hip, coxa_end, femur_end, tibia_end


def test_disk_above_segment_canonical():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    actual = _compare_segment_disk((0.0, 0.0, 2.0), (0.0, 0.0, 3.0), disk)
    assert actual == pytest.approx(2.0, abs=CANONICAL_TOL)


def test_disk_plane_intersection_outside_then_along_plane():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    actual = _compare_segment_disk((2.0, 0.0, 0.0), (3.0, 0.0, 0.0), disk)
    assert actual == pytest.approx(1.0, abs=CANONICAL_TOL)


def test_segment_pierces_disk():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    actual = _compare_segment_disk((0.0, 0.0, -1.0), (0.0, 0.0, 1.0), disk)
    assert actual == pytest.approx(0.0, abs=CANONICAL_TOL)


def test_closest_point_is_segment_endpoint():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    actual = _compare_segment_disk((3.0, 0.0, 4.0), (8.0, 0.0, 9.0), disk)
    expected = math.hypot(3.0 - 1.0, 4.0)
    assert actual == pytest.approx(expected, abs=CANONICAL_TOL)


def test_closest_point_is_disk_rim():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    actual = _compare_segment_disk((3.0, 0.0, 1.0), (3.0, 0.0, -1.0), disk)
    assert actual == pytest.approx(2.0, abs=CANONICAL_TOL)


def test_fully_separated_oblique_segment():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 0.5)
    actual = _compare_segment_disk((4.0, 3.0, 2.0), (5.0, 4.0, 3.0), disk)
    assert actual > 0.5


def test_capsule_radius_makes_net_gap_negative():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    unsigned = _compare_segment_disk((0.0, 0.0, 0.2), (0.0, 0.0, 0.4), disk)
    solved = solve_segment_to_horizontal_disk_distance(
        (0.0, 0.0, 0.2), (0.0, 0.0, 0.4), disk
    )
    _assert_certified(solved)
    signed = signed_distance_disk_capsule(
        disk, Capsule('fat', (0.0, 0.0, 0.2), (0.0, 0.0, 0.4), 0.5)
    )
    _assert_finite(signed)
    assert unsigned == pytest.approx(0.2, abs=CANONICAL_TOL)
    assert signed == pytest.approx(solved.distance_m - 0.5, abs=0.0)
    assert signed == pytest.approx(-0.3, abs=CANONICAL_TOL)
    assert signed < 0.0
    assert solved.distance_m > 0.0


def test_random_segment_disk_matches_sampling_oracle():
    rng = random.Random(RNG_SEED)
    disk = HorizontalDisk('d', (0.1, -0.2, 0.3), 0.75)
    for _ in range(40):
        a = (rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0))
        b = (rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0), rng.uniform(-2.0, 2.0))
        _compare_segment_disk(a, b, disk)


def test_disk_aabb_above_face():
    disk = HorizontalDisk('d', (0.0, 0.0, 2.0), 1.0)
    box = box_from_center_size((0.0, 0.0, 0.0), (2.0, 2.0, 2.0))
    actual = signed_distance_disk_aabb(disk, box)
    expected = _oracle_signed_disk_aabb(disk, box)
    _assert_finite(actual)
    assert actual == pytest.approx(1.0, abs=CANONICAL_TOL)
    assert actual == pytest.approx(expected, abs=CANONICAL_TOL)


def test_disk_aabb_side_and_intersection_and_corner():
    box = box_from_center_size((0.0, 0.0, 0.0), (2.0, 2.0, 2.0))
    side = HorizontalDisk('s', (3.0, 0.0, 0.0), 1.0)
    hit = HorizontalDisk('h', (0.0, 0.0, 0.0), 1.0)
    corner = HorizontalDisk('c', (3.0, 3.0, 3.0), 0.5)
    for disk, expected_sign in ((side, 1), (hit, -1), (corner, 1)):
        actual = signed_distance_disk_aabb(disk, box)
        oracle = _oracle_signed_disk_aabb(disk, box)
        _assert_finite(actual)
        assert actual == pytest.approx(oracle, abs=CANONICAL_TOL)
        if expected_sign > 0:
            assert actual > 0.0
        else:
            assert actual < 0.0
    sampled = _oracle_disk_aabb_sampled_unsigned(corner, box)
    unsigned_actual = max(signed_distance_disk_aabb(corner, box), 0.0)
    assert unsigned_actual <= sampled + ABS_TOL


def test_random_disk_aabb_matches_independent_oracle():
    rng = random.Random(RNG_SEED)
    box = box_from_center_size((0.0, 0.0, 0.0), (1.0, 2.0, 0.8))
    for _ in range(40):
        disk = HorizontalDisk(
            'r',
            (rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0)),
            rng.uniform(0.05, 1.5),
        )
        actual = signed_distance_disk_aabb(disk, box)
        oracle = _oracle_signed_disk_aabb(disk, box)
        _assert_finite(actual)
        assert actual == pytest.approx(oracle, abs=1.0e-9)
        sampled = _oracle_disk_aabb_sampled_unsigned(disk, box)
        unsigned_actual = max(actual, 0.0)
        assert unsigned_actual <= sampled + 1.0e-4


def test_envelope_aabb_matches_independent_extrema():
    disks = make_rotor_disks(0.30, 0.12, 0.068, 6, math.pi / 6.0)
    box = box_from_center_size((0.0, 0.0, 0.0), (0.40, 0.30, 0.10))
    capsule = Capsule('leg', (0.16, 0.15, -0.02), (0.30, 0.30, -0.20), 0.02)
    parts = [box, horizontal_disk_aabb(disks[0]), capsule_aabb(capsule)]
    for disk in disks[1:]:
        parts.append(horizontal_disk_aabb(disk))
    union = union_aabb(parts)
    xs = [box.minimum[0], box.maximum[0]]
    ys = [box.minimum[1], box.maximum[1]]
    zs = [box.minimum[2], box.maximum[2]]
    for disk in disks:
        xs.extend([disk.center[0] - disk.radius, disk.center[0] + disk.radius])
        ys.extend([disk.center[1] - disk.radius, disk.center[1] + disk.radius])
        zs.append(disk.center[2])
    for end in (capsule.a, capsule.b):
        xs.extend([end[0] - capsule.radius, end[0] + capsule.radius])
        ys.extend([end[1] - capsule.radius, end[1] + capsule.radius])
        zs.extend([end[2] - capsule.radius, end[2] + capsule.radius])
    assert union.minimum[0] == pytest.approx(min(xs), abs=CANONICAL_TOL)
    assert union.maximum[0] == pytest.approx(max(xs), abs=CANONICAL_TOL)
    assert union.minimum[1] == pytest.approx(min(ys), abs=CANONICAL_TOL)
    assert union.maximum[1] == pytest.approx(max(ys), abs=CANONICAL_TOL)
    assert union.minimum[2] == pytest.approx(min(zs), abs=CANONICAL_TOL)
    assert union.maximum[2] == pytest.approx(max(zs), abs=CANONICAL_TOL)


def test_tip_clearance_monotonic_in_diameter_and_radius():
    radius = 0.30
    diameters = (0.10, 0.15, 0.20, 0.25)
    gaps_by_d = [
        adjacent_rotor_tip_clearance_m(radius, diameter, 6)
        for diameter in diameters
    ]
    for left, right in zip(gaps_by_d, gaps_by_d[1:]):
        _assert_finite(left)
        _assert_finite(right)
        assert right <= left + 1.0e-15
    diameter = 0.20
    radii = (0.30, 0.325, 0.35, 0.40)
    gaps_by_r = [
        adjacent_rotor_tip_clearance_m(item, diameter, 6) for item in radii
    ]
    for left, right in zip(gaps_by_r, gaps_by_r[1:]):
        _assert_finite(left)
        _assert_finite(right)
        assert right >= left - 1.0e-15


def test_hexarotor_sixty_degree_rotational_symmetry():
    radius = 0.30
    z_plane = 0.068
    centers = hexarotor_disk_centers(radius, z_plane, 6, math.pi / 6.0)
    yaws = motor_yaw_angles_rad(6, math.pi / 6.0)
    assert len(centers) == 6
    step = math.pi / 3.0
    cosine = math.cos(step)
    sine = math.sin(step)
    rotated = tuple(
        (cosine * x - sine * y, sine * x + cosine * y, z)
        for x, y, z in centers
    )
    for point in rotated:
        matched = False
        for original in centers:
            if math.dist(point, original) <= 1.0e-12:
                matched = True
                break
        assert matched, f'rotated center {point} is not in the original set'
    adjacent = [
        math.dist(centers[index], centers[(index + 1) % 6])
        for index in range(6)
    ]
    for gap in adjacent:
        assert gap == pytest.approx(radius, abs=1.0e-12)
    for index, yaw in enumerate(yaws):
        expected = math.pi / 6.0 + index * (2.0 * math.pi / 6.0)
        assert yaw == pytest.approx(expected, abs=1.0e-15)


def test_leg_fk_matches_independent_urdf_chain():
    mount = LegMount('lf', 0.16, 0.15, -0.015, math.pi / 4.0)
    lengths = LegSegmentLengths(0.060, 0.125, 0.145)
    radii = LegSegmentRadii(0.016, 0.016, 0.013, 0.015)
    coxa, femur, tibia = -0.30, 0.50, 1.00
    capsules = leg_segment_capsules(mount, lengths, radii, coxa, femur, tibia)
    hip, coxa_end, femur_end, tibia_end = _oracle_fk_points(
        mount, lengths, coxa, femur, tibia
    )
    assert capsules[0].a == pytest.approx(hip, abs=1.0e-12)
    assert capsules[0].b == pytest.approx(coxa_end, abs=1.0e-12)
    assert capsules[1].a == pytest.approx(coxa_end, abs=1.0e-12)
    assert capsules[1].b == pytest.approx(femur_end, abs=1.0e-12)
    assert capsules[2].a == pytest.approx(femur_end, abs=1.0e-12)
    assert capsules[2].b == pytest.approx(tibia_end, abs=1.0e-12)
    assert capsules[3].a == pytest.approx(tibia_end, abs=1.0e-12)
    assert capsules[3].b == pytest.approx(tibia_end, abs=1.0e-12)


def test_positive_femur_sends_distal_segment_down():
    mount = LegMount('lm', 0.0, 0.15, 0.0, math.pi / 2.0)
    lengths = LegSegmentLengths(0.060, 0.125, 0.145)
    radii = LegSegmentRadii(0.01, 0.01, 0.01, 0.01)
    zero = leg_segment_capsules(mount, lengths, radii, 0.0, 0.0, 0.0)
    plus = leg_segment_capsules(mount, lengths, radii, 0.0, 0.4, 0.0)
    assert plus[1].b[2] < zero[1].b[2]


def test_left_right_mount_yaw_mirror():
    lengths = LegSegmentLengths(0.060, 0.125, 0.145)
    radii = LegSegmentRadii(0.016, 0.016, 0.013, 0.015)
    left = LegMount('lf', 0.16, 0.15, -0.015, math.pi / 4.0)
    right = LegMount('rf', 0.16, -0.15, -0.015, -math.pi / 4.0)
    coxa, femur, tibia = 0.2, 0.4, 0.6
    left_caps = leg_segment_capsules(left, lengths, radii, coxa, femur, tibia)
    right_caps = leg_segment_capsules(right, lengths, radii, -coxa, femur, tibia)
    for left_cap, right_cap in zip(left_caps, right_caps):
        for left_pt, right_pt in ((left_cap.a, right_cap.a), (left_cap.b, right_cap.b)):
            assert left_pt[0] == pytest.approx(right_pt[0], abs=1.0e-12)
            assert left_pt[1] == pytest.approx(-right_pt[1], abs=1.0e-12)
            assert left_pt[2] == pytest.approx(right_pt[2], abs=1.0e-12)


def test_segment_disk_rejects_non_finite_radius():
    disk = HorizontalDisk('bad', (0.0, 0.0, 0.0), float('nan'))
    with pytest.raises(InvalidInputError, match='radius'):
        signed_distance_disk_capsule(
            disk, Capsule('s', (0.0, 0.0, 1.0), (0.0, 0.0, 2.0), 0.1)
        )


def test_regular_case_converges_with_certified_gap():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (0.0, 0.0, 2.0)
    b = (0.0, 0.0, 3.0)
    solved = solve_segment_to_horizontal_disk_distance(a, b, disk)
    _assert_certified(solved)
    expected = _oracle_point_to_disk(a, disk.center, disk.radius)
    assert solved.distance_m == pytest.approx(expected, abs=CANONICAL_TOL)
    assert solved.distance_m == pytest.approx(2.0, abs=CANONICAL_TOL)
    assert solved.solver_tolerance_m == GEOMETRY_SOLVER_TOLERANCE_M
    assert solved.upper_bound_m - solved.lower_bound_m <= (
        GEOMETRY_SOLVER_TOLERANCE_M
    )


def test_low_evaluation_budget_raises_without_returning_distance():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (3.0, 0.0, 1.0)
    b = (3.0, 0.0, -1.0)
    with pytest.raises(GeometryConvergenceError, match='evaluation budget') as caught:
        solve_segment_to_horizontal_disk_distance(
            a, b, disk, tol=1.0e-18, max_evaluations=1
        )
    assert isinstance(caught.value, AnalysisError)
    assert isinstance(caught.value, GeometryConvergenceError)


def test_capsule_net_gap_fail_closes_when_uncertified(monkeypatch):
    import arachne_hx6_analysis.geometry as geometry

    monkeypatch.setattr(geometry, 'GEOMETRY_SOLVER_MAX_EVALUATIONS', 1)
    monkeypatch.setattr(geometry, 'GEOMETRY_SOLVER_TOLERANCE_M', 1.0e-18)
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    with pytest.raises(GeometryConvergenceError, match='evaluation budget'):
        signed_distance_disk_capsule(
            disk, Capsule('rim', (3.0, 0.0, 1.0), (3.0, 0.0, -1.0), 0.02)
        )


def test_near_grazing_disk_rim():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    offset = 1.0e-4
    a = (1.0 + offset, 0.0, 1.0)
    b = (1.0 + offset, 0.0, -1.0)
    actual = _compare_segment_disk(a, b, disk)
    expected = _oracle_point_to_disk((1.0 + offset, 0.0, 0.0), disk.center, disk.radius)
    assert actual == pytest.approx(expected, abs=CANONICAL_TOL)
    assert actual == pytest.approx(offset, abs=CANONICAL_TOL)


def test_extremely_short_segment():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (0.0, 0.0, 2.0)
    b = (1.0e-16, 0.0, 2.0)
    actual = _compare_segment_disk(a, b, disk)
    expected = _oracle_point_to_disk(a, disk.center, disk.radius)
    assert actual == pytest.approx(expected, abs=1.0e-12)
    assert actual == pytest.approx(2.0, abs=1.0e-12)


def test_long_segment_tiny_tolerance_still_certifies():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (0.0, 0.0, 2.0)
    b = (50.0, 0.0, 2.0)
    tiny = 1.0e-12
    solved = solve_segment_to_horizontal_disk_distance(a, b, disk, tol=tiny)
    _assert_certified(solved)
    expected = _oracle_point_to_disk(a, disk.center, disk.radius)
    assert solved.distance_m == pytest.approx(expected, abs=tiny)
    assert solved.distance_m == pytest.approx(2.0, abs=tiny)
    assert solved.upper_bound_m - solved.lower_bound_m <= tiny
    sampled = _oracle_segment_to_disk(a, b, disk.center, disk.radius)
    assert solved.distance_m <= sampled + ABS_TOL
    assert sampled - solved.distance_m <= _sampling_error_bound(a, b) + ABS_TOL


def test_segment_almost_parallel_to_disk_plane():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (2.0, 0.0, 1.0e-3)
    b = (5.0, 0.0, 1.2e-3)
    actual = _compare_segment_disk(a, b, disk)
    expected = _oracle_point_to_disk(a, disk.center, disk.radius)
    assert actual == pytest.approx(expected, abs=CANONICAL_TOL)
    assert actual == pytest.approx(math.hypot(1.0, 1.0e-3), abs=CANONICAL_TOL)


def test_solver_rejects_non_positive_nan_inf_tolerance_and_budget():
    disk = HorizontalDisk('d', (0.0, 0.0, 0.0), 1.0)
    a = (0.0, 0.0, 2.0)
    b = (0.0, 0.0, 3.0)
    for bad_tol in (0.0, -1.0e-9, float('nan'), float('inf'), True):
        with pytest.raises(InvalidInputError, match='geometry_solver_tolerance_m'):
            solve_segment_to_horizontal_disk_distance(a, b, disk, tol=bad_tol)
    for bad_budget in (0, -3, True):
        with pytest.raises(
            InvalidInputError, match='geometry_solver_max_evaluations'
        ):
            solve_segment_to_horizontal_disk_distance(
                a, b, disk, max_evaluations=bad_budget
            )
    with pytest.raises(InvalidInputError, match='geometry_solver_max_evaluations'):
        solve_segment_to_horizontal_disk_distance(
            a, b, disk, max_evaluations=1.5
        )
