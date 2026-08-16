"""Evidence-level metadata rules and ledger status.

Evidence cannot auto-upgrade. PLANNING_ASSUMPTION is not hardware
evidence and cannot close procurement or structure-freeze gates.
Missing metadata for a declared level is rejected.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.requirements_types import (
    EVIDENCE_MEASURED,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    EVIDENCE_TEST_VALIDATED,
    EVIDENCE_VENDOR_DECLARED,
    HARDWARE_GATE_LEVELS,
    HARDWARE_SUFFICIENT_LEVELS,
    KIND_QUANTITATIVE,
    REQUIREMENTS_COMPLETE,
    REQUIREMENTS_INCOMPLETE,
    EvidenceRecord,
    RequirementRecord,
)
from arachne_hx6_analysis.requirements_validation import require_interval


def validate_evidence_level_metadata(item: EvidenceRecord, path: str) -> None:
    """Reject a declared level that lacks its required metadata."""
    require_interval(item.lower, item.upper, f'{path}.lower', f'{path}.upper')
    if item.evidence_level == EVIDENCE_MISSING:
        for name in ('value', 'lower', 'upper'):
            if getattr(item, name) is not None:
                raise InvalidInputError(
                    f'{path}.{name} must be null when evidence_level is MISSING'
                )
        return
    if item.evidence_level == EVIDENCE_PLANNING_ASSUMPTION:
        return
    if item.evidence_level == EVIDENCE_VENDOR_DECLARED:
        _require_text(item.vendor, f'{path}.vendor', EVIDENCE_VENDOR_DECLARED)
        _require_text(item.model, f'{path}.model', EVIDENCE_VENDOR_DECLARED)
        _require_text(item.source, f'{path}.source', EVIDENCE_VENDOR_DECLARED)
        if not item.source_date and not item.access_date:
            raise InvalidInputError(
                f'{path} VENDOR_DECLARED requires source_date or access_date'
            )
        return
    if item.evidence_level == EVIDENCE_MEASURED:
        _require_text(
            item.measurement_method,
            f'{path}.measurement_method',
            EVIDENCE_MEASURED,
        )
        _require_text(
            item.measurement_equipment,
            f'{path}.measurement_equipment',
            EVIDENCE_MEASURED,
        )
        _require_text(item.unit, f'{path}.unit', EVIDENCE_MEASURED)
        if item.sample_count is None or item.sample_count < 1:
            raise InvalidInputError(
                f'{path}.sample_count must be >= 1 for MEASURED'
            )
        _require_text(
            item.measurement_time or item.source_date,
            f'{path}.measurement_time',
            EVIDENCE_MEASURED,
        )
        return
    if item.evidence_level == EVIDENCE_TEST_VALIDATED:
        _require_text(item.test_id, f'{path}.test_id', EVIDENCE_TEST_VALIDATED)
        _require_text(
            item.test_conditions,
            f'{path}.test_conditions',
            EVIDENCE_TEST_VALIDATED,
        )
        _require_text(
            item.raw_result, f'{path}.raw_result', EVIDENCE_TEST_VALIDATED
        )
        _require_text(item.verdict, f'{path}.verdict', EVIDENCE_TEST_VALIDATED)
        return
    raise InvalidInputError(
        f'{path}.evidence_level is not allowed: {item.evidence_level!r}'
    )


def evidence_by_id(
    items: Sequence[EvidenceRecord],
) -> dict[str, EvidenceRecord]:
    """Index evidence records. Duplicate IDs are a loader error."""
    return {item.evidence_id: item for item in items}


def evidence_counts_by_level(
    items: Sequence[EvidenceRecord],
) -> dict[str, int]:
    """Stable counts for every official evidence level, including zeros."""
    counts = {
        EVIDENCE_MISSING: 0,
        EVIDENCE_PLANNING_ASSUMPTION: 0,
        EVIDENCE_VENDOR_DECLARED: 0,
        EVIDENCE_MEASURED: 0,
        EVIDENCE_TEST_VALIDATED: 0,
    }
    for item in items:
        counts[item.evidence_level] = counts.get(item.evidence_level, 0) + 1
    return counts


def hardware_evidence_is_sufficient(level: str) -> bool:
    """VENDOR_DECLARED or better may fill an interval; not a flyable claim."""
    return level in HARDWARE_SUFFICIENT_LEVELS


def hardware_gate_is_satisfied(level: str) -> bool:
    """Only measured or test-validated evidence can close a hardware gate."""
    return level in HARDWARE_GATE_LEVELS


def planning_assumption_cannot_close_hardware_gate(level: str) -> bool:
    """PLANNING_ASSUMPTION is recorded, not hardware evidence."""
    return level == EVIDENCE_PLANNING_ASSUMPTION


def evidence_ledger_status(
    requirements: Sequence[RequirementRecord],
    evidence: Mapping[str, EvidenceRecord],
) -> str:
    """INCOMPLETE unless every blocking requirement has sufficient evidence.

    Qualitative blocking requirements are included. PLANNING_ASSUMPTION
    is never sufficient.
    """
    for req in requirements:
        if not req.blocking:
            continue
        if not req.required_evidence_ids:
            return REQUIREMENTS_INCOMPLETE
        for evidence_id in req.required_evidence_ids:
            item = evidence.get(evidence_id)
            if item is None:
                return REQUIREMENTS_INCOMPLETE
            if item.evidence_level not in HARDWARE_SUFFICIENT_LEVELS:
                return REQUIREMENTS_INCOMPLETE
    hardware_items = [
        item for item in evidence.values()
        if item.component_id not in ('analysis_process', 'safety')
    ]
    if any(item.evidence_level == EVIDENCE_MISSING for item in hardware_items):
        return REQUIREMENTS_INCOMPLETE
    return REQUIREMENTS_COMPLETE


def evidence_has_quantitative_content(item: EvidenceRecord) -> bool:
    """True when a finite value or a complete finite interval and unit exist."""
    if item.unit is None or not str(item.unit).strip():
        return False
    if item.value is not None:
        return True
    if (
        item.lower is not None
        and item.upper is not None
        and item.lower <= item.upper
    ):
        return True
    return False


def reject_claimed_high_level_without_quantitative_content(
    requirements: Sequence[RequirementRecord],
    evidence: Sequence[EvidenceRecord],
) -> None:
    """Fail closed when a quantitative requirement cites metadata-only evidence.

    VENDOR_DECLARED, MEASURED, and TEST_VALIDATED may not upgrade a
    quantitative requirement using only vendor, model, date, or test-name
    metadata. MISSING and PLANNING_ASSUMPTION stay ordinary blockers.
    Qualitative requirements do not require numeric content.
    """
    evidence_map = {item.evidence_id: item for item in evidence}
    bad: list[str] = []
    for req in requirements:
        if req.kind != KIND_QUANTITATIVE:
            continue
        for evidence_id in req.required_evidence_ids:
            item = evidence_map.get(evidence_id)
            if item is None:
                continue
            if item.evidence_level not in HARDWARE_SUFFICIENT_LEVELS:
                continue
            if not evidence_has_quantitative_content(item):
                bad.append(
                    f'requirement:{req.requirement_id}->evidence:{evidence_id}'
                    f'({item.evidence_level})'
                )
    if bad:
        raise InvalidInputError(
            'quantitative requirement evidence claims VENDOR_DECLARED, '
            'MEASURED, or TEST_VALIDATED without a finite value or a '
            'complete finite interval and non-empty unit: ' + ', '.join(bad)
        )


def _require_text(value: str | None, path: str, level: str) -> None:
    if value is None or not str(value).strip():
        raise InvalidInputError(f'{path} is required for {level}')
