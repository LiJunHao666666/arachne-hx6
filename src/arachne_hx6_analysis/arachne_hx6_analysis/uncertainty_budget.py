"""Geometry uncertainty budget and arm-radius mass-coupling contracts.

No empirical kg/m constants. Combination method is never auto-selected.
Nominal CLEARANCE_MET is never promoted to a robust pass.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import math
from typing import Sequence

from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.requirements_types import (
    ARM_COUPLING_INTERVAL_COMPUTED,
    ARM_COUPLING_UNDETERMINED,
    COMBINATION_LINEAR_SUM,
    COMBINATION_RSS,
    GEOMETRY_BUDGET_COMPLETE,
    GEOMETRY_BUDGET_INCOMPLETE,
    REQUIRED_UNCERTAINTY_SOURCES,
    ROBUST_GEOMETRY_UNDETERMINED,
    ArmCouplingContract,
    ArmCouplingResult,
    UncertaintyBudgetResult,
    UncertaintySource,
)


ARM_REQUIRED_FIELDS = (
    'baseline_radius_m',
    'candidate_radius_m',
    'extension_length_per_arm_m',
    'arm_count',
    'linear_mass_lower_kg_per_m',
    'linear_mass_upper_kg_per_m',
    'connector_mass_lower_kg',
    'connector_mass_upper_kg',
    'wiring_mass_lower_kg_per_m',
    'wiring_mass_upper_kg_per_m',
    'reinforcement_mass_lower_kg',
    'reinforcement_mass_upper_kg',
)


def evaluate_uncertainty_budget(
    sources: Sequence[UncertaintySource],
    combination_method: str | None,
    nominal_clearance_margin_m: float | None,
) -> UncertaintyBudgetResult:
    """Combine allowances only when every source and the method exist."""
    by_id = {item.source_id: item for item in sources}
    missing = [
        source_id
        for source_id in REQUIRED_UNCERTAINTY_SOURCES
        if source_id not in by_id or not _source_is_complete(by_id[source_id])
    ]
    extra = sorted(set(by_id) - set(REQUIRED_UNCERTAINTY_SOURCES))
    if extra:
        raise InvalidInputError(
            f'geometry uncertainty unknown sources: {extra}'
        )
    if missing or combination_method is None:
        return UncertaintyBudgetResult(
            geometry_uncertainty_budget_status=GEOMETRY_BUDGET_INCOMPLETE,
            combination_method=combination_method,
            total_geometry_uncertainty_allowance_m=None,
            robust_clearance_margin_m=None,
            robust_geometry_status=ROBUST_GEOMETRY_UNDETERMINED,
            sources=tuple(
                by_id[source_id]
                for source_id in REQUIRED_UNCERTAINTY_SOURCES
                if source_id in by_id
            ),
            missing_source_ids=tuple(missing),
        )
    allowances = [
        _source_allowance_m(by_id[source_id])
        for source_id in REQUIRED_UNCERTAINTY_SOURCES
    ]
    total = combine_allowances(allowances, combination_method)
    robust_margin = None
    if nominal_clearance_margin_m is not None:
        robust_margin = nominal_clearance_margin_m - total
    return UncertaintyBudgetResult(
        geometry_uncertainty_budget_status=GEOMETRY_BUDGET_COMPLETE,
        combination_method=combination_method,
        total_geometry_uncertainty_allowance_m=total,
        robust_clearance_margin_m=robust_margin,
        robust_geometry_status=ROBUST_GEOMETRY_UNDETERMINED,
        sources=tuple(
            by_id[source_id] for source_id in REQUIRED_UNCERTAINTY_SOURCES
        ),
        missing_source_ids=(),
    )


def combine_allowances(
    allowances_m: Sequence[float],
    method: str,
) -> float:
    """Closed-form combination. Method must be explicit."""
    if method == COMBINATION_LINEAR_SUM:
        return float(sum(allowances_m))
    if method == COMBINATION_RSS:
        return math.sqrt(sum(value * value for value in allowances_m))
    raise InvalidInputError(
        f'combination_method must be {COMBINATION_LINEAR_SUM} or '
        f'{COMBINATION_RSS}, got {method!r}'
    )


def evaluate_arm_coupling(contract: ArmCouplingContract) -> ArmCouplingResult:
    """Compute arm-extension mass only when every required field is present."""
    missing = [
        name for name in ARM_REQUIRED_FIELDS
        if getattr(contract, name) is None
    ]
    if missing or not contract.evidence_ids:
        return ArmCouplingResult(
            arm_radius_mass_coupling_status=ARM_COUPLING_UNDETERMINED,
            arm_extension_mass_lower_kg=None,
            arm_extension_mass_upper_kg=None,
            extension_length_per_arm_m=contract.extension_length_per_arm_m,
            missing_field_names=tuple(missing),
        )
    extension = _resolved_extension_m(contract)
    lower = _arm_mass_bound(
        contract.arm_count,
        extension,
        contract.linear_mass_lower_kg_per_m,
        contract.connector_mass_lower_kg,
        contract.wiring_mass_lower_kg_per_m,
        contract.reinforcement_mass_lower_kg,
    )
    upper = _arm_mass_bound(
        contract.arm_count,
        extension,
        contract.linear_mass_upper_kg_per_m,
        contract.connector_mass_upper_kg,
        contract.wiring_mass_upper_kg_per_m,
        contract.reinforcement_mass_upper_kg,
    )
    if lower > upper:
        raise InvalidInputError(
            'arm extension mass lower > upper after interval propagation'
        )
    return ArmCouplingResult(
        arm_radius_mass_coupling_status=ARM_COUPLING_INTERVAL_COMPUTED,
        arm_extension_mass_lower_kg=lower,
        arm_extension_mass_upper_kg=upper,
        extension_length_per_arm_m=extension,
        missing_field_names=(),
    )


def _source_is_complete(source: UncertaintySource) -> bool:
    if source.allowance_m is not None:
        return True
    return source.lower_m is not None and source.upper_m is not None


def _source_allowance_m(source: UncertaintySource) -> float:
    if source.allowance_m is not None:
        return source.allowance_m
    return max(abs(source.lower_m), abs(source.upper_m))


def _resolved_extension_m(contract: ArmCouplingContract) -> float:
    computed = (
        float(contract.candidate_radius_m) - float(contract.baseline_radius_m)
    )
    provided = float(contract.extension_length_per_arm_m)
    if computed < 0.0:
        raise InvalidInputError(
            'arm_radius_mass_coupling.candidate_radius_m must be >= '
            'baseline_radius_m'
        )
    if abs(computed - provided) > 1.0e-12:
        raise InvalidInputError(
            'arm_radius_mass_coupling.extension_length_per_arm_m must equal '
            'candidate_radius_m - baseline_radius_m'
        )
    return provided


def _arm_mass_bound(
    arm_count: int,
    extension_m: float,
    linear_kg_per_m: float,
    connector_kg: float,
    wiring_kg_per_m: float,
    reinforcement_kg: float,
) -> float:
    per_arm = (
        extension_m * linear_kg_per_m
        + connector_kg
        + extension_m * wiring_kg_per_m
        + reinforcement_kg
    )
    return float(arm_count) * per_arm
