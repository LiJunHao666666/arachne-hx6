"""Official G3 JSON payload. Field names are part of the report contract.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Any

from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
)
from arachne_hx6_analysis.requirements_types import (
    OVERALL_SYSTEM_READINESS,
    RequirementsResult,
)


def build_requirements_json(
    result: RequirementsResult,
    generated_at: str,
) -> dict[str, Any]:
    """Official requirements / evidence snapshot."""
    return {
        'status': STATUS_ANALYSIS_ONLY,
        'procurement_allowed': False,
        'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
        'overall_system_readiness': OVERALL_SYSTEM_READINESS,
        'requirements_status': result.requirements_status,
        'evidence_ledger_status': result.evidence_ledger_status,
        'mass_ledger_status': result.mass_ledger_status,
        'component_mass_interval_status': (
            result.mass.component_mass_interval_status
        ),
        'total_mass_lower_kg': result.mass.total_mass_lower_kg,
        'total_mass_upper_kg': result.mass.total_mass_upper_kg,
        'missing_component_ids': list(result.mass.missing_component_ids),
        'planning_scenario_comparison': dict(
            result.mass.planning_scenario_comparison
        ),
        'whole_vehicle_energy_mass_closure_claimed': (
            result.mass.whole_vehicle_energy_mass_closure_claimed
        ),
        'geometry_uncertainty_budget_status': (
            result.geometry_uncertainty_budget_status
        ),
        'total_geometry_uncertainty_allowance_m': (
            result.uncertainty.total_geometry_uncertainty_allowance_m
        ),
        'robust_clearance_margin_m': result.uncertainty.robust_clearance_margin_m,
        'robust_geometry_status': result.robust_geometry_status,
        'stow_requirements_status': result.stow_requirements_status,
        'stow_pose_evidence_status': result.stow.stow_pose_evidence_status,
        'stow_hardware_validation_status': (
            result.stow.stow_hardware_validation_status
        ),
        'stow_gate': result.stow.stow_gate,
        'arm_radius_mass_coupling_status': (
            result.arm_radius_mass_coupling_status
        ),
        'arm_extension_mass_lower_kg': (
            result.arm_coupling.arm_extension_mass_lower_kg
        ),
        'arm_extension_mass_upper_kg': (
            result.arm_coupling.arm_extension_mass_upper_kg
        ),
        'traceability_status': result.traceability_status,
        'readiness_gate': result.readiness_gate,
        **_requirement_set_contract(result),
        'blocker_ids': list(result.traceability.blocker_ids),
        'orphan_evidence_ids': list(result.traceability.orphan_evidence_ids),
        'orphan_test_ids': list(result.traceability.orphan_test_ids),
        'broken_reference_ids': list(result.traceability.broken_reference_ids),
        'blocking_reasons': list(result.blocking_reasons),
        'next_required_evidence': list(result.next_required_evidence),
        'generated_at_utc': generated_at,
        'traceability': {
            **_requirement_set_contract(result),
            'specified_means_clause_written_not_verified_or_satisfied': True,
            'planning_assumption_does_not_count_as_verified_or_satisfied': True,
            'planning_assumption_is_not_sufficient_evidence': True,
            'g3_completion_does_not_unlock_procurement': True,
            'evidence_total_by_level': dict(
                result.traceability.evidence_total_by_level
            ),
            'coverage_ratio': result.traceability.coverage_ratio,
            'coverage_is_not_a_pass_criterion': True,
        },
        'requirements': [
            _requirement_dict(
                item,
                dict(result.traceability.blocking_requirement_reasons),
                result.traceability,
            )
            for item in result.requirements
        ],
        'evidence': [_evidence_dict(item) for item in result.evidence],
        'tests': [_test_dict(item) for item in result.tests],
        'mass_ledger': {
            'status': result.mass.mass_ledger_status,
            'component_mass_interval_status': (
                result.mass.component_mass_interval_status
            ),
            'items': [_mass_dict(item) for item in result.mass.components],
        },
        'geometry_uncertainty_budget': {
            'status': result.uncertainty.geometry_uncertainty_budget_status,
            'combination_method': result.uncertainty.combination_method,
            'sources': [
                {
                    'source_id': source.source_id,
                    'lower_m': source.lower_m,
                    'upper_m': source.upper_m,
                    'allowance_m': source.allowance_m,
                    'unit': source.unit,
                    'evidence_id': source.evidence_id,
                    'notes': source.notes,
                }
                for source in result.uncertainty.sources
            ],
            'missing_source_ids': list(result.uncertainty.missing_source_ids),
        },
        'arm_radius_mass_coupling': {
            'status': result.arm_radius_mass_coupling_status,
            'baseline_radius_m': result.config.arm_coupling.baseline_radius_m,
            'candidate_radius_m': result.config.arm_coupling.candidate_radius_m,
            'extension_length_per_arm_m': (
                result.arm_coupling.extension_length_per_arm_m
            ),
            'arm_count': result.config.arm_coupling.arm_count,
            'arm_extension_mass_lower_kg': (
                result.arm_coupling.arm_extension_mass_lower_kg
            ),
            'arm_extension_mass_upper_kg': (
                result.arm_coupling.arm_extension_mass_upper_kg
            ),
            'missing_field_names': list(result.arm_coupling.missing_field_names),
            'evidence_ids': list(result.config.arm_coupling.evidence_ids),
        },
        'stow_requirements': {
            **result.stow.contract.__dict__,
            'stow_requirements_status': result.stow.stow_requirements_status,
            'stow_pose_evidence_status': result.stow.stow_pose_evidence_status,
            'stow_hardware_validation_status': (
                result.stow.stow_hardware_validation_status
            ),
            'stow_gate': result.stow.stow_gate,
            'missing_field_names': list(result.stow.missing_field_names),
        },
        'inputs': {
            'requirements_path': str(result.config.requirements_path),
            'evidence_path': str(result.config.evidence_path),
            'uncertainty_path': str(result.config.uncertainty_path),
            'stow_path': str(result.config.stow_path),
            'notes': result.config.notes,
        },
    }


def _requirement_set_contract(result: RequirementsResult) -> dict[str, Any]:
    """Official requirement-set counts and sorted unique ID lists."""
    trace = result.traceability
    return {
        'requirements_total': trace.requirements_total,
        'requirements_specified': trace.requirements_specified,
        'requirements_incomplete_specification': (
            trace.requirements_incomplete_specification
        ),
        'requirements_verified': trace.requirements_verified,
        'requirements_satisfied': trace.requirements_satisfied,
        'specified_requirement_ids': list(trace.specified_requirement_ids),
        'incomplete_specification_requirement_ids': list(
            trace.incomplete_specification_requirement_ids
        ),
        'verified_requirement_ids': list(trace.verified_requirement_ids),
        'satisfied_requirement_ids': list(trace.satisfied_requirement_ids),
        'missing_evidence_requirement_ids': list(
            trace.missing_evidence_requirement_ids
        ),
        'planning_assumption_only_requirement_ids': list(
            trace.planning_assumption_only_requirement_ids
        ),
        'mixed_insufficient_evidence_requirement_ids': list(
            trace.mixed_insufficient_evidence_requirement_ids
        ),
        'sufficient_evidence_requirement_ids': list(
            trace.sufficient_evidence_requirement_ids
        ),
        'evidence_blocked_requirement_ids': list(
            trace.evidence_blocked_requirement_ids
        ),
        'incomplete_blocking_requirement_ids': list(
            trace.incomplete_blocking_requirement_ids
        ),
        'all_blocking_requirement_ids': list(trace.all_blocking_requirement_ids),
        'nonblocking_unverified_requirement_ids': list(
            trace.nonblocking_unverified_requirement_ids
        ),
        'unsatisfied_blocking_requirement_ids': list(
            trace.unsatisfied_blocking_requirement_ids
        ),
        'blocking_reason_codes': list(trace.blocking_reason_codes),
        'blocking_requirement_reasons': [
            {'requirement_id': req_id, 'reason_code': code}
            for req_id, code in trace.blocking_requirement_reasons
        ],
    }


def _requirement_dict(item, reasons, trace) -> dict[str, Any]:
    req_id = item.requirement_id
    return {
        'requirement_id': req_id,
        'title': item.title,
        'category': item.category,
        'description': item.description,
        'rationale': item.rationale,
        'verification_method': item.verification_method,
        'required_evidence_ids': list(item.required_evidence_ids),
        'linked_test_ids': list(item.linked_test_ids),
        'linked_report_fields': list(item.linked_report_fields),
        'threshold': item.threshold,
        'value': item.value,
        'range_lower': item.range_lower,
        'range_upper': item.range_upper,
        'unit': item.unit,
        'applicability': item.applicability,
        'blocking': item.blocking,
        'kind': item.kind,
        'status': item.status,
        'blocking_reason_code': reasons.get(req_id),
        'is_specified': req_id in trace.specified_requirement_ids,
        'is_incomplete_specification': (
            req_id in trace.incomplete_specification_requirement_ids
        ),
        'is_verified': req_id in trace.verified_requirement_ids,
        'is_satisfied': req_id in trace.satisfied_requirement_ids,
        'is_missing_evidence': req_id in trace.missing_evidence_requirement_ids,
        'is_planning_assumption_only': (
            req_id in trace.planning_assumption_only_requirement_ids
        ),
        'is_mixed_insufficient_evidence': (
            req_id in trace.mixed_insufficient_evidence_requirement_ids
        ),
        'is_sufficient_evidence': (
            req_id in trace.sufficient_evidence_requirement_ids
        ),
        'is_evidence_blocked': req_id in trace.evidence_blocked_requirement_ids,
        'is_incomplete_blocking': (
            req_id in trace.incomplete_blocking_requirement_ids
        ),
        'is_all_blocking': req_id in trace.all_blocking_requirement_ids,
        'is_nonblocking_unverified': (
            req_id in trace.nonblocking_unverified_requirement_ids
        ),
        'is_unsatisfied_blocking': (
            req_id in trace.unsatisfied_blocking_requirement_ids
        ),
        'notes': item.notes,
    }


def _evidence_dict(item) -> dict[str, Any]:
    return {
        'evidence_id': item.evidence_id,
        'component_id': item.component_id,
        'parameter': item.parameter,
        'evidence_level': item.evidence_level,
        'value': item.value,
        'lower': item.lower,
        'upper': item.upper,
        'unit': item.unit,
        'source': item.source,
        'source_date': item.source_date,
        'measurement_method': item.measurement_method,
        'sample_count': item.sample_count,
        'uncertainty': item.uncertainty,
        'linked_requirement_ids': list(item.linked_requirement_ids),
        'status': item.status,
        'notes': item.notes,
        'vendor': item.vendor,
        'model': item.model,
        'access_date': item.access_date,
        'measurement_equipment': item.measurement_equipment,
        'measurement_time': item.measurement_time,
        'test_id': item.test_id,
        'test_conditions': item.test_conditions,
        'raw_result': item.raw_result,
        'verdict': item.verdict,
        'uncertainty_unit': item.uncertainty_unit,
    }


def _test_dict(item) -> dict[str, Any]:
    return {
        'test_id': item.test_id,
        'title': item.title,
        'method': item.method,
        'linked_requirement_ids': list(item.linked_requirement_ids),
        'status': item.status,
        'notes': item.notes,
    }


def _mass_dict(item) -> dict[str, Any]:
    return {
        'component_id': item.component_id,
        'quantity': item.quantity,
        'mass_lower_kg': item.mass_lower_kg,
        'mass_upper_kg': item.mass_upper_kg,
        'evidence_id': item.evidence_id,
        'evidence_level': item.evidence_level,
        'completeness_status': item.completeness_status,
        'notes': item.notes,
    }
