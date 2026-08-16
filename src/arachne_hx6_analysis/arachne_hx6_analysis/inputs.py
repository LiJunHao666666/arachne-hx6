"""Strict YAML / planning-input converters shared by G1.5 and G2.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Any, Mapping
import math

from arachne_hx6_analysis.model import InvalidInputError


def require_key(mapping: Mapping[str, Any], key: str, path: str = '') -> Any:
    """Return mapping[key] or raise InvalidInputError with a dotted path."""
    try:
        return mapping[key]
    except KeyError as exc:
        prefix = f'{path}.' if path else ''
        raise InvalidInputError(f'{prefix}{key} is required') from exc


def as_mapping(value: Any, path: str) -> dict[str, Any]:
    """Require a dict and return it."""
    if not isinstance(value, dict):
        raise InvalidInputError(
            f'{path} must be a mapping, got {type(value).__name__}'
        )
    return value


def as_list(value: Any, path: str) -> list[Any]:
    """Require a list and return it."""
    if not isinstance(value, list):
        raise InvalidInputError(
            f'{path} must be a list, got {type(value).__name__}'
        )
    return value


def as_bool(value: Any, path: str) -> bool:
    """Require a real bool. Integers are not accepted."""
    if not isinstance(value, bool):
        raise InvalidInputError(f'{path} must be a boolean, got {value!r}')
    return value


def as_str(value: Any, path: str) -> str:
    """Require a string."""
    if not isinstance(value, str):
        raise InvalidInputError(f'{path} must be a string, got {value!r}')
    return value


def optional_str(value: Any, path: str) -> str:
    """None becomes empty string; otherwise require a string."""
    if value is None:
        return ''
    return as_str(value, path).strip()


def as_float(value: Any, path: str) -> float:
    """Require a finite real number. Bools are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(f'{path} must be a real number, got {value!r}')
    number = float(value)
    if not math.isfinite(number):
        raise InvalidInputError(f'{path} must be finite, got {value!r}')
    return number


def as_int(value: Any, path: str) -> int:
    """Require an integer. Integer-valued floats are accepted; 6.5 is not."""
    if isinstance(value, bool):
        raise InvalidInputError(f'{path} must be an integer, got {value!r}')
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or value != int(value):
            raise InvalidInputError(
                f'{path} must be an integer without truncation, got {value!r}'
            )
        return int(value)
    raise InvalidInputError(f'{path} must be an integer, got {value!r}')


def as_optional_float(value: Any, path: str) -> float | None:
    """Allow YAML null; otherwise a finite real number."""
    if value is None:
        return None
    return as_float(value, path)


def as_optional_non_negative_float(value: Any, path: str) -> float | None:
    """Allow YAML null; otherwise a finite number >= 0. No silent default."""
    if value is None:
        return None
    number = as_float(value, path)
    if number < 0.0:
        raise InvalidInputError(f'{path} must be null or >= 0, got {number}')
    return number
