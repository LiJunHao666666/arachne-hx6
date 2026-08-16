"""Bidirectional requirement-evidence-test-report traceability.

Broken references fail immediately. Requirement-evidence and
requirement-test links must agree in both directions; any mismatch
raises InvalidInputError. Orphan evidence and tests are reported and
cannot open EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS. Blocking requirements
without sufficient evidence become blockers. Coverage ratio is
diagnostic only and never a pass criterion.

SPECIFIED means the requirement clause is written. It is not verification
and not satisfaction. PLANNING_ASSUMPTION is not sufficient evidence and
does not count toward verified or satisfied.

Evidence is sufficient only when every required evidence item is
VENDOR_DECLARED, MEASURED, or TEST_VALIDATED. MISSING, PLANNING_ASSUMPTION,
empty evidence IDs, and mixed insufficient sets all fail closed.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from arachne_hx6_analysis.evidence_ledger import evidence_counts_by_level
from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.requirements_types import (
    BLOCK_REASON_INCOMPLETE_SPECIFICATION,
    BLOCK_REASON_MISSING_EVIDENCE,
    BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE,
    BLOCK_REASON_NO_REQUIRED_EVIDENCE,
    BLOCK_REASON_NOT_SATISFIED,
    BLOCK_REASON_PLANNING_ASSUMPTION_ONLY,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_ASSUMPTION,
    EVIDENCE_TEST_VALIDATED,
    HARDWARE_SUFFICIENT_LEVELS,
    OFFICIAL_REPORT_FIELDS,
    REQUIREMENT_INCOMPLETE,
    REQUIREMENT_SPECIFIED,
    TEST_NOT_PERFORMED,
    TRACE_CONSISTENT,
    TRACE_INCOMPLETE,
    EvidenceRecord,
    RequirementRecord,
    TestRecord,
    TraceabilityResult,
)


def evaluate_traceability(
    requirements: Sequence[RequirementRecord],
    evidence: Sequence[EvidenceRecord],
    tests: Sequence[TestRecord],
) -> TraceabilityResult:
    """Build the official graph and fail on broken references."""
    evidence_ids = {item.evidence_id: item for item in evidence}
    test_ids = {item.test_id: item for item in tests}
    requirement_ids = {item.requirement_id: item for item in requirements}
    broken: list[str] = []
    for req in requirements:
        for evidence_id in req.required_evidence_ids:
            if evidence_id not in evidence_ids:
                broken.append(f'requirement:{req.requirement_id}->{evidence_id}')
        for test_id in req.linked_test_ids:
            if test_id not in test_ids:
                broken.append(f'requirement:{req.requirement_id}->{test_id}')
        for field_name in req.linked_report_fields:
            if field_name not in OFFICIAL_REPORT_FIELDS:
                broken.append(
                    f'requirement:{req.requirement_id}->report:{field_name}'
                )
    for item in evidence:
        for req_id in item.linked_requirement_ids:
            if req_id not in requirement_ids:
                broken.append(f'evidence:{item.evidence_id}->{req_id}')
    for test in tests:
        for req_id in test.linked_requirement_ids:
            if req_id not in requirement_ids:
                broken.append(f'test:{test.test_id}->{req_id}')
    if broken:
        raise InvalidInputError(
            'broken traceability references: ' + ', '.join(broken)
        )
    inconsistent = _inconsistent_bidirectional_links(
        requirements, evidence_ids, test_ids, requirement_ids
    )
    if inconsistent:
        raise InvalidInputError(
            'inconsistent bidirectional traceability: '
            + ', '.join(inconsistent)
        )
    linked_from_requirements = {
        evidence_id
        for req in requirements
        for evidence_id in req.required_evidence_ids
    }
    orphan_evidence = tuple(
        sorted(
            item.evidence_id
            for item in evidence
            if item.evidence_id not in linked_from_requirements
        )
    )
    linked_tests = {
        test_id
        for req in requirements
        for test_id in req.linked_test_ids
    }
    orphan_tests = tuple(
        sorted(
            test.test_id for test in tests if test.test_id not in linked_tests
        )
    )
    specified_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if req.status == REQUIREMENT_SPECIFIED
    )
    incomplete_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if req.status == REQUIREMENT_INCOMPLETE
    )
    if set(req.status for req in requirements) - {
        REQUIREMENT_SPECIFIED,
        REQUIREMENT_INCOMPLETE,
    }:
        raise InvalidInputError(
            'requirement status must be SPECIFIED or INCOMPLETE_REQUIREMENT'
        )
    if len(specified_ids) + len(incomplete_ids) != len(requirements):
        raise InvalidInputError(
            'requirements_specified + requirements_incomplete_specification '
            'must equal requirements_total'
        )
    classified = _classify_requirement_sets(requirements, evidence_ids)
    incomplete_blocking_ids = classified['incomplete_blocking']
    evidence_blocked_ids = classified['evidence_blocked']
    if set(incomplete_blocking_ids) - set(incomplete_ids):
        raise InvalidInputError(
            'incomplete_blocking_requirement_ids must be a subset of '
            'incomplete_specification_requirement_ids'
        )
    if set(evidence_blocked_ids) - set(specified_ids):
        raise InvalidInputError(
            'evidence_blocked_requirement_ids must be a subset of '
            'specified_requirement_ids'
        )
    all_blocking_ids = _sorted_unique_ids(
        incomplete_blocking_ids + evidence_blocked_ids
    )
    if set(all_blocking_ids) != (
        set(incomplete_blocking_ids) | set(evidence_blocked_ids)
    ):
        raise InvalidInputError(
            'all_blocking_requirement_ids must equal the union of '
            'incomplete_blocking_requirement_ids and '
            'evidence_blocked_requirement_ids'
        )
    for req_id in all_blocking_ids:
        req = requirement_ids[req_id]
        if not req.blocking:
            raise InvalidInputError(
                f'blocker {req_id!r} is not a blocking requirement'
            )
    verified_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if _requirement_is_verified(req, evidence_ids)
    )
    satisfied_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if _requirement_is_satisfied(req, evidence_ids, test_ids)
    )
    _reject_planning_as_verified_or_satisfied(
        verified_ids, satisfied_ids, requirement_ids, evidence_ids
    )
    if set(verified_ids) & (
        set(classified['missing_evidence'])
        | set(classified['planning_assumption_only'])
        | set(classified['mixed_insufficient'])
        | set(evidence_blocked_ids)
        | set(incomplete_ids)
    ):
        raise InvalidInputError(
            'verified requirements cannot also be incomplete or '
            'evidence-blocked'
        )
    unsatisfied_blocking_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if req.blocking
        and req.requirement_id in verified_ids
        and req.requirement_id not in satisfied_ids
    )
    nonblocking_unverified_ids = _sorted_unique_ids(
        req.requirement_id
        for req in requirements
        if not req.blocking and req.requirement_id not in verified_ids
    )
    blocking_reasons = _blocking_requirement_reasons(
        requirements,
        classified,
        verified_ids,
        satisfied_ids,
    )
    for req in requirements:
        if not req.blocking:
            continue
        if req.requirement_id in satisfied_ids:
            continue
        if req.requirement_id not in {item[0] for item in blocking_reasons}:
            raise InvalidInputError(
                f'blocking requirement {req.requirement_id!r} has no '
                'blocker reason'
            )
    reason_codes = _sorted_unique_ids(code for _req_id, code in blocking_reasons)
    blockers = all_blocking_ids
    status = TRACE_CONSISTENT
    if orphan_evidence or orphan_tests or blockers or incomplete_ids:
        status = TRACE_INCOMPLETE
    coverage = (
        float(len(specified_ids)) / float(len(requirements))
        if requirements
        else None
    )
    return TraceabilityResult(
        requirements_total=len(requirements),
        requirements_specified=len(specified_ids),
        requirements_incomplete_specification=len(incomplete_ids),
        requirements_verified=len(verified_ids),
        requirements_satisfied=len(satisfied_ids),
        specified_requirement_ids=specified_ids,
        incomplete_specification_requirement_ids=incomplete_ids,
        verified_requirement_ids=verified_ids,
        satisfied_requirement_ids=satisfied_ids,
        missing_evidence_requirement_ids=classified['missing_evidence'],
        planning_assumption_only_requirement_ids=classified[
            'planning_assumption_only'
        ],
        mixed_insufficient_evidence_requirement_ids=classified[
            'mixed_insufficient'
        ],
        sufficient_evidence_requirement_ids=classified['sufficient'],
        evidence_blocked_requirement_ids=evidence_blocked_ids,
        incomplete_blocking_requirement_ids=incomplete_blocking_ids,
        all_blocking_requirement_ids=all_blocking_ids,
        nonblocking_unverified_requirement_ids=nonblocking_unverified_ids,
        unsatisfied_blocking_requirement_ids=unsatisfied_blocking_ids,
        blocking_reason_codes=reason_codes,
        blocking_requirement_reasons=blocking_reasons,
        evidence_total_by_level=evidence_counts_by_level(evidence),
        orphan_evidence_ids=orphan_evidence,
        orphan_test_ids=orphan_tests,
        broken_reference_ids=(),
        traceability_status=status,
        blocker_ids=blockers,
        coverage_ratio=coverage,
    )


def _sorted_unique_ids(ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(ids)))


def _inconsistent_bidirectional_links(
    requirements: Sequence[RequirementRecord],
    evidence_ids: Mapping[str, EvidenceRecord],
    test_ids: Mapping[str, TestRecord],
    requirement_ids: Mapping[str, RequirementRecord],
) -> list[str]:
    """Return every requirement-evidence and requirement-test mismatch."""
    inconsistent: list[str] = []
    for req in requirements:
        for evidence_id in req.required_evidence_ids:
            item = evidence_ids[evidence_id]
            if req.requirement_id not in item.linked_requirement_ids:
                inconsistent.append(
                    f'requirement:{req.requirement_id}->evidence:{evidence_id} '
                    'missing reverse evidence.linked_requirement_ids'
                )
        for test_id in req.linked_test_ids:
            test = test_ids[test_id]
            if req.requirement_id not in test.linked_requirement_ids:
                inconsistent.append(
                    f'requirement:{req.requirement_id}->test:{test_id} '
                    'missing reverse test.linked_requirement_ids'
                )
    for item in evidence_ids.values():
        for req_id in item.linked_requirement_ids:
            req = requirement_ids[req_id]
            if item.evidence_id not in req.required_evidence_ids:
                inconsistent.append(
                    f'evidence:{item.evidence_id}->requirement:{req_id} '
                    'missing reverse requirement.required_evidence_ids'
                )
    for test in test_ids.values():
        for req_id in test.linked_requirement_ids:
            req = requirement_ids[req_id]
            if test.test_id not in req.linked_test_ids:
                inconsistent.append(
                    f'test:{test.test_id}->requirement:{req_id} '
                    'missing reverse requirement.linked_test_ids'
                )
    return inconsistent


def _classify_requirement_sets(
    requirements: Sequence[RequirementRecord],
    evidence: Mapping[str, EvidenceRecord],
) -> dict[str, tuple[str, ...]]:
    """Partition specified requirements by fail-closed evidence class.

    PLANNING_ASSUMPTION is never sufficient. Mixed PLANNING_ASSUMPTION and
    MISSING is never sufficient. Empty evidence IDs are never sufficient.
    """
    incomplete_blocking: list[str] = []
    missing_evidence: list[str] = []
    planning_only: list[str] = []
    mixed_insufficient: list[str] = []
    sufficient: list[str] = []
    no_required: list[str] = []
    evidence_blocked: list[str] = []
    for req in requirements:
        if req.status == REQUIREMENT_INCOMPLETE:
            if req.blocking:
                incomplete_blocking.append(req.requirement_id)
            continue
        if req.status != REQUIREMENT_SPECIFIED:
            continue
        reason = _specified_evidence_reason(req, evidence)
        if reason == BLOCK_REASON_NO_REQUIRED_EVIDENCE:
            no_required.append(req.requirement_id)
        elif reason == BLOCK_REASON_MISSING_EVIDENCE:
            missing_evidence.append(req.requirement_id)
        elif reason == BLOCK_REASON_PLANNING_ASSUMPTION_ONLY:
            planning_only.append(req.requirement_id)
        elif reason == BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE:
            mixed_insufficient.append(req.requirement_id)
        elif reason is None:
            sufficient.append(req.requirement_id)
        if req.blocking and reason is not None:
            evidence_blocked.append(req.requirement_id)
    return {
        'incomplete_blocking': _sorted_unique_ids(incomplete_blocking),
        'missing_evidence': _sorted_unique_ids(missing_evidence),
        'planning_assumption_only': _sorted_unique_ids(planning_only),
        'mixed_insufficient': _sorted_unique_ids(mixed_insufficient),
        'sufficient': _sorted_unique_ids(sufficient),
        'no_required_evidence': _sorted_unique_ids(no_required),
        'evidence_blocked': _sorted_unique_ids(evidence_blocked),
    }


def _specified_evidence_reason(
    req: RequirementRecord,
    evidence: Mapping[str, EvidenceRecord],
) -> str | None:
    """Return the insufficient-evidence reason, or None if sufficient."""
    if not req.required_evidence_ids:
        return BLOCK_REASON_NO_REQUIRED_EVIDENCE
    levels = [
        evidence[evidence_id].evidence_level
        for evidence_id in req.required_evidence_ids
    ]
    if _levels_are_sufficient(levels):
        return None
    if all(level == EVIDENCE_MISSING for level in levels):
        return BLOCK_REASON_MISSING_EVIDENCE
    if all(level == EVIDENCE_PLANNING_ASSUMPTION for level in levels):
        return BLOCK_REASON_PLANNING_ASSUMPTION_ONLY
    return BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE


def _levels_are_sufficient(levels: Sequence[str]) -> bool:
    return bool(levels) and all(
        level in HARDWARE_SUFFICIENT_LEVELS for level in levels
    )


def _blocking_requirement_reasons(
    requirements: Sequence[RequirementRecord],
    classified: Mapping[str, tuple[str, ...]],
    verified_ids: Sequence[str],
    satisfied_ids: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    """Every blocking unverified or unsatisfied requirement gets a reason."""
    incomplete_blocking = set(classified['incomplete_blocking'])
    evidence_blocked = set(classified['evidence_blocked'])
    missing_evidence = set(classified['missing_evidence'])
    planning_only = set(classified['planning_assumption_only'])
    mixed_insufficient = set(classified['mixed_insufficient'])
    no_required = set(classified['no_required_evidence'])
    verified = set(verified_ids)
    satisfied = set(satisfied_ids)
    rows: list[tuple[str, str]] = []
    for req in requirements:
        if not req.blocking:
            continue
        req_id = req.requirement_id
        if req_id in satisfied:
            continue
        if req_id in incomplete_blocking:
            rows.append((req_id, BLOCK_REASON_INCOMPLETE_SPECIFICATION))
            continue
        if req_id in evidence_blocked:
            if req_id in no_required:
                rows.append((req_id, BLOCK_REASON_NO_REQUIRED_EVIDENCE))
            elif req_id in missing_evidence:
                rows.append((req_id, BLOCK_REASON_MISSING_EVIDENCE))
            elif req_id in planning_only:
                rows.append((req_id, BLOCK_REASON_PLANNING_ASSUMPTION_ONLY))
            elif req_id in mixed_insufficient:
                rows.append((req_id, BLOCK_REASON_MIXED_INSUFFICIENT_EVIDENCE))
            else:
                rows.append((req_id, BLOCK_REASON_MISSING_EVIDENCE))
            continue
        if req_id in verified:
            rows.append((req_id, BLOCK_REASON_NOT_SATISFIED))
    return tuple(sorted(rows, key=lambda item: item[0]))


def _requirement_is_verified(
    req: RequirementRecord,
    evidence: Mapping[str, EvidenceRecord],
) -> bool:
    """True only when the clause is specified and hardware evidence exists.

    SPECIFIED and PLANNING_ASSUMPTION never count as verified.
    """
    if req.status != REQUIREMENT_SPECIFIED:
        return False
    if not req.required_evidence_ids:
        return False
    levels = [
        evidence[evidence_id].evidence_level
        for evidence_id in req.required_evidence_ids
    ]
    if any(
        level in (EVIDENCE_MISSING, EVIDENCE_PLANNING_ASSUMPTION)
        for level in levels
    ):
        return False
    return all(level in HARDWARE_SUFFICIENT_LEVELS for level in levels)


def _requirement_is_satisfied(
    req: RequirementRecord,
    evidence: Mapping[str, EvidenceRecord],
    tests: Mapping[str, TestRecord],
) -> bool:
    """True only after verified hardware evidence and performed tests.

    G3 does not treat SPECIFIED, PLANNING_ASSUMPTION, or MEASURED-only
    evidence as satisfaction. Satisfaction stays closed in this gate.
    """
    if not _requirement_is_verified(req, evidence):
        return False
    if req.linked_test_ids:
        if any(
            tests[test_id].status == TEST_NOT_PERFORMED
            for test_id in req.linked_test_ids
        ):
            return False
    levels = [
        evidence[evidence_id].evidence_level
        for evidence_id in req.required_evidence_ids
    ]
    if not all(level == EVIDENCE_TEST_VALIDATED for level in levels):
        return False
    if any(
        evidence[evidence_id].verdict is None
        or not str(evidence[evidence_id].verdict).strip()
        for evidence_id in req.required_evidence_ids
    ):
        return False
    return False


def _reject_planning_as_verified_or_satisfied(
    verified_ids: Sequence[str],
    satisfied_ids: Sequence[str],
    requirements: Mapping[str, RequirementRecord],
    evidence: Mapping[str, EvidenceRecord],
) -> None:
    for req_id in list(verified_ids) + list(satisfied_ids):
        req = requirements[req_id]
        for evidence_id in req.required_evidence_ids:
            level = evidence[evidence_id].evidence_level
            if level in (EVIDENCE_MISSING, EVIDENCE_PLANNING_ASSUMPTION):
                raise InvalidInputError(
                    'PLANNING_ASSUMPTION and MISSING cannot increase '
                    'requirements_verified or requirements_satisfied'
                )
