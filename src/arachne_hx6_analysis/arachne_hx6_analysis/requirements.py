"""G3 requirements, evidence-ledger, and uncertainty-gate orchestration.

Does not modify G1 URDF, G1.5 propulsion math, or G2 architecture
semantics. Highest official outcome is EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from arachne_hx6_analysis.evidence_ledger import (
    evidence_by_id,
    evidence_ledger_status,
)
from arachne_hx6_analysis.mass_budget import evaluate_mass_budget
from arachne_hx6_analysis.readiness_gates import (
    evidence_status_from_trace,
    requirements_status,
    select_readiness_gate,
)
from arachne_hx6_analysis.requirements_loader import (
    default_config_paths,
    load_requirements_config,
)
from arachne_hx6_analysis.requirements_types import (
    OVERALL_SYSTEM_READINESS,
    STOW_GATE_UNDETERMINED,
    STOW_HARDWARE_NOT_PERFORMED,
    STOW_POSE_EVIDENCE_UNQUALIFIED,
    STOW_REQUIREMENTS_COMPLETE,
    STOW_REQUIREMENTS_INCOMPLETE,
    RequirementsConfig,
    RequirementsResult,
    StowContract,
    StowResult,
)
from arachne_hx6_analysis.traceability import evaluate_traceability
from arachne_hx6_analysis.uncertainty_budget import (
    evaluate_arm_coupling,
    evaluate_uncertainty_budget,
)

STOW_NUMERIC_FIELDS = (
    'maximum_stowed_length_m',
    'maximum_stowed_width_m',
    'maximum_stowed_height_m',
    'minimum_rotor_to_leg_clearance_m',
    'maximum_transition_time_s',
    'actuator_torque_lower_nm',
    'actuator_torque_upper_nm',
    'lock_load_capacity_n',
    'lock_stiffness_nm_per_rad',
    'position_repeatability_rad',
)
STOW_TEXT_FIELDS = (
    'power_loss_safe_state',
    'landing_deployment_condition',
    'flight_lock_verification_method',
    'emergency_recovery_requirement',
)


def evaluate_requirements(
    config: RequirementsConfig,
) -> RequirementsResult:
    """Evaluate the G3 contract. Never a procurement or flyable result."""
    evidence_map = evidence_by_id(config.evidence)
    mass = evaluate_mass_budget(config.mass_components, evidence_map)
    uncertainty = evaluate_uncertainty_budget(
        config.uncertainty_sources,
        config.combination_method,
        config.nominal_clearance_margin_m,
    )
    arm = evaluate_arm_coupling(config.arm_coupling)
    stow = evaluate_stow(config.stow)
    trace = evaluate_traceability(
        config.requirements, config.evidence, config.tests
    )
    req_status = requirements_status(config.requirements)
    ev_status = evidence_ledger_status(config.requirements, evidence_map)
    if ev_status == 'COMPLETE':
        ev_status = evidence_status_from_trace(trace)
    gate, reasons, next_evidence = select_readiness_gate(
        config.requirements,
        config.evidence,
        mass,
        uncertainty,
        stow,
        arm,
        trace,
    )
    return RequirementsResult(
        status='ANALYSIS_ONLY',
        procurement_allowed=False,
        overall_system_readiness=OVERALL_SYSTEM_READINESS,
        requirements_status=req_status,
        evidence_ledger_status=ev_status,
        mass_ledger_status=mass.mass_ledger_status,
        geometry_uncertainty_budget_status=(
            uncertainty.geometry_uncertainty_budget_status
        ),
        robust_geometry_status=uncertainty.robust_geometry_status,
        stow_requirements_status=stow.stow_requirements_status,
        arm_radius_mass_coupling_status=arm.arm_radius_mass_coupling_status,
        traceability_status=trace.traceability_status,
        readiness_gate=gate,
        blocking_reasons=reasons,
        next_required_evidence=next_evidence,
        config=config,
        requirements=config.requirements,
        evidence=config.evidence,
        tests=config.tests,
        mass=mass,
        uncertainty=uncertainty,
        arm_coupling=arm,
        stow=stow,
        traceability=trace,
    )


def evaluate_stow(contract: StowContract) -> StowResult:
    """Stow hardware limits stay incomplete until every field is present."""
    missing = [
        name
        for name in STOW_NUMERIC_FIELDS + STOW_TEXT_FIELDS
        if getattr(contract, name) is None
    ]
    if missing:
        status = STOW_REQUIREMENTS_INCOMPLETE
        gate = STOW_GATE_UNDETERMINED
    else:
        status = STOW_REQUIREMENTS_COMPLETE
        gate = STOW_GATE_UNDETERMINED
    return StowResult(
        stow_requirements_status=status,
        stow_pose_evidence_status=STOW_POSE_EVIDENCE_UNQUALIFIED,
        stow_hardware_validation_status=STOW_HARDWARE_NOT_PERFORMED,
        stow_gate=gate,
        missing_field_names=tuple(missing),
        contract=contract,
    )


__all__ = [
    'default_config_paths',
    'evaluate_requirements',
    'evaluate_stow',
    'load_requirements_config',
]
