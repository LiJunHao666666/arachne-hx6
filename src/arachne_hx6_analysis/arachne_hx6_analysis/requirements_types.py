"""G3 requirement, evidence, and readiness-gate vocabulary.

Leaf module: no G3 subpackage imports. Shared IDs and records for the
requirements contract, evidence ledger, mass intervals, uncertainty
budget, stow contract, and fail-closed gates.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from arachne_hx6_analysis.architecture_types import REQUIRED_MASS_LEDGER_ITEMS
from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
)

STATUS_ANALYSIS_ONLY = STATUS_ANALYSIS_ONLY
STATUS_NOT_FOR_PROCUREMENT = STATUS_NOT_FOR_PROCUREMENT
OVERALL_SYSTEM_READINESS = STATUS_OVERALL_UNDETERMINED

EVIDENCE_MISSING = 'MISSING'
EVIDENCE_PLANNING_ASSUMPTION = 'PLANNING_ASSUMPTION'
EVIDENCE_VENDOR_DECLARED = 'VENDOR_DECLARED'
EVIDENCE_MEASURED = 'MEASURED'
EVIDENCE_TEST_VALIDATED = 'TEST_VALIDATED'
ALLOWED_EVIDENCE_LEVELS = (
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    EVIDENCE_VENDOR_DECLARED,
    EVIDENCE_MEASURED,
    EVIDENCE_TEST_VALIDATED,
)
HARDWARE_SUFFICIENT_LEVELS = (
    EVIDENCE_VENDOR_DECLARED,
    EVIDENCE_MEASURED,
    EVIDENCE_TEST_VALIDATED,
)
HARDWARE_GATE_LEVELS = (
    EVIDENCE_MEASURED,
    EVIDENCE_TEST_VALIDATED,
)

REQUIREMENT_INCOMPLETE = 'INCOMPLETE_REQUIREMENT'
REQUIREMENT_SPECIFIED = 'SPECIFIED'
REQUIREMENTS_INCOMPLETE = 'INCOMPLETE'
REQUIREMENTS_COMPLETE = 'COMPLETE'
BLOCK_REASON_INCOMPLETE_SPECIFICATION = 'INCOMPLETE_SPECIFICATION'
BLOCK_REASON_MISSING_EVIDENCE = 'MISSING_EVIDENCE'
BLOCK_REASON_NO_REQUIRED_EVIDENCE = 'NO_REQUIRED_EVIDENCE'
BLOCK_REASON_PLANNING_ASSUMPTION_ONLY = 'PLANNING_ASSUMPTION_ONLY'
BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE = 'MIXED_INSUFFICIENT_EVIDENCE'
BLOCK_REASON_NOT_SATISFIED = 'NOT_SATISFIED'

KIND_QUANTITATIVE = 'quantitative'
KIND_QUALITATIVE = 'qualitative'
ALLOWED_REQUIREMENT_KINDS = (KIND_QUANTITATIVE, KIND_QUALITATIVE)

ALLOWED_CATEGORIES = (
    'SYS-MASS',
    'SYS-GEO',
    'SYS-STOW',
    'SYS-PROP',
    'SYS-POWER',
    'SYS-STRUCT',
    'SYS-THERM',
    'SYS-CTRL',
    'SYS-SENSE',
    'SYS-SAFE',
    'SYS-TRACE',
)
ALLOWED_VERIFICATION_METHODS = (
    'ANALYSIS',
    'INSPECTION',
    'TEST',
    'DEMONSTRATION',
    'ANALYSIS_AND_TEST',
)

COMPONENT_COMPLETE = 'COMPLETE'
COMPONENT_INCOMPLETE = 'INCOMPLETE'
MASS_LEDGER_INCOMPLETE = 'INCOMPLETE'
MASS_LEDGER_COMPLETE = 'COMPLETE'
COMPONENT_INTERVAL_INCOMPLETE = 'INCOMPLETE'
COMPONENT_INTERVAL_COMPLETE = 'COMPLETE'

GEOMETRY_BUDGET_INCOMPLETE = 'INCOMPLETE'
GEOMETRY_BUDGET_COMPLETE = 'COMPLETE'
ROBUST_GEOMETRY_UNDETERMINED = 'UNDETERMINED'
COMBINATION_LINEAR_SUM = 'CONSERVATIVE_LINEAR_SUM'
COMBINATION_RSS = 'RSS'
ALLOWED_COMBINATION_METHODS = (COMBINATION_LINEAR_SUM, COMBINATION_RSS)

REQUIRED_UNCERTAINTY_SOURCES = (
    'manufacturing_tolerance',
    'assembly_tolerance',
    'motor_mount_position_error',
    'propeller_radius_tolerance',
    'propeller_tracking_or_flapping_allowance',
    'structural_deflection_allowance',
    'leg_joint_zero_error',
    'sensor_pod_installation_error',
    'cable_connector_intrusion_allowance',
)

STOW_REQUIREMENTS_INCOMPLETE = 'INCOMPLETE'
STOW_REQUIREMENTS_COMPLETE = 'COMPLETE'
STOW_POSE_EVIDENCE_UNQUALIFIED = 'UNQUALIFIED_ANALYSIS_POSE'
STOW_HARDWARE_NOT_PERFORMED = 'NOT_PERFORMED'
STOW_GATE_UNDETERMINED = 'UNDETERMINED_REQUIREMENTS'

ARM_COUPLING_UNDETERMINED = 'UNDETERMINED_MISSING_EVIDENCE'
ARM_COUPLING_INTERVAL_COMPUTED = 'INTERVAL_COMPUTED_NOT_A_HARDWARE_PASS'

TRACE_INCOMPLETE = 'INCOMPLETE'
TRACE_CONSISTENT = 'CONSISTENT'

GATE_INVALID_INPUT = 'INVALID_INPUT'
GATE_UNDETERMINED_REQUIREMENTS = 'UNDETERMINED_REQUIREMENTS'
GATE_UNDETERMINED_EVIDENCE = 'UNDETERMINED_EVIDENCE'
GATE_UNDETERMINED_MASS_LEDGER = 'UNDETERMINED_MASS_LEDGER'
GATE_UNDETERMINED_GEOMETRY_UNCERTAINTY = 'UNDETERMINED_GEOMETRY_UNCERTAINTY'
GATE_UNDETERMINED_STOW_REQUIREMENTS = 'UNDETERMINED_STOW_REQUIREMENTS'
GATE_UNDETERMINED_ARM_MASS_COUPLING = 'UNDETERMINED_ARM_MASS_COUPLING'
GATE_EVIDENCE_COMPLETE_NEXT = 'EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS'
ALLOWED_READINESS_GATES = (
    GATE_UNDETERMINED_REQUIREMENTS,
    GATE_UNDETERMINED_EVIDENCE,
    GATE_UNDETERMINED_MASS_LEDGER,
    GATE_UNDETERMINED_GEOMETRY_UNCERTAINTY,
    GATE_UNDETERMINED_STOW_REQUIREMENTS,
    GATE_UNDETERMINED_ARM_MASS_COUPLING,
    GATE_EVIDENCE_COMPLETE_NEXT,
)
READINESS_GATE_PRIORITY = ALLOWED_READINESS_GATES

FORBIDDEN_G3_STATUS_WORDS = (
    'VIABLE',
    'FLYABLE',
    'SAFE_TO_FLY',
    'PROCUREMENT_READY',
    'RECOMMENDED_FOR_PURCHASE',
    'VALIDATED_HARDWARE',
    'STOWED_PASS',
    'VALID_STOWED_POSE',
)

G2_MASS_COMPONENT_IDS = REQUIRED_MASS_LEDGER_ITEMS

PLANNING_COMPARISON_NOT_APPLICABLE = 'NOT_APPLICABLE_MASS_LEDGER_INCOMPLETE'
PLANNING_COMPARISON_INTERVAL_ONLY = 'PLANNING_LABEL_COMPARISON_ONLY'

TEST_NOT_PERFORMED = 'NOT_PERFORMED'

OFFICIAL_REPORT_FIELDS = (
    'status',
    'procurement_allowed',
    'overall_system_readiness',
    'requirements_status',
    'evidence_ledger_status',
    'mass_ledger_status',
    'component_mass_interval_status',
    'total_mass_lower_kg',
    'total_mass_upper_kg',
    'missing_component_ids',
    'planning_scenario_comparison',
    'geometry_uncertainty_budget_status',
    'total_geometry_uncertainty_allowance_m',
    'robust_clearance_margin_m',
    'robust_geometry_status',
    'stow_requirements_status',
    'stow_pose_evidence_status',
    'stow_hardware_validation_status',
    'stow_gate',
    'arm_radius_mass_coupling_status',
    'arm_extension_mass_lower_kg',
    'arm_extension_mass_upper_kg',
    'traceability_status',
    'readiness_gate',
    'blocker_ids',
    'orphan_evidence_ids',
    'broken_reference_ids',
    'blocking_reasons',
    'next_required_evidence',
    'whole_vehicle_energy_mass_closure_claimed',
    'requirements_total',
    'requirements_specified',
    'requirements_incomplete_specification',
    'requirements_verified',
    'requirements_satisfied',
    'specified_requirement_ids',
    'incomplete_specification_requirement_ids',
    'verified_requirement_ids',
    'satisfied_requirement_ids',
    'missing_evidence_requirement_ids',
    'planning_assumption_only_requirement_ids',
    'mixed_insufficient_evidence_requirement_ids',
    'sufficient_evidence_requirement_ids',
    'evidence_blocked_requirement_ids',
    'incomplete_blocking_requirement_ids',
    'all_blocking_requirement_ids',
    'nonblocking_unverified_requirement_ids',
    'unsatisfied_blocking_requirement_ids',
    'blocking_reason_codes',
    'blocking_requirement_reasons',
)

ALLOWED_COMPONENT_IDS = G2_MASS_COMPONENT_IDS + (
    'geometry_uncertainty',
    'arm_extension',
    'stow_mechanism',
    'propulsion',
    'power',
    'thermal',
    'control',
    'sensing',
    'safety',
    'analysis_process',
    'vehicle',
)


@dataclass(frozen=True)
class RequirementRecord:
    requirement_id: str
    title: str
    category: str
    description: str
    rationale: str
    verification_method: str
    required_evidence_ids: tuple[str, ...]
    linked_test_ids: tuple[str, ...]
    linked_report_fields: tuple[str, ...]
    threshold: float | None
    value: float | None
    range_lower: float | None
    range_upper: float | None
    unit: str | None
    applicability: str
    blocking: bool
    notes: str
    kind: str
    status: str


@dataclass(frozen=True)
class TestRecord:
    test_id: str
    title: str
    method: str
    linked_requirement_ids: tuple[str, ...]
    status: str
    notes: str


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    component_id: str
    parameter: str
    evidence_level: str
    value: float | None
    lower: float | None
    upper: float | None
    unit: str | None
    source: str | None
    source_date: str | None
    measurement_method: str | None
    sample_count: int | None
    uncertainty: float | None
    linked_requirement_ids: tuple[str, ...]
    status: str
    notes: str
    vendor: str | None = None
    model: str | None = None
    access_date: str | None = None
    measurement_equipment: str | None = None
    measurement_time: str | None = None
    test_id: str | None = None
    test_conditions: str | None = None
    raw_result: str | None = None
    verdict: str | None = None
    uncertainty_unit: str | None = None


@dataclass(frozen=True)
class MassComponent:
    component_id: str
    quantity: int
    mass_lower_kg: float | None
    mass_upper_kg: float | None
    evidence_id: str
    evidence_level: str
    completeness_status: str
    notes: str


@dataclass(frozen=True)
class UncertaintySource:
    source_id: str
    lower_m: float | None
    upper_m: float | None
    allowance_m: float | None
    unit: str
    evidence_id: str
    notes: str


@dataclass(frozen=True)
class ArmCouplingContract:
    baseline_radius_m: float | None
    candidate_radius_m: float | None
    extension_length_per_arm_m: float | None
    arm_count: int | None
    linear_mass_lower_kg_per_m: float | None
    linear_mass_upper_kg_per_m: float | None
    connector_mass_lower_kg: float | None
    connector_mass_upper_kg: float | None
    wiring_mass_lower_kg_per_m: float | None
    wiring_mass_upper_kg_per_m: float | None
    reinforcement_mass_lower_kg: float | None
    reinforcement_mass_upper_kg: float | None
    evidence_ids: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class StowContract:
    maximum_stowed_length_m: float | None
    maximum_stowed_width_m: float | None
    maximum_stowed_height_m: float | None
    minimum_rotor_to_leg_clearance_m: float | None
    maximum_transition_time_s: float | None
    actuator_torque_lower_nm: float | None
    actuator_torque_upper_nm: float | None
    lock_load_capacity_n: float | None
    lock_stiffness_nm_per_rad: float | None
    position_repeatability_rad: float | None
    power_loss_safe_state: str | None
    landing_deployment_condition: str | None
    flight_lock_verification_method: str | None
    emergency_recovery_requirement: str | None
    notes: str


@dataclass(frozen=True)
class RequirementsConfig:
    status: str
    procurement_allowed: bool
    notes: str
    requirements: tuple[RequirementRecord, ...]
    tests: tuple[TestRecord, ...]
    evidence: tuple[EvidenceRecord, ...]
    mass_components: tuple[MassComponent, ...]
    uncertainty_sources: tuple[UncertaintySource, ...]
    combination_method: str | None
    nominal_clearance_margin_m: float | None
    arm_coupling: ArmCouplingContract
    stow: StowContract
    requirements_path: Path
    evidence_path: Path
    uncertainty_path: Path
    stow_path: Path
    raw: Mapping[str, object] = field(repr=False)


@dataclass(frozen=True)
class MassBudgetResult:
    component_mass_interval_status: str
    mass_ledger_status: str
    total_mass_lower_kg: float | None
    total_mass_upper_kg: float | None
    missing_component_ids: tuple[str, ...]
    components: tuple[MassComponent, ...]
    planning_scenario_comparison: Mapping[str, Any]
    whole_vehicle_energy_mass_closure_claimed: bool


@dataclass(frozen=True)
class UncertaintyBudgetResult:
    geometry_uncertainty_budget_status: str
    combination_method: str | None
    total_geometry_uncertainty_allowance_m: float | None
    robust_clearance_margin_m: float | None
    robust_geometry_status: str
    sources: tuple[UncertaintySource, ...]
    missing_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ArmCouplingResult:
    arm_radius_mass_coupling_status: str
    arm_extension_mass_lower_kg: float | None
    arm_extension_mass_upper_kg: float | None
    extension_length_per_arm_m: float | None
    missing_field_names: tuple[str, ...]


@dataclass(frozen=True)
class StowResult:
    stow_requirements_status: str
    stow_pose_evidence_status: str
    stow_hardware_validation_status: str
    stow_gate: str
    missing_field_names: tuple[str, ...]
    contract: StowContract


@dataclass(frozen=True)
class TraceabilityResult:
    requirements_total: int
    requirements_specified: int
    requirements_incomplete_specification: int
    requirements_verified: int
    requirements_satisfied: int
    specified_requirement_ids: tuple[str, ...]
    incomplete_specification_requirement_ids: tuple[str, ...]
    verified_requirement_ids: tuple[str, ...]
    satisfied_requirement_ids: tuple[str, ...]
    missing_evidence_requirement_ids: tuple[str, ...]
    planning_assumption_only_requirement_ids: tuple[str, ...]
    mixed_insufficient_evidence_requirement_ids: tuple[str, ...]
    sufficient_evidence_requirement_ids: tuple[str, ...]
    evidence_blocked_requirement_ids: tuple[str, ...]
    incomplete_blocking_requirement_ids: tuple[str, ...]
    all_blocking_requirement_ids: tuple[str, ...]
    nonblocking_unverified_requirement_ids: tuple[str, ...]
    unsatisfied_blocking_requirement_ids: tuple[str, ...]
    blocking_reason_codes: tuple[str, ...]
    blocking_requirement_reasons: tuple[tuple[str, str], ...]
    evidence_total_by_level: Mapping[str, int]
    orphan_evidence_ids: tuple[str, ...]
    orphan_test_ids: tuple[str, ...]
    broken_reference_ids: tuple[str, ...]
    traceability_status: str
    blocker_ids: tuple[str, ...]
    coverage_ratio: float | None


@dataclass(frozen=True)
class RequirementsResult:
    status: str
    procurement_allowed: bool
    overall_system_readiness: str
    requirements_status: str
    evidence_ledger_status: str
    mass_ledger_status: str
    geometry_uncertainty_budget_status: str
    robust_geometry_status: str
    stow_requirements_status: str
    arm_radius_mass_coupling_status: str
    traceability_status: str
    readiness_gate: str
    blocking_reasons: tuple[str, ...]
    next_required_evidence: tuple[str, ...]
    config: RequirementsConfig
    requirements: tuple[RequirementRecord, ...]
    evidence: tuple[EvidenceRecord, ...]
    tests: tuple[TestRecord, ...]
    mass: MassBudgetResult
    uncertainty: UncertaintyBudgetResult
    arm_coupling: ArmCouplingResult
    stow: StowResult
    traceability: TraceabilityResult
