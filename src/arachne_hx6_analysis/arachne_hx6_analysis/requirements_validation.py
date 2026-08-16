"""Strict YAML field validation for G3 requirement contracts.

Unknown keys are rejected. Bools cannot stand in for numbers. NaN and
Infinity are rejected. YAML syntax and type errors become InvalidInputError
with a field path.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from arachne_hx6_analysis.inputs import (
    as_bool,
    as_float,
    as_int,
    as_list,
    as_mapping,
    as_optional_float,
    as_str,
    require_key,
)
from arachne_hx6_analysis.model import InvalidInputError


def load_yaml_mapping(path: str | Path, root_name: str) -> dict[str, Any]:
    """Load a YAML file and require a top-level mapping."""
    config_path = Path(path)
    if not config_path.is_file():
        raise InvalidInputError(f'config file not found: {config_path}')
    try:
        raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {config_path}: {exc}') from exc
    try:
        return as_mapping(raw, root_name)
    except InvalidInputError:
        raise
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f'invalid {root_name}: {exc}') from exc


def reject_unknown_keys(
    mapping: Mapping[str, Any],
    allowed: Iterable[str],
    path: str,
) -> None:
    """Reject keys that are not in the explicit allow-list."""
    allowed_set = set(allowed)
    unknown = sorted(set(mapping) - allowed_set)
    if unknown:
        raise InvalidInputError(f'{path} has unknown fields: {unknown}')


def as_optional_str(value: Any, path: str) -> str | None:
    """Allow YAML null; otherwise a non-empty-stripped string may be empty."""
    if value is None:
        return None
    return as_str(value, path)


def as_optional_nonempty_str(value: Any, path: str) -> str | None:
    """Allow YAML null; otherwise a non-empty string."""
    if value is None:
        return None
    text = as_str(value, path).strip()
    if not text:
        raise InvalidInputError(f'{path} must be null or a non-empty string')
    return text


def as_optional_int(value: Any, path: str) -> int | None:
    """Allow YAML null; otherwise an integer. Bools are rejected."""
    if value is None:
        return None
    return as_int(value, path)


def as_optional_non_negative_int(value: Any, path: str) -> int | None:
    """Allow YAML null; otherwise an integer >= 0."""
    if value is None:
        return None
    number = as_int(value, path)
    if number < 0:
        raise InvalidInputError(f'{path} must be null or >= 0, got {number}')
    return number


def as_positive_int(value: Any, path: str) -> int:
    """Require an integer >= 1. Bools are rejected."""
    number = as_int(value, path)
    if number < 1:
        raise InvalidInputError(f'{path} must be an integer >= 1, got {number}')
    return number


def as_optional_non_negative_float(value: Any, path: str) -> float | None:
    """Allow YAML null; otherwise a finite number >= 0."""
    if value is None:
        return None
    number = as_float(value, path)
    if number < 0.0:
        raise InvalidInputError(f'{path} must be null or >= 0, got {number}')
    return number


def as_nonempty_id(value: Any, path: str) -> str:
    """Require a non-empty identifier after stripping whitespace."""
    text = as_str(value, path).strip()
    if not text:
        raise InvalidInputError(f'{path} must be a non-empty id')
    return text


def as_id_list(value: Any, path: str) -> tuple[str, ...]:
    """Require a list of non-empty unique strings."""
    items = as_list(value, path)
    parsed: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        text = as_str(item, f'{path}[{index}]').strip()
        if not text:
            raise InvalidInputError(f'{path}[{index}] must be a non-empty string')
        if text in seen:
            raise InvalidInputError(f'duplicate {path} value: {text!r}')
        seen.add(text)
        parsed.append(text)
    return tuple(parsed)


def require_unique_ids(ids: Iterable[str], kind: str) -> None:
    """Reject duplicate IDs of one kind."""
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            raise InvalidInputError(f'duplicate {kind} id: {item_id!r}')
        seen.add(item_id)


def require_interval(
    lower: float | None,
    upper: float | None,
    lower_path: str,
    upper_path: str,
) -> None:
    """If both bounds exist they must satisfy lower <= upper."""
    if lower is None or upper is None:
        return
    if lower > upper:
        raise InvalidInputError(
            f'{lower_path}={lower} must be <= {upper_path}={upper}'
        )


def require_unit_when_numeric(
    has_numeric: bool,
    unit: str | None,
    unit_path: str,
) -> None:
    """A numeric field must carry an explicit unit."""
    if has_numeric and (unit is None or not unit.strip()):
        raise InvalidInputError(
            f'{unit_path} is required when a numeric value is present'
        )


def as_allowed_str(value: Any, path: str, allowed: Iterable[str]) -> str:
    """Require a string from a closed set."""
    text = as_str(value, path)
    allowed_tuple = tuple(allowed)
    if text not in allowed_tuple:
        raise InvalidInputError(
            f'{path} must be one of {list(allowed_tuple)}, got {text!r}'
        )
    return text


def require_analysis_only_header(root: Mapping[str, Any], path: str) -> None:
    """Every official G3 YAML must stay ANALYSIS_ONLY and not for purchase."""
    status = as_str(require_key(root, 'status', path), f'{path}.status')
    if status != 'ANALYSIS_ONLY':
        raise InvalidInputError(
            f'{path}.status must be ANALYSIS_ONLY, got {status!r}'
        )
    allowed = as_bool(
        require_key(root, 'procurement_allowed', path),
        f'{path}.procurement_allowed',
    )
    if allowed:
        raise InvalidInputError(f'{path}.procurement_allowed must be false')
