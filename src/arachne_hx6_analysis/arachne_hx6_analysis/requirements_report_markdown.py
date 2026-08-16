"""Markdown serialization of the G3 requirements and evidence report.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
)
from arachne_hx6_analysis.requirements_types import (
    OVERALL_SYSTEM_READINESS,
    RequirementsResult,
)

MD_NULL = '—'


def render_requirements_markdown(
    result: RequirementsResult,
    generated_at: str,
) -> str:
    """Human-review Markdown. Values only; never a procurement list."""
    trace = result.traceability
    lines = [
        '# Arachne-HX6 G3 Requirements, Evidence Ledger, and Uncertainty Gates',
        '',
        f'**{STATUS_ANALYSIS_ONLY}**',
        f'**{STATUS_NOT_FOR_PROCUREMENT}**',
        f'**overall_system_readiness: {OVERALL_SYSTEM_READINESS}**',
        f'**readiness_gate: {result.readiness_gate}**',
        f'**procurement_allowed: {str(result.procurement_allowed).lower()}**',
        '',
        f'- Generated (UTC): `{generated_at}`',
        '- These records are engineering contracts, not a buy list.',
        '- Missing values stay null / empty / `—`. They are never treated as 0.',
        '- Highest possible G3 outcome is `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`.',
        '',
        '## Top-level statuses',
        '',
        f'- requirements_status: `{result.requirements_status}`',
        f'- evidence_ledger_status: `{result.evidence_ledger_status}`',
        f'- mass_ledger_status: `{result.mass_ledger_status}`',
        f'- component_mass_interval_status: '
        f'`{result.mass.component_mass_interval_status}`',
        f'- total_mass_lower_kg: {_md_num(result.mass.total_mass_lower_kg)}',
        f'- total_mass_upper_kg: {_md_num(result.mass.total_mass_upper_kg)}',
        f'- geometry_uncertainty_budget_status: '
        f'`{result.geometry_uncertainty_budget_status}`',
        f'- total_geometry_uncertainty_allowance_m: '
        f'{_md_num(result.uncertainty.total_geometry_uncertainty_allowance_m)}',
        f'- robust_clearance_margin_m: '
        f'{_md_num(result.uncertainty.robust_clearance_margin_m)}',
        f'- robust_geometry_status: `{result.robust_geometry_status}`',
        f'- stow_requirements_status: `{result.stow_requirements_status}`',
        f'- stow_pose_evidence_status: `{result.stow.stow_pose_evidence_status}`',
        f'- stow_hardware_validation_status: '
        f'`{result.stow.stow_hardware_validation_status}`',
        f'- stow_gate: `{result.stow.stow_gate}`',
        f'- arm_radius_mass_coupling_status: '
        f'`{result.arm_radius_mass_coupling_status}`',
        f'- arm_extension_mass_lower_kg: '
        f'{_md_num(result.arm_coupling.arm_extension_mass_lower_kg)}',
        f'- arm_extension_mass_upper_kg: '
        f'{_md_num(result.arm_coupling.arm_extension_mass_upper_kg)}',
        f'- traceability_status: `{result.traceability_status}`',
        f'- whole_vehicle_energy_mass_closure_claimed: '
        f'`{result.mass.whole_vehicle_energy_mass_closure_claimed}`',
        '',
        '## Requirement sets',
        '',
        '- SPECIFIED means the requirement clause is written. It is not',
        '  verification and not satisfaction.',
        '- PLANNING_ASSUMPTION does not increase requirements_verified or',
        '  requirements_satisfied, and is not sufficient evidence.',
        '- incomplete_specification is a missing numeric clause, not the',
        '  blocker union.',
        '- evidence_blocked is SPECIFIED and blocking, but evidence is not',
        '  sufficient: no evidence IDs, all MISSING, all',
        '  PLANNING_ASSUMPTION, or a mixed insufficient set.',
        '- all_blocking_requirement_ids is the sorted unique union of',
        '  incomplete_blocking_requirement_ids and',
        '  evidence_blocked_requirement_ids. The count is computed, not',
        '  hardcoded.',
        '- Completing G3 does not unlock procurement, physical assembly, or',
        '  the next stage.',
        '',
        f'- requirements_total: {trace.requirements_total}',
        f'- requirements_specified: {trace.requirements_specified}',
        f'- specified_requirement_ids: {_md_list(trace.specified_requirement_ids)}',
        f'- requirements_incomplete_specification: '
        f'{trace.requirements_incomplete_specification}',
        f'- incomplete_specification_requirement_ids: '
        f'{_md_list(trace.incomplete_specification_requirement_ids)}',
        f'- requirements_verified: {trace.requirements_verified}',
        f'- verified_requirement_ids: {_md_list(trace.verified_requirement_ids)}',
        f'- requirements_satisfied: {trace.requirements_satisfied}',
        f'- satisfied_requirement_ids: {_md_list(trace.satisfied_requirement_ids)}',
        f'- missing_evidence_requirement_ids: '
        f'{_md_list(trace.missing_evidence_requirement_ids)}',
        f'- planning_assumption_only_requirement_ids: '
        f'{_md_list(trace.planning_assumption_only_requirement_ids)}',
        f'- mixed_insufficient_evidence_requirement_ids: '
        f'{_md_list(trace.mixed_insufficient_evidence_requirement_ids)}',
        f'- sufficient_evidence_requirement_ids: '
        f'{_md_list(trace.sufficient_evidence_requirement_ids)}',
        f'- incomplete_blocking_requirement_ids: '
        f'{_md_list(trace.incomplete_blocking_requirement_ids)}',
        f'- evidence_blocked_requirement_ids: '
        f'{_md_list(trace.evidence_blocked_requirement_ids)}',
        f'- all_blocking_requirement_ids: '
        f'{_md_list(trace.all_blocking_requirement_ids)}',
        f'- nonblocking_unverified_requirement_ids: '
        f'{_md_list(trace.nonblocking_unverified_requirement_ids)}',
        f'- unsatisfied_blocking_requirement_ids: '
        f'{_md_list(trace.unsatisfied_blocking_requirement_ids)}',
        f'- blocking_reason_codes: {_md_list(trace.blocking_reason_codes)}',
        '',
        '## Traceability',
        '',
        f'- coverage_ratio: {_md_num(trace.coverage_ratio)} '
        '(diagnostic only; specified / total; not a pass criterion)',
        f'- blocker_ids: {_md_list(trace.blocker_ids)}',
        f'- orphan_evidence_ids: {_md_list(trace.orphan_evidence_ids)}',
        f'- orphan_test_ids: {_md_list(trace.orphan_test_ids)}',
        f'- broken_reference_ids: {_md_list(trace.broken_reference_ids)}',
        '',
        'Evidence counts by level:',
        '',
    ]
    for level, count in result.traceability.evidence_total_by_level.items():
        lines.append(f'- `{level}`: {count}')
    lines.extend(
        [
            '',
            '## Requirements',
            '',
            '| ID | category | status | blocking | kind | reason | evidence |',
            '|---|---|---|---|---|---|---|',
        ]
    )
    reason_by_id = dict(trace.blocking_requirement_reasons)
    for item in result.requirements:
        lines.append(
            '| {rid} | `{cat}` | `{status}` | {blk} | {kind} | {reason} | {ev} |'.format(
                rid=item.requirement_id,
                cat=item.category,
                status=item.status,
                blk='yes' if item.blocking else 'no',
                kind=item.kind,
                reason=reason_by_id.get(item.requirement_id) or MD_NULL,
                ev=','.join(item.required_evidence_ids) or MD_NULL,
            )
        )
    lines.extend(
        [
            '',
            '## Mass ledger (G2 19 items)',
            '',
            '| component_id | qty | lower_kg | upper_kg | evidence | level | status |',
            '|---|---:|---:|---:|---|---|---|',
        ]
    )
    for item in result.mass.components:
        lines.append(
            '| `{cid}` | {qty} | {lo} | {hi} | `{ev}` | `{lvl}` | `{st}` |'.format(
                cid=item.component_id,
                qty=item.quantity,
                lo=_md_num(item.mass_lower_kg),
                hi=_md_num(item.mass_upper_kg),
                ev=item.evidence_id,
                lvl=item.evidence_level,
                st=item.completeness_status,
            )
        )
    comparison = result.mass.planning_scenario_comparison
    lines.extend(
        [
            '',
            '## Planning scenario comparison',
            '',
            f'- used_as_part_evidence: `{comparison["used_as_part_evidence"]}`',
            f'- comparison_status: `{comparison["comparison_status"]}`',
            f'- {comparison["notes"]}',
            '',
            '| scenario | non_battery_mass_kg | inside_computed_interval |',
            '|---|---:|---|',
        ]
    )
    for row in comparison['scenarios']:
        inside = row['inside_computed_interval']
        inside_text = MD_NULL if inside is None else str(inside)
        lines.append(
            f'| `{row["name"]}` | {row["non_battery_mass_kg"]} | {inside_text} |'
        )
    lines.extend(
        [
            '',
            '## Geometry uncertainty sources',
            '',
            f'- combination_method: '
            f'`{result.uncertainty.combination_method or MD_NULL}`',
            '',
            '| source_id | lower_m | upper_m | allowance_m | evidence |',
            '|---|---:|---:|---:|---|',
        ]
    )
    for source in result.uncertainty.sources:
        lines.append(
            '| `{sid}` | {lo} | {hi} | {al} | `{ev}` |'.format(
                sid=source.source_id,
                lo=_md_num(source.lower_m),
                hi=_md_num(source.upper_m),
                al=_md_num(source.allowance_m),
                ev=source.evidence_id,
            )
        )
    lines.extend(
        [
            '',
            '## Next required evidence',
            '',
        ]
    )
    if result.next_required_evidence:
        for evidence_id in result.next_required_evidence:
            lines.append(f'- `{evidence_id}`')
    else:
        lines.append(f'- {MD_NULL}')
    lines.extend(
        [
            '',
            '## Blocking reasons',
            '',
        ]
    )
    if result.blocking_reasons:
        for reason in result.blocking_reasons:
            lines.append(f'- `{reason}`')
    else:
        lines.append(f'- {MD_NULL}')
    lines.extend(
        [
            '',
            f'**{STATUS_ANALYSIS_ONLY} / {STATUS_NOT_FOR_PROCUREMENT}**',
            '',
        ]
    )
    return '\n'.join(lines)


def _md_num(value: float | None) -> str:
    if value is None:
        return MD_NULL
    return f'{value:.6g}'


def _md_list(values) -> str:
    if not values:
        return MD_NULL
    return ', '.join(f'`{item}`' for item in values)
