"""G2 architecture constants, result records, and config dataclasses.

Leaf module: no architecture subpackage imports. Shared vocabulary for
baseline extraction, kinematics, mass ledger, candidate evaluation, and
joint gating.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
from typing import Any, Mapping, Sequence

from arachne_hx6_analysis.geometry import LegMount
from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    InvalidInputError,
)

GATE_CLEARANCE_MET = 'CLEARANCE_MET'
GATE_CLEARANCE_NOT_MET = 'CLEARANCE_NOT_MET'
ARCH_GATE_REJECTED_GEOMETRY = 'REJECTED_GEOMETRY'
ARCH_GATE_REJECTED_ENERGY_CLOSURE = 'REJECTED_ENERGY_CLOSURE'
ARCH_GATE_UNDETERMINED_MASS_LEDGER = 'UNDETERMINED_MASS_LEDGER'
ARCH_GATE_UNDETERMINED_MODEL_LIMITATION = 'UNDETERMINED_MODEL_LIMITATION'
ALLOWED_ARCHITECTURE_GATES = (
    ARCH_GATE_REJECTED_GEOMETRY,
    ARCH_GATE_REJECTED_ENERGY_CLOSURE,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARCH_GATE_UNDETERMINED_MODEL_LIMITATION,
)
FORBIDDEN_ARCHITECTURE_STATUS_WORDS = (
    'VIABLE',
    'FLYABLE',
    'SAFE_TO_FLY',
    'PROCUREMENT_READY',
    'RECOMMENDED_FOR_PURCHASE',
    'VALID_STOWED_POSE',
    'STOWED_PASS',
)
MASS_LEDGER_INCOMPLETE = 'INCOMPLETE'
MASS_LEDGER_COMPLETE = 'COMPLETE'
STOW_REQUIREMENTS_INCOMPLETE = 'INCOMPLETE'
STOW_POSE_EVIDENCE_UNQUALIFIED = 'UNQUALIFIED_ANALYSIS_POSE'
ROBUST_GEOMETRY_UNDETERMINED = 'UNDETERMINED'
ROBUST_GATE_UNQUANTIFIED = 'UNDETERMINED_UNQUANTIFIED_GEOMETRY_UNCERTAINTY'
NOMINAL_GEOMETRY_MET = 'NOMINAL_CLEARANCE_MET'
NOMINAL_GEOMETRY_NOT_MET = 'NOMINAL_CLEARANCE_NOT_MET'
ARM_COUPLING_BASELINE = 'BASELINE_RADIUS_NO_EXTENSION_MODEL'
ARM_COUPLING_UNMODELED = 'UNMODELED_ARM_EXTENSION_MASS'
ARM_EXTENSION_LIMITATION_REASON = 'arm_extension_mass_not_coupled_into_energy_closure'
BASELINE_MOTOR_CENTER_RADIUS_M = 0.30
REQUIRED_STOW_REQUIREMENT_KEYS = (
    'maximum_total_height_m',
    'maximum_leg_below_body_m',
    'maximum_planform_length_m',
    'maximum_planform_width_m',
)
EVIDENCE_MISSING = 'MISSING'
EVIDENCE_PLANNING_PLACEHOLDER = 'PLANNING_PLACEHOLDER'
EVIDENCE_VENDOR_DECLARED = 'VENDOR_DECLARED'
EVIDENCE_MEASURED = 'MEASURED'
ALLOWED_EVIDENCE_STATUS = (
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_PLACEHOLDER,
    EVIDENCE_VENDOR_DECLARED,
    EVIDENCE_MEASURED,
)
POSE_KIND_ANALYSIS_ONLY = 'ANALYSIS_POSE_ONLY'
TRANSITION_PROOF_FLAG = (
    'SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF'
)
REQUIRED_INTERMEDIATE_DIAMETERS_IN = (8.0, 10.0)
LEG_PREFIXES = ('lf', 'lm', 'lr', 'rf', 'rm', 'rr')
LEG_JOINT_SUFFIXES = ('coxa', 'femur', 'tibia')
REQUIRED_JOINT_NAMES = tuple(
    f'{prefix}_{suffix}_joint'
    for prefix in LEG_PREFIXES
    for suffix in LEG_JOINT_SUFFIXES
)
REQUIRED_MASS_LEDGER_ITEMS = (
    'frame_and_body',
    'six_leg_structures',
    'eighteen_leg_actuators',
    'six_motors',
    'six_escs',
    'propellers_and_hubs',
    'arm_extensions_and_reinforcement',
    'power_distribution',
    'high_current_wiring',
    'connectors_and_protection',
    'flight_controller',
    'companion_computer',
    'navigation_sensors',
    'rescue_environment_sensors',
    'cooling',
    'folding_and_locking_mechanism',
    'battery_container',
    'enclosure_and_fasteners',
    'contingency_allowance',
)
G1_BASELINE_XACRO_KEYS = (
    ('hex_arm_span_m', 'hex_arm_span'),
    ('coxa_length_m', 'coxa_length'),
    ('femur_length_m', 'femur_length'),
    ('tibia_length_m', 'tibia_length'),
    ('body_length_m', 'body_length'),
    ('body_width_m', 'body_width'),
    ('body_height_m', 'body_height'),
    ('sensor_pod_size_x_m', 'sensor_pod_size_x'),
    ('sensor_pod_size_y_m', 'sensor_pod_size_y'),
    ('sensor_pod_size_z_m', 'sensor_pod_size_z'),
    ('sensor_pod_z_m', 'sensor_pod_z'),
    ('hex_deck_offset_m', 'hex_deck_offset'),
    ('hex_rotor_z_offset_m', 'hex_rotor_z_offset'),
)
_BASELINE_ABS_TOL = 1.0e-12
_GATE_EPS = 1.0e-12


@dataclass(frozen=True)
class MassLedgerItem:
    item_id: str
    evidence_status: str
    mass_kg: float | None
    source_kind: str
    notes: str


@dataclass(frozen=True)
class ClearanceEvidence:
    """Nominal vs robust clearance for one geometric check."""

    nominal_clearance_m: float
    required_clearance_m: float
    nominal_clearance_margin_m: float
    geometry_uncertainty_allowance_m: float | None
    robust_clearance_margin_m: float | None
    nominal_gate: str
    robust_gate: str

    def as_dict(self) -> dict[str, Any]:
        return {
            'nominal_clearance_m': self.nominal_clearance_m,
            'required_clearance_m': self.required_clearance_m,
            'nominal_clearance_margin_m': self.nominal_clearance_margin_m,
            'geometry_uncertainty_allowance_m': (
                self.geometry_uncertainty_allowance_m
            ),
            'robust_clearance_margin_m': self.robust_clearance_margin_m,
            'nominal_gate': self.nominal_gate,
            'robust_gate': self.robust_gate,
        }


@dataclass(frozen=True)
class StowRequirements:
    maximum_total_height_m: float | None
    maximum_leg_below_body_m: float | None
    maximum_planform_length_m: float | None
    maximum_planform_width_m: float | None

    def as_dict(self) -> dict[str, float | None]:
        return {
            'maximum_total_height_m': self.maximum_total_height_m,
            'maximum_leg_below_body_m': self.maximum_leg_below_body_m,
            'maximum_planform_length_m': self.maximum_planform_length_m,
            'maximum_planform_width_m': self.maximum_planform_width_m,
        }

    def status(self) -> str:
        values = self.as_dict().values()
        if any(value is None for value in values):
            return STOW_REQUIREMENTS_INCOMPLETE
        return STOW_REQUIREMENTS_INCOMPLETE


@dataclass(frozen=True)
class G1Baseline:
    hex_arm_span_m: float
    coxa_length_m: float
    femur_length_m: float
    tibia_length_m: float
    body_length_m: float
    body_width_m: float
    body_height_m: float
    sensor_pod_size_x_m: float
    sensor_pod_size_y_m: float
    sensor_pod_size_z_m: float
    sensor_pod_z_m: float
    hex_deck_offset_m: float
    hex_rotor_z_offset_m: float
    rotor_plane_z_m: float
    sensor_pod_y_m: float
    first_motor_yaw_rad: float
    coxa_radius_m: float
    femur_width_m: float
    femur_height_m: float
    tibia_width_m: float
    tibia_height_m: float
    foot_radius_m: float
    camera_size_x_m: float
    camera_size_y_m: float
    camera_size_z_m: float
    camera_x_m: float
    camera_z_m: float
    joint_limits: Mapping[str, tuple[float, float]]
    mounts: tuple[LegMount, ...]
    xacro_values: Mapping[str, float] = field(repr=False)


@dataclass(frozen=True)
class ArchitectureConfig:
    status: str
    procurement_allowed: bool
    notes: str
    rotor_count: int
    propeller_diameters_in: tuple[float, ...]
    motor_center_radii_m: tuple[float, ...]
    min_tip_clearance_m: float
    min_body_clearance_m: float
    min_sensor_pod_clearance_m: float
    min_leg_clearance_m: float
    geometry_uncertainty_allowance_m: float | None
    sample_count: int
    analysis_stowed_pose_kind: str
    analysis_stowed_notes: str
    analysis_stowed_joints: Mapping[str, float]
    stow_requirements: StowRequirements
    g1_baseline_yaml: Mapping[str, float]
    mass_ledger_items: tuple[MassLedgerItem, ...]
    propulsion_config_path: Path
    xacro_path: Path
    standing_pose_path: Path
    raw: Mapping[str, object] = field(repr=False)

    def validate(self) -> None:
        if self.status != STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(
                f'status must be {STATUS_ANALYSIS_ONLY}, got {self.status!r}'
            )
        if self.procurement_allowed:
            raise InvalidInputError('procurement_allowed must be false')
        if self.rotor_count != 6:
            raise InvalidInputError(
                f'rotor_count must be 6, got {self.rotor_count}'
            )
        if not self.propeller_diameters_in:
            raise InvalidInputError('propeller_diameters_in must not be empty')
        if not self.motor_center_radii_m:
            raise InvalidInputError('motor_center_radii_m must not be empty')
        _require_positive_unique(
            self.propeller_diameters_in, 'propeller_diameters_in'
        )
        _require_positive_unique(
            self.motor_center_radii_m, 'motor_center_radii_m'
        )
        present = {round(value, 10) for value in self.propeller_diameters_in}
        for required in REQUIRED_INTERMEDIATE_DIAMETERS_IN:
            if round(required, 10) not in present:
                raise InvalidInputError(
                    'propeller_diameters_in must include intermediate '
                    f'candidates {list(REQUIRED_INTERMEDIATE_DIAMETERS_IN)}; '
                    f'missing {required}'
                )
        _require_non_negative_named(self.min_tip_clearance_m, 'min_tip_clearance_m')
        _require_non_negative_named(
            self.min_body_clearance_m, 'min_body_clearance_m'
        )
        _require_non_negative_named(
            self.min_sensor_pod_clearance_m, 'min_sensor_pod_clearance_m'
        )
        _require_non_negative_named(
            self.min_leg_clearance_m, 'min_leg_clearance_m'
        )
        if self.geometry_uncertainty_allowance_m is not None:
            _require_non_negative_named(
                self.geometry_uncertainty_allowance_m,
                'geometry_uncertainty_allowance_m',
            )
        if (
            not isinstance(self.sample_count, int)
            or isinstance(self.sample_count, bool)
            or self.sample_count < 2
        ):
            raise InvalidInputError(
                'leg_sweep.sample_count must be an integer >= 2, '
                f'got {self.sample_count!r}'
            )
        if self.analysis_stowed_pose_kind != POSE_KIND_ANALYSIS_ONLY:
            raise InvalidInputError(
                'analysis_stowed.pose_kind must be '
                f'{POSE_KIND_ANALYSIS_ONLY}, got '
                f'{self.analysis_stowed_pose_kind!r}'
            )


@dataclass(frozen=True)
class BaselineCheck:
    consistent: bool
    comparisons: tuple[dict[str, Any], ...]
    xacro_path: str
    standing_pose_path: str


@dataclass(frozen=True)
class SweepResult:
    sample_count: int
    min_clearance_m: float
    worst_sample_index: int
    worst_path_fraction: float
    worst_leg_segment: str
    worst_rotor: str
    below_threshold: bool
    start_clearance_m: float
    end_clearance_m: float
    proof_flag: str


@dataclass(frozen=True)
class GeometryCandidate:
    diameter_inch: float
    diameter_m: float
    motor_center_radius_m: float
    adjacent_motor_center_m: float
    adjacent_rotor_tip_clearance_m: float
    min_motor_center_radius_m: float
    rotor_envelope_diameter_m: float
    rotor_spacing_gate: str
    body_clearance_m: float
    body_clearance_gate: str
    body_worst_rotor: str
    sensor_pod_clearance_m: float
    sensor_pod_clearance_gate: str
    sensor_pod_worst_rotor: str
    sampled_leg_sweep: SweepResult
    zero_pose_leg_clearance_m: float
    standing_envelope: Mapping[str, float]
    zero_envelope: Mapping[str, float]
    analysis_stowed_envelope: Mapping[str, float]
    rotor_spacing_evidence: ClearanceEvidence
    body_clearance_evidence: ClearanceEvidence
    sensor_pod_clearance_evidence: ClearanceEvidence
    sampled_leg_evidence: ClearanceEvidence
    nominal_geometry_status: str
    robust_geometry_status: str
    arm_radius_mass_coupling_status: str
    standing_total_height_m: float
    analysis_pose_total_height_m: float
    height_reduction_m: float
    height_reduction_ratio: float
    standing_leg_below_body_m: float
    analysis_pose_leg_below_body_m: float
    standing_planform_length_m: float
    standing_planform_width_m: float
    analysis_pose_planform_length_m: float
    analysis_pose_planform_width_m: float
    standing_rotor_plane_to_lowest_leg_point_m: float
    rotor_plane_to_lowest_leg_point_m: float
    rejection_reasons: tuple[str, ...]
    limitation_reasons: tuple[str, ...]


@dataclass(frozen=True)
class JointGateRow:
    uncertainty_case: str
    scenario_name: str
    diameter_inch: float
    motor_center_radius_m: float
    rotor_spacing_gate: str
    body_clearance_gate: str
    sensor_pod_clearance_gate: str
    sampled_leg_sweep_gate: str
    nominal_geometry_status: str
    robust_geometry_status: str
    energy_mass_closure: bool
    energy_mass_closure_status: str
    mass_ledger_status: str
    stow_requirements_status: str
    arm_radius_mass_coupling_status: str
    architecture_gate: str
    rejection_reasons: tuple[str, ...]
    limitation_reasons: tuple[str, ...]
    adjacent_motor_center_m: float
    adjacent_rotor_tip_clearance_m: float
    min_motor_center_radius_m: float
    rotor_envelope_diameter_m: float
    body_clearance_m: float
    sensor_pod_clearance_m: float
    sampled_min_clearance_m: float
    standing_length_m: float
    standing_width_m: float
    standing_height_m: float
    stowed_length_m: float
    stowed_width_m: float
    stowed_height_m: float
    standing_leg_below_body_m: float
    analysis_pose_leg_below_body_m: float
    height_reduction_m: float
    height_reduction_ratio: float
    rotor_plane_to_lowest_leg_point_m: float
    energy_total_mass_kg: float | None
    energy_battery_mass_kg: float | None


@dataclass(frozen=True)
class ArchitectureResult:
    status: str
    procurement_allowed: bool
    overall_architecture_feasibility: str
    mass_ledger_status: str
    stow_requirements_status: str
    stow_pose_evidence_status: str
    stow_pose_is_hardware_validated: bool
    robust_geometry_status: str
    transition_proof_flag: str
    config: ArchitectureConfig
    baseline: BaselineCheck
    standing_joints: Mapping[str, float]
    analysis_stowed_joints: Mapping[str, float]
    mass_ledger_items: tuple[MassLedgerItem, ...]
    geometry_candidates: tuple[GeometryCandidate, ...]
    joint_gate_rows: tuple[JointGateRow, ...]
    unmodeled: tuple[str, ...]
    diagnostic: Mapping[str, Any]



def _require_positive_unique(values: Sequence[float], path: str) -> None:
    seen: set[float] = set()
    for index, value in enumerate(values):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise InvalidInputError(
                f'{path}[{index}] must be a real number, got {value!r}'
            )
        if not math.isfinite(value) or value <= 0.0:
            raise InvalidInputError(
                f'{path}[{index}] must be finite and > 0, got {value}'
            )
        if value in seen:
            raise InvalidInputError(f'duplicate {path} value: {value}')
        seen.add(value)


def _require_non_negative_named(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    if not math.isfinite(value) or value < 0.0:
        raise InvalidInputError(f'{name} must be finite and >= 0, got {value}')
