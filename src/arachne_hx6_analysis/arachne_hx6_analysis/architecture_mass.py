"""Parts-level mass-ledger parsing and completeness status.

Evidence statuses stay fail-closed: MISSING or planning placeholders keep
the ledger INCOMPLETE. This is not whole-vehicle mass closure.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from arachne_hx6_analysis.architecture_types import (
    ALLOWED_EVIDENCE_STATUS,
    EVIDENCE_MEASURED,
    EVIDENCE_MISSING,
    EVIDENCE_PLANNING_PLACEHOLDER,
    EVIDENCE_VENDOR_DECLARED,
    MASS_LEDGER_COMPLETE,
    MASS_LEDGER_INCOMPLETE,
    REQUIRED_MASS_LEDGER_ITEMS,
    MassLedgerItem,
)
from arachne_hx6_analysis.inputs import (
    as_list,
    as_mapping,
    as_optional_float,
    as_str,
    optional_str,
    require_key,
)
from arachne_hx6_analysis.model import InvalidInputError

def _parse_mass_ledger(raw: Mapping[str, Any]) -> tuple[MassLedgerItem, ...]:
    items_raw = as_list(
        require_key(raw, 'items', 'mass_ledger'), 'mass_ledger.items'
    )
    parsed: dict[str, MassLedgerItem] = {}
    for index, item in enumerate(items_raw):
        path = f'mass_ledger.items[{index}]'
        mapping = as_mapping(item, path)
        item_id = as_str(require_key(mapping, 'id', path), f'{path}.id').strip()
        if not item_id:
            raise InvalidInputError(f'{path}.id must be non-empty')
        if item_id in parsed:
            raise InvalidInputError(f'duplicate mass_ledger id: {item_id!r}')
        status = as_str(
            require_key(mapping, 'evidence_status', path),
            f'{path}.evidence_status',
        )
        if status not in ALLOWED_EVIDENCE_STATUS:
            raise InvalidInputError(
                f'{path}.evidence_status must be one of '
                f'{list(ALLOWED_EVIDENCE_STATUS)}, got {status!r}'
            )
        mass = as_optional_float(mapping.get('mass_kg', None), f'{path}.mass_kg')
        if status == EVIDENCE_MISSING:
            if mass is not None:
                raise InvalidInputError(
                    f'{path}.mass_kg must be null when evidence_status is MISSING'
                )
        elif status in (EVIDENCE_VENDOR_DECLARED, EVIDENCE_MEASURED):
            if mass is None or mass <= 0.0:
                raise InvalidInputError(
                    f'{path}.mass_kg must be > 0 for {status}'
                )
        elif mass is not None and mass <= 0.0:
            raise InvalidInputError(
                f'{path}.mass_kg must be null or > 0, got {mass}'
            )
        parsed[item_id] = MassLedgerItem(
            item_id=item_id,
            evidence_status=status,
            mass_kg=mass,
            source_kind=as_str(
                require_key(mapping, 'source_kind', path),
                f'{path}.source_kind',
            ),
            notes=optional_str(mapping.get('notes', ''), f'{path}.notes'),
        )
    missing = [item_id for item_id in REQUIRED_MASS_LEDGER_ITEMS if item_id not in parsed]
    extra = sorted(set(parsed) - set(REQUIRED_MASS_LEDGER_ITEMS))
    if missing:
        raise InvalidInputError(f'mass_ledger missing required items: {missing}')
    if extra:
        raise InvalidInputError(f'mass_ledger unknown items: {extra}')
    return tuple(parsed[item_id] for item_id in REQUIRED_MASS_LEDGER_ITEMS)



def _mass_ledger_status(items: Sequence[MassLedgerItem]) -> str:
    if any(item.evidence_status == EVIDENCE_MISSING for item in items):
        return MASS_LEDGER_INCOMPLETE
    if any(
        item.evidence_status == EVIDENCE_PLANNING_PLACEHOLDER for item in items
    ):
        return MASS_LEDGER_INCOMPLETE
    if all(
        item.evidence_status in (EVIDENCE_VENDOR_DECLARED, EVIDENCE_MEASURED)
        for item in items
    ):
        return MASS_LEDGER_COMPLETE
    return MASS_LEDGER_INCOMPLETE
