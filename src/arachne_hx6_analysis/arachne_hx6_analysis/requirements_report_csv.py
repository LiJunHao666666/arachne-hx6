"""CSV serialization of official G3 requirement rows.

Null cells stay empty. Never write 0 for a missing value.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import csv
from io import StringIO
import math
from typing import Any

from arachne_hx6_analysis.model import (
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
)
from arachne_hx6_analysis.requirements_types import (
    OVERALL_SYSTEM_READINESS,
    RequirementsResult,
)


def _csv_cell(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidInputError(f'CSV value is not finite: {value!r}')
        if abs(value) < 1.0e-3 and value != 0.0:
            return repr(value)
        return f'{value:.8f}'.rstrip('0').rstrip('.')
    if isinstance(value, (list, tuple)):
        return ','.join(str(item) for item in value)
    return str(value)


def render_requirements_csv(result: RequirementsResult) -> str:
    fieldnames = [
        'status',
        'not_for_procurement',
        'procurement_allowed',
        'overall_system_readiness',
        'readiness_gate',
        'requirements_status',
        'evidence_ledger_status',
        'mass_ledger_status',
        'geometry_uncertainty_budget_status',
        'robust_geometry_status',
        'stow_requirements_status',
        'stow_gate',
        'arm_radius_mass_coupling_status',
        'traceability_status',
        'requirements_total',
        'requirements_specified',
        'requirements_incomplete_specification',
        'requirements_verified',
        'requirements_satisfied',
        'is_specified',
        'is_incomplete_specification',
        'is_verified',
        'is_satisfied',
        'is_missing_evidence',
        'is_planning_assumption_only',
        'is_mixed_insufficient_evidence',
        'is_sufficient_evidence',
        'is_evidence_blocked',
        'is_incomplete_blocking',
        'is_all_blocking',
        'is_nonblocking_unverified',
        'is_unsatisfied_blocking',
        'requirement_blocking_reason_code',
        'blocking_reason_codes',
        'requirement_id',
        'title',
        'category',
        'requirement_status',
        'blocking',
        'kind',
        'verification_method',
        'unit',
        'threshold',
        'value',
        'range_lower',
        'range_upper',
        'required_evidence_ids',
        'linked_test_ids',
        'linked_report_fields',
        'total_mass_lower_kg',
        'total_mass_upper_kg',
        'arm_extension_mass_lower_kg',
        'arm_extension_mass_upper_kg',
        'total_geometry_uncertainty_allowance_m',
        'robust_clearance_margin_m',
    ]
    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    trace = result.traceability
    specified = set(trace.specified_requirement_ids)
    incomplete = set(trace.incomplete_specification_requirement_ids)
    verified = set(trace.verified_requirement_ids)
    satisfied = set(trace.satisfied_requirement_ids)
    missing_evidence = set(trace.missing_evidence_requirement_ids)
    planning_only = set(trace.planning_assumption_only_requirement_ids)
    mixed_insufficient = set(trace.mixed_insufficient_evidence_requirement_ids)
    sufficient = set(trace.sufficient_evidence_requirement_ids)
    evidence_blocked = set(trace.evidence_blocked_requirement_ids)
    incomplete_blocking = set(trace.incomplete_blocking_requirement_ids)
    all_blocking = set(trace.all_blocking_requirement_ids)
    nonblocking_unverified = set(trace.nonblocking_unverified_requirement_ids)
    unsatisfied_blocking = set(trace.unsatisfied_blocking_requirement_ids)
    reason_by_id = dict(trace.blocking_requirement_reasons)
    for item in result.requirements:
        writer.writerow(
            {
                'status': STATUS_ANALYSIS_ONLY,
                'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
                'procurement_allowed': _csv_cell(result.procurement_allowed),
                'overall_system_readiness': OVERALL_SYSTEM_READINESS,
                'readiness_gate': result.readiness_gate,
                'requirements_status': result.requirements_status,
                'evidence_ledger_status': result.evidence_ledger_status,
                'mass_ledger_status': result.mass_ledger_status,
                'geometry_uncertainty_budget_status': (
                    result.geometry_uncertainty_budget_status
                ),
                'robust_geometry_status': result.robust_geometry_status,
                'stow_requirements_status': result.stow_requirements_status,
                'stow_gate': result.stow.stow_gate,
                'arm_radius_mass_coupling_status': (
                    result.arm_radius_mass_coupling_status
                ),
                'traceability_status': result.traceability_status,
                'requirements_total': _csv_cell(trace.requirements_total),
                'requirements_specified': _csv_cell(trace.requirements_specified),
                'requirements_incomplete_specification': _csv_cell(
                    trace.requirements_incomplete_specification
                ),
                'requirements_verified': _csv_cell(trace.requirements_verified),
                'requirements_satisfied': _csv_cell(trace.requirements_satisfied),
                'is_specified': _csv_cell(item.requirement_id in specified),
                'is_incomplete_specification': _csv_cell(
                    item.requirement_id in incomplete
                ),
                'is_verified': _csv_cell(item.requirement_id in verified),
                'is_satisfied': _csv_cell(item.requirement_id in satisfied),
                'is_missing_evidence': _csv_cell(
                    item.requirement_id in missing_evidence
                ),
                'is_planning_assumption_only': _csv_cell(
                    item.requirement_id in planning_only
                ),
                'is_mixed_insufficient_evidence': _csv_cell(
                    item.requirement_id in mixed_insufficient
                ),
                'is_sufficient_evidence': _csv_cell(
                    item.requirement_id in sufficient
                ),
                'is_evidence_blocked': _csv_cell(
                    item.requirement_id in evidence_blocked
                ),
                'is_incomplete_blocking': _csv_cell(
                    item.requirement_id in incomplete_blocking
                ),
                'is_all_blocking': _csv_cell(item.requirement_id in all_blocking),
                'is_nonblocking_unverified': _csv_cell(
                    item.requirement_id in nonblocking_unverified
                ),
                'is_unsatisfied_blocking': _csv_cell(
                    item.requirement_id in unsatisfied_blocking
                ),
                'requirement_blocking_reason_code': _csv_cell(
                    reason_by_id.get(item.requirement_id)
                ),
                'blocking_reason_codes': _csv_cell(trace.blocking_reason_codes),
                'requirement_id': item.requirement_id,
                'title': item.title,
                'category': item.category,
                'requirement_status': item.status,
                'blocking': _csv_cell(item.blocking),
                'kind': item.kind,
                'verification_method': item.verification_method,
                'unit': _csv_cell(item.unit),
                'threshold': _csv_cell(item.threshold),
                'value': _csv_cell(item.value),
                'range_lower': _csv_cell(item.range_lower),
                'range_upper': _csv_cell(item.range_upper),
                'required_evidence_ids': _csv_cell(item.required_evidence_ids),
                'linked_test_ids': _csv_cell(item.linked_test_ids),
                'linked_report_fields': _csv_cell(item.linked_report_fields),
                'total_mass_lower_kg': _csv_cell(result.mass.total_mass_lower_kg),
                'total_mass_upper_kg': _csv_cell(result.mass.total_mass_upper_kg),
                'arm_extension_mass_lower_kg': _csv_cell(
                    result.arm_coupling.arm_extension_mass_lower_kg
                ),
                'arm_extension_mass_upper_kg': _csv_cell(
                    result.arm_coupling.arm_extension_mass_upper_kg
                ),
                'total_geometry_uncertainty_allowance_m': _csv_cell(
                    result.uncertainty.total_geometry_uncertainty_allowance_m
                ),
                'robust_clearance_margin_m': _csv_cell(
                    result.uncertainty.robust_clearance_margin_m
                ),
            }
        )
    return handle.getvalue()
