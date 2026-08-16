"""Fail-closed G3 readiness-gate priority.

The highest official outcome is EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS.
That is not a flyable, procurement, or hardware-validation conclusion.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Sequence

from arachne_hx6_analysis.requirements_types import (
    ARM_COUPLING_UNDETERMINED,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    GATE_EVIDENCE_COMPLETE_NEXT,
    GATE_UNDETERMINED_ARM_MASS_COUPLING,
    GATE_UNDETERMINED_EVIDENCE,
    GATE_UNDETERMINED_GEOMETRY_UNCERTAINTY,
    GATE_UNDETERMINED_MASS_LEDGER,
    GATE_UNDETERMINED_REQUIREMENTS,
    GATE_UNDETERMINED_STOW_REQUIREMENTS,
    GEOMETRY_BUDGET_INCOMPLETE,
    HARDWARE_SUFFICIENT_LEVELS,
    MASS_LEDGER_INCOMPLETE,
    REQUIREMENT_INCOMPLETE,
    REQUIREMENTS_INCOMPLETE,
    STOW_REQUIREMENTS_INCOMPLETE,
    TRACE_CONSISTENT,
    ArmCouplingResult,
    EvidenceRecord,
    MassBudgetResult,
    RequirementRecord,
    StowResult,
    TraceabilityResult,
    UncertaintyBudgetResult,
)


def select_readiness_gate(
    requirements: Sequence[RequirementRecord],
    evidence: Sequence[EvidenceRecord],
    mass: MassBudgetResult,
    uncertainty: UncertaintyBudgetResult,
    stow: StowResult,
    arm: ArmCouplingResult,
    trace: TraceabilityResult,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Return (gate, blocking_reasons, next_required_evidence)."""
    reasons: list[str] = []
    next_evidence: list[str] = []
    incomplete_reqs = [
        req.requirement_id
        for req in requirements
        if req.status == REQUIREMENT_INCOMPLETE
    ]
    if incomplete_reqs:
        reasons.append(
            'incomplete_requirements:' + ','.join(incomplete_reqs)
        )
    missing_evidence = [
        item.evidence_id
        for item in evidence
        if item.evidence_level == EVIDENCE_MISSING
    ]
    planning_evidence = [
        item.evidence_id
        for item in evidence
        if item.evidence_level == EVIDENCE_PLANNING_ASSUMPTION
    ]
    if missing_evidence:
        reasons.append('missing_evidence:' + ','.join(missing_evidence))
        next_evidence.extend(missing_evidence)
    if planning_evidence:
        reasons.append(
            'planning_assumption_not_hardware_evidence:'
            + ','.join(planning_evidence)
        )
    if mass.mass_ledger_status == MASS_LEDGER_INCOMPLETE:
        reasons.append(
            'mass_ledger_incomplete:' + ','.join(mass.missing_component_ids)
        )
    if uncertainty.geometry_uncertainty_budget_status == (
        GEOMETRY_BUDGET_INCOMPLETE
    ):
        reasons.append(
            'geometry_uncertainty_incomplete:'
            + ','.join(uncertainty.missing_source_ids)
        )
    if stow.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE:
        reasons.append(
            'stow_requirements_incomplete:' + ','.join(stow.missing_field_names)
        )
    if arm.arm_radius_mass_coupling_status == ARM_COUPLING_UNDETERMINED:
        reasons.append(
            'arm_radius_mass_coupling_undetermined:'
            + ','.join(arm.missing_field_names)
        )
    if trace.blocker_ids:
        reasons.append('blockers:' + ','.join(trace.blocker_ids))
    if trace.orphan_evidence_ids:
        reasons.append(
            'orphan_evidence:' + ','.join(trace.orphan_evidence_ids)
        )
    if trace.orphan_test_ids:
        reasons.append('orphan_test:' + ','.join(trace.orphan_test_ids))
    if trace.traceability_status != TRACE_CONSISTENT:
        reasons.append(
            'traceability_incomplete:' + trace.traceability_status
        )
    trace_blocks_next = (
        bool(trace.orphan_evidence_ids)
        or bool(trace.orphan_test_ids)
        or trace.traceability_status != TRACE_CONSISTENT
    )
    gate = GATE_EVIDENCE_COMPLETE_NEXT
    if incomplete_reqs:
        gate = GATE_UNDETERMINED_REQUIREMENTS
    elif (
        missing_evidence
        or planning_closes_hardware(evidence, requirements)
        or trace_blocks_next
    ):
        gate = GATE_UNDETERMINED_EVIDENCE
    elif mass.mass_ledger_status == MASS_LEDGER_INCOMPLETE:
        gate = GATE_UNDETERMINED_MASS_LEDGER
    elif uncertainty.geometry_uncertainty_budget_status == (
        GEOMETRY_BUDGET_INCOMPLETE
    ):
        gate = GATE_UNDETERMINED_GEOMETRY_UNCERTAINTY
    elif stow.stow_requirements_status == STOW_REQUIREMENTS_INCOMPLETE:
        gate = GATE_UNDETERMINED_STOW_REQUIREMENTS
    elif arm.arm_radius_mass_coupling_status == ARM_COUPLING_UNDETERMINED:
        gate = GATE_UNDETERMINED_ARM_MASS_COUPLING
    return gate, tuple(reasons), tuple(next_evidence)


def planning_closes_hardware(
    evidence: Sequence[EvidenceRecord],
    requirements: Sequence[RequirementRecord],
) -> bool:
    """True when a blocking requirement lacks sufficient hardware evidence.

    PLANNING_ASSUMPTION-only, mixed PLANNING_ASSUMPTION + MISSING, empty
    evidence IDs, and any remaining MISSING item all fail closed. Applies
    to qualitative and quantitative blocking requirements.
    """
    evidence_map = {item.evidence_id: item for item in evidence}
    for req in requirements:
        if not req.blocking:
            continue
        if not req.required_evidence_ids:
            return True
        levels = [
            evidence_map[evidence_id].evidence_level
            for evidence_id in req.required_evidence_ids
        ]
        if not levels:
            return True
        if any(level not in HARDWARE_SUFFICIENT_LEVELS for level in levels):
            return True
    return False


def requirements_status(requirements: Sequence[RequirementRecord]) -> str:
    """INCOMPLETE if any requirement lacks a real threshold or value."""
    if any(req.status == REQUIREMENT_INCOMPLETE for req in requirements):
        return REQUIREMENTS_INCOMPLETE
    return 'COMPLETE'


def evidence_status_from_trace(trace: TraceabilityResult) -> str:
    """Ledger is incomplete while any required hardware evidence is missing."""
    missing = trace.evidence_total_by_level.get(EVIDENCE_MISSING, 0)
    planning = trace.evidence_total_by_level.get(
        EVIDENCE_PLANNING_ASSUMPTION, 0
    )
    if missing or planning or trace.blocker_ids:
        return REQUIREMENTS_INCOMPLETE
    return 'COMPLETE'
