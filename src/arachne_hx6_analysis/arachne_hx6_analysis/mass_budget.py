"""G2 19-item mass ledger interval propagation.

Missing or null masses stay null. They are never treated as zero.
G1.5 7.16 / 12 / 16 kg planning scenarios are comparison labels only
and are never written into the component ledger.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from arachne_hx6_analysis.architecture_types import REQUIRED_MASS_LEDGER_ITEMS
from arachne_hx6_analysis.evidence_ledger import hardware_evidence_is_sufficient
from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.requirements_types import (
    COMPONENT_COMPLETE,
    COMPONENT_INCOMPLETE,
    COMPONENT_INTERVAL_COMPLETE,
    COMPONENT_INTERVAL_INCOMPLETE,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    MASS_LEDGER_COMPLETE,
    MASS_LEDGER_INCOMPLETE,
    PLANNING_COMPARISON_INTERVAL_ONLY,
    PLANNING_COMPARISON_NOT_APPLICABLE,
    EvidenceRecord,
    MassBudgetResult,
    MassComponent,
)


G1_5_PLANNING_SCENARIOS = (
    ('g1_placeholder', 7.16),
    ('planned', 12.0),
    ('growth', 16.0),
)


def evaluate_mass_budget(
    components: Sequence[MassComponent],
    evidence: Mapping[str, EvidenceRecord],
) -> MassBudgetResult:
    """Propagate component intervals or keep the official total null."""
    _require_g2_component_set(components)
    completed: list[MassComponent] = []
    missing: list[str] = []
    for item in components:
        record = evidence.get(item.evidence_id)
        level = record.evidence_level if record is not None else EVIDENCE_MISSING
        lower = item.mass_lower_kg
        upper = item.mass_upper_kg
        if record is not None:
            if lower is None:
                lower = record.lower
            if upper is None:
                upper = record.upper
        complete = (
            lower is not None
            and upper is not None
            and level != EVIDENCE_MISSING
        )
        status = COMPONENT_COMPLETE if complete else COMPONENT_INCOMPLETE
        if not complete:
            missing.append(item.component_id)
        completed.append(
            MassComponent(
                component_id=item.component_id,
                quantity=item.quantity,
                mass_lower_kg=lower,
                mass_upper_kg=upper,
                evidence_id=item.evidence_id,
                evidence_level=level,
                completeness_status=status,
                notes=item.notes,
            )
        )
    interval_ready = not missing and all(
        row.mass_lower_kg is not None and row.mass_upper_kg is not None
        for row in completed
    )
    if interval_ready:
        total_lower = 0.0
        total_upper = 0.0
        for row in completed:
            total_lower += float(row.quantity) * float(row.mass_lower_kg)
            total_upper += float(row.quantity) * float(row.mass_upper_kg)
        interval_status = COMPONENT_INTERVAL_COMPLETE
    else:
        total_lower = None
        total_upper = None
        interval_status = COMPONENT_INTERVAL_INCOMPLETE
    hardware_complete = interval_ready and all(
        hardware_evidence_is_sufficient(row.evidence_level)
        for row in completed
    )
    if any(row.evidence_level == EVIDENCE_PLANNING_ASSUMPTION for row in completed):
        hardware_complete = False
    ledger_status = (
        MASS_LEDGER_COMPLETE if hardware_complete else MASS_LEDGER_INCOMPLETE
    )
    comparison = planning_scenario_comparison(total_lower, total_upper)
    return MassBudgetResult(
        component_mass_interval_status=interval_status,
        mass_ledger_status=ledger_status,
        total_mass_lower_kg=total_lower,
        total_mass_upper_kg=total_upper,
        missing_component_ids=tuple(missing),
        components=tuple(completed),
        planning_scenario_comparison=comparison,
        whole_vehicle_energy_mass_closure_claimed=False,
    )


def planning_scenario_comparison(
    total_lower_kg: float | None,
    total_upper_kg: float | None,
) -> dict[str, object]:
    """Compare a complete interval to G1.5 planning labels. Never as parts."""
    interval_available = (
        total_lower_kg is not None and total_upper_kg is not None
    )
    scenarios = []
    for name, mass_kg in G1_5_PLANNING_SCENARIOS:
        inside: bool | None
        if interval_available:
            inside = float(total_lower_kg) <= mass_kg <= float(total_upper_kg)
        else:
            inside = None
        scenarios.append(
            {
                'name': name,
                'non_battery_mass_kg': mass_kg,
                'role': 'G1_5_PLANNING_LABEL_NOT_PART_EVIDENCE',
                'inside_computed_interval': inside,
            }
        )
    return {
        'used_as_part_evidence': False,
        'interval_available': interval_available,
        'comparison_status': (
            PLANNING_COMPARISON_INTERVAL_ONLY
            if interval_available
            else PLANNING_COMPARISON_NOT_APPLICABLE
        ),
        'notes': (
            'G1.5 7.16 / 12 / 16 kg values are planning boundaries only. '
            'They are not component masses and are not written into the ledger.'
        ),
        'scenarios': scenarios,
    }


def _require_g2_component_set(components: Sequence[MassComponent]) -> None:
    ids = tuple(item.component_id for item in components)
    missing = [item_id for item_id in REQUIRED_MASS_LEDGER_ITEMS if item_id not in ids]
    extra = sorted(set(ids) - set(REQUIRED_MASS_LEDGER_ITEMS))
    if missing:
        raise InvalidInputError(
            f'mass_components missing required G2 items: {missing}'
        )
    if extra:
        raise InvalidInputError(f'mass_components unknown items: {extra}')
    if len(ids) != len(set(ids)):
        raise InvalidInputError('duplicate mass_components component_id')
