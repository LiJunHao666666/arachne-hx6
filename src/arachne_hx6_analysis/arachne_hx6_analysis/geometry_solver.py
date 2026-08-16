"""Certified unsigned segment-to-horizontal-disk distance solver.

Returns a distance only when upper_bound - lower_bound <= tolerance.
Reaching the evaluation budget without that certificate is fail-closed.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import heapq
import math
import sys
from typing import Iterator, Sequence

from arachne_hx6_analysis.geometry_primitives import (
    Capsule,
    HorizontalDisk,
    Vec3,
    _EPS,
    _clamp,
    _hypot3,
    _point_to_disk_closest,
    _sub,
)
from arachne_hx6_analysis.model import (
    GeometryConvergenceError,
    InvalidInputError,
)

GEOMETRY_SOLVER_TOLERANCE_M = 1.0e-9
GEOMETRY_SOLVER_MAX_EVALUATIONS = 128
SOLVER_METHOD_BEST_FIRST_LIPSCHITZ = 'best_first_lipschitz_subdivision'
CONVERGENCE_CERTIFIED = 'CERTIFIED'



@dataclass(frozen=True)
class SegmentDiskDistanceResult:
    """Certified unsigned segment-to-disk distance plus solver diagnostics."""

    distance_m: float
    solver_method: str
    solver_tolerance_m: float
    evaluations_used: int
    certified_error_bound_m: float
    convergence_status: str
    lower_bound_m: float
    upper_bound_m: float


@dataclass
class GeometrySolverAccumulator:
    """Worst-case certified solver diagnostics over many queries."""

    solver_method: str = SOLVER_METHOD_BEST_FIRST_LIPSCHITZ
    solver_tolerance_m: float = GEOMETRY_SOLVER_TOLERANCE_M
    evaluations_used: int = 0
    certified_error_bound_m: float = 0.0
    convergence_status: str = CONVERGENCE_CERTIFIED
    solves_certified: int = 0
    max_evaluations: int = GEOMETRY_SOLVER_MAX_EVALUATIONS

    def record(self, result: SegmentDiskDistanceResult) -> None:
        self.solves_certified += 1
        self.evaluations_used = max(self.evaluations_used, result.evaluations_used)
        self.certified_error_bound_m = max(
            self.certified_error_bound_m, result.certified_error_bound_m
        )
        self.solver_method = result.solver_method
        self.solver_tolerance_m = result.solver_tolerance_m
        if result.convergence_status != CONVERGENCE_CERTIFIED:
            self.convergence_status = result.convergence_status

    def as_dict(self) -> dict[str, object]:
        return {
            'solver_method': self.solver_method,
            'solver_tolerance_m': self.solver_tolerance_m,
            'evaluations_used': self.evaluations_used,
            'certified_error_bound_m': self.certified_error_bound_m,
            'convergence_status': self.convergence_status,
            'max_evaluations': self.max_evaluations,
            'solves_certified': self.solves_certified,
            'return_rule': 'upper_bound - lower_bound <= solver_tolerance_m',
        }


_solver_accumulators: list[GeometrySolverAccumulator] = []


def _record_solver_result(result: SegmentDiskDistanceResult) -> None:
    if _solver_accumulators:
        _solver_accumulators[-1].record(result)


@contextmanager
def collect_geometry_solver_diagnostics() -> Iterator[GeometrySolverAccumulator]:
    """Record certified segment-disk solves for an architecture run."""
    accumulator = GeometrySolverAccumulator()
    _solver_accumulators.append(accumulator)
    try:
        yield accumulator
    finally:
        _solver_accumulators.pop()



def _interval_lower_bound(
    t0: float,
    t1: float,
    f0: float,
    g0: float,
    f1: float,
    g1: float,
    length: float,
) -> float:
    """Valid lower bound on min f over [t0, t1].

    Distance to a filled disk is convex and 1-Lipschitz, so both the
    path-speed Lipschitz bound and the convex supporting-line bound are
    valid. The supporting value is stepped toward zero by one ulp so a
    floating-point overestimate cannot discard the true minimizer.
    """
    width = t1 - t0
    if width <= 0.0:
        return min(f0, f1)
    lipschitz = min(f0, f1) - length * width
    if g0 >= 0.0 and g1 >= 0.0:
        support = f0
    elif g0 <= 0.0 and g1 <= 0.0:
        support = f1
    elif g0 != g1:
        delta_t = (f1 - f0 - g1 * width) / (g0 - g1)
        if 0.0 <= delta_t <= width:
            support = f0 + g0 * delta_t
        else:
            support = min(f0, f1)
    else:
        support = min(f0, f1)
    support = min(support, f0, f1)
    if support > 0.0:
        support = math.nextafter(support, 0.0)
    return max(0.0, lipschitz, support)


def _require_positive_tolerance(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise InvalidInputError(f'{name} must be finite and > 0, got {value}')
    return number


def _require_positive_evaluation_budget(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f'{name} must be an integer, got {value!r}')
    if value < 1:
        raise InvalidInputError(f'{name} must be an integer >= 1, got {value}')
    return value


def _certified_segment_disk_result(
    distance_m: float,
    tolerance_m: float,
    evaluations_used: int,
    lower_bound_m: float,
    upper_bound_m: float,
) -> SegmentDiskDistanceResult:
    if (
        not math.isfinite(distance_m)
        or not math.isfinite(lower_bound_m)
        or not math.isfinite(upper_bound_m)
        or distance_m < 0.0
        or lower_bound_m < 0.0
        or upper_bound_m < 0.0
        or upper_bound_m < lower_bound_m
    ):
        raise InvalidInputError('segment-disk distance must be finite and >= 0')
    gap = upper_bound_m - lower_bound_m
    if gap > tolerance_m:
        raise GeometryConvergenceError(
            'segment-to-disk distance is not certified: '
            f'upper_bound - lower_bound = {gap} m > tolerance {tolerance_m} m'
        )
    result = SegmentDiskDistanceResult(
        distance_m=distance_m,
        solver_method=SOLVER_METHOD_BEST_FIRST_LIPSCHITZ,
        solver_tolerance_m=tolerance_m,
        evaluations_used=evaluations_used,
        certified_error_bound_m=gap,
        convergence_status=CONVERGENCE_CERTIFIED,
        lower_bound_m=lower_bound_m,
        upper_bound_m=upper_bound_m,
    )
    _record_solver_result(result)
    return result



def _active_solver_defaults() -> tuple[float, int]:
    """Use live façade constants so tests can monkeypatch geometry.py."""
    facade = sys.modules.get('arachne_hx6_analysis.geometry')
    if facade is not None:
        tolerance = getattr(facade, 'GEOMETRY_SOLVER_TOLERANCE_M', None)
        budget = getattr(facade, 'GEOMETRY_SOLVER_MAX_EVALUATIONS', None)
        if tolerance is not None and budget is not None:
            return tolerance, budget
    return GEOMETRY_SOLVER_TOLERANCE_M, GEOMETRY_SOLVER_MAX_EVALUATIONS


def solve_segment_to_horizontal_disk_distance(
    a: Vec3,
    b: Vec3,
    disk: HorizontalDisk,
    tol: float | None = None,
    max_evaluations: int | None = None,
) -> SegmentDiskDistanceResult:
    """Unsigned segment-to-disk distance with an error certificate.

    Exact plane-hit test, analytic candidates (endpoints, axis, cylinder,
    closest approach to the disk centre), then best-first subdivision.
    Each interval keeps a valid lower bound from the path-speed Lipschitz
    constant and from convex supporting lines (distance to a filled disk
    is convex). The distance is returned only when

        upper_bound - lower_bound <= geometry_solver_tolerance_m.

    Reaching the evaluation budget without that certificate raises
    GeometryConvergenceError. The previous 128-evaluation cap could return
    the current best without a proof.
    """
    default_tol, default_budget = _active_solver_defaults()
    tolerance_m = _require_positive_tolerance(
        default_tol if tol is None else tol,
        'geometry_solver_tolerance_m',
    )
    evaluation_budget = _require_positive_evaluation_budget(
        default_budget if max_evaluations is None else max_evaluations,
        'geometry_solver_max_evaluations',
    )
    ax, ay, az = a
    bx, by, bz = b
    dx = bx - ax
    dy = by - ay
    dz = bz - az
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    cx, cy, cz = disk.center
    radius = disk.radius
    if not math.isfinite(radius) or radius <= 0.0:
        raise InvalidInputError(
            f'disk radius must be finite and > 0, got {radius}'
        )
    if not math.isfinite(length):
        raise InvalidInputError('segment length must be finite')

    if abs(dz) > _EPS:
        t_plane = (cz - az) / dz
        if 0.0 <= t_plane <= 1.0:
            ix = ax + t_plane * dx
            iy = ay + t_plane * dy
            if math.hypot(ix - cx, iy - cy) <= radius:
                return _certified_segment_disk_result(
                    0.0, tolerance_m, 0, 0.0, 0.0
                )

    def dist_and_deriv(t: float) -> tuple[float, float]:
        point = (ax + t * dx, ay + t * dy, az + t * dz)
        closest = _point_to_disk_closest(point, disk)
        offset = _sub(point, closest)
        value = _hypot3(offset)
        if not math.isfinite(value):
            raise InvalidInputError('segment-disk distance is not finite')
        if value <= 0.0:
            return 0.0, 0.0
        deriv = (offset[0] * dx + offset[1] * dy + offset[2] * dz) / value
        if not math.isfinite(deriv):
            raise InvalidInputError('segment-disk derivative is not finite')
        return value, deriv

    candidates = [0.0, 1.0]
    qa = dx * dx + dy * dy
    px = ax - cx
    py = ay - cy
    if qa > _EPS:
        t_axis = -(px * dx + py * dy) / qa
        if 0.0 <= t_axis <= 1.0:
            candidates.append(t_axis)
        disc = (
            (2.0 * (px * dx + py * dy)) ** 2
            - 4.0 * qa * (px * px + py * py - radius * radius)
        )
        if disc >= 0.0:
            root = math.sqrt(disc)
            t1 = (-2.0 * (px * dx + py * dy) - root) / (2.0 * qa)
            t2 = (-2.0 * (px * dx + py * dy) + root) / (2.0 * qa)
            for t_cyl in (t1, t2):
                if 0.0 <= t_cyl <= 1.0:
                    candidates.append(t_cyl)
    ab2 = length * length
    if ab2 > _EPS:
        t_c = ((cx - ax) * dx + (cy - ay) * dy + (cz - az) * dz) / ab2
        candidates.append(_clamp(t_c, 0.0, 1.0))

    knots = sorted({_clamp(float(value), 0.0, 1.0) for value in candidates})
    if knots[0] != 0.0:
        knots.insert(0, 0.0)
    if knots[-1] != 1.0:
        knots.append(1.0)
    evaluations_used = 0
    knot_values: dict[float, tuple[float, float]] = {}
    for t_knot in knots:
        knot_values[t_knot] = dist_and_deriv(t_knot)
        evaluations_used += 1
    upper_bound = min(value for value, _deriv in knot_values.values())
    if upper_bound <= 0.0:
        return _certified_segment_disk_result(
            0.0, tolerance_m, evaluations_used, 0.0, 0.0
        )
    if length <= 0.0:
        return _certified_segment_disk_result(
            upper_bound, tolerance_m, evaluations_used, upper_bound, upper_bound
        )
    if length <= tolerance_m:
        lower_bound = max(0.0, upper_bound - length)
        return _certified_segment_disk_result(
            upper_bound,
            tolerance_m,
            evaluations_used,
            lower_bound,
            upper_bound,
        )

    counter = 0
    heap: list[tuple[float, int, float, float, float, float, float, float]] = []

    def push(
        t0: float,
        t1: float,
        f0: float,
        g0: float,
        f1: float,
        g1: float,
    ) -> None:
        nonlocal counter
        width = t1 - t0
        if width <= 0.0:
            return
        lower = _interval_lower_bound(t0, t1, f0, g0, f1, g1, length)
        if lower >= upper_bound:
            return
        heapq.heappush(heap, (lower, counter, t0, t1, f0, g0, f1, g1))
        counter += 1

    def global_lower_bound() -> float:
        if not heap:
            return upper_bound
        return min(upper_bound, heap[0][0])

    for t0, t1 in zip(knots, knots[1:]):
        f0, g0 = knot_values[t0]
        f1, g1 = knot_values[t1]
        push(t0, t1, f0, g0, f1, g1)

    subdivision_evals = 0
    while True:
        lower_bound = global_lower_bound()
        if upper_bound - lower_bound <= tolerance_m:
            return _certified_segment_disk_result(
                upper_bound,
                tolerance_m,
                evaluations_used,
                lower_bound,
                upper_bound,
            )
        if subdivision_evals >= evaluation_budget:
            raise GeometryConvergenceError(
                'segment-to-disk Lipschitz solver reached the evaluation '
                f'budget ({evaluation_budget}) with optimality gap '
                f'{upper_bound - lower_bound} m > tolerance {tolerance_m} m'
            )
        _lower, _tie, t0, t1, f0, g0, f1, g1 = heapq.heappop(heap)
        if _lower >= upper_bound:
            continue
        tm = 0.5 * (t0 + t1)
        fm, gm = dist_and_deriv(tm)
        evaluations_used += 1
        subdivision_evals += 1
        if fm < upper_bound:
            upper_bound = fm
            if upper_bound <= 0.0:
                return _certified_segment_disk_result(
                    0.0, tolerance_m, evaluations_used, 0.0, 0.0
                )
        push(t0, tm, f0, g0, fm, gm)
        push(tm, t1, fm, gm, f1, g1)


def segment_to_horizontal_disk_distance(
    a: Vec3,
    b: Vec3,
    disk: HorizontalDisk,
    tol: float | None = None,
    max_evaluations: int | None = None,
) -> float:
    """Unsigned distance from a line segment to a filled horizontal disk.

    Returns only a certified distance. See
    solve_segment_to_horizontal_disk_distance for the error certificate.
    """
    return solve_segment_to_horizontal_disk_distance(
        a, b, disk, tol=tol, max_evaluations=max_evaluations
    ).distance_m


def signed_distance_disk_capsule(disk: HorizontalDisk, capsule: Capsule) -> float:
    """Signed gap: certified segment-to-disk distance minus capsule radius."""
    unsigned = solve_segment_to_horizontal_disk_distance(
        capsule.a, capsule.b, disk
    )
    return unsigned.distance_m - capsule.radius




def min_disk_capsule_clearance_m(
    disks: Sequence[HorizontalDisk],
    capsules: Sequence[Capsule],
) -> tuple[float, str, str]:
    """Minimum signed disk-capsule gap, plus disk and capsule names."""
    if not disks or not capsules:
        raise InvalidInputError('need at least one disk and one capsule')
    best_gap = float('inf')
    best_disk = disks[0].name
    best_capsule = capsules[0].name
    for disk in disks:
        for capsule in capsules:
            gap = signed_distance_disk_capsule(disk, capsule)
            if gap < best_gap:
                best_gap = gap
                best_disk = disk.name
                best_capsule = capsule.name
    return best_gap, best_disk, best_capsule
