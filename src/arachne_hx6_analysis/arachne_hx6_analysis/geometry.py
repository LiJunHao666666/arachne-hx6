"""G2 geometric primitives, clearances, and coxa/femur/tibia kinematics.

Rotor disks are filled horizontal circles with area, not points or rims only.
Leg segments are capsules (line segment + radius). Bodies and sensor pods
are axis-aligned boxes.

Public names are re-exported from geometry_primitives, geometry_solver, and
geometry_kinematics. Solver defaults live on this module so tests may
monkeypatch GEOMETRY_SOLVER_TOLERANCE_M and GEOMETRY_SOLVER_MAX_EVALUATIONS.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from arachne_hx6_analysis.geometry_kinematics import (
    LegMount,
    LegSegmentLengths,
    LegSegmentRadii,
    Transform,
    box_cross_section_capsule_radius_m,
    identity_transform,
    leg_segment_capsules,
)
from arachne_hx6_analysis.geometry_primitives import (
    Aabb,
    Capsule,
    HorizontalDisk,
    Vec3,
    aabb_extents,
    adjacent_rotor_tip_clearance_m,
    box_from_center_size,
    capsule_aabb,
    hex_layout_metrics,
    hexarotor_disk_centers,
    horizontal_disk_aabb,
    make_rotor_disks,
    min_disk_box_clearance_m,
    min_pairwise_disk_clearance_m,
    motor_yaw_angles_rad,
    point_to_horizontal_disk_distance,
    rot_y,
    rot_z,
    signed_distance_disk_aabb,
    signed_distance_horizontal_disks,
    union_aabb,
)
from arachne_hx6_analysis.geometry_solver import (
    CONVERGENCE_CERTIFIED,
    GEOMETRY_SOLVER_MAX_EVALUATIONS,
    GEOMETRY_SOLVER_TOLERANCE_M,
    GeometrySolverAccumulator,
    SOLVER_METHOD_BEST_FIRST_LIPSCHITZ,
    SegmentDiskDistanceResult,
    collect_geometry_solver_diagnostics,
    min_disk_capsule_clearance_m,
    segment_to_horizontal_disk_distance,
    signed_distance_disk_capsule,
    solve_segment_to_horizontal_disk_distance,
)
