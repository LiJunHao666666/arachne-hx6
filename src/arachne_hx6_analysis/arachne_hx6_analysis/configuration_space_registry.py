"""Closed G4-D1A include/exclude pair registry.

Include is exactly 162 directed pair IDs. Exclude is exactly 420 directed
pair IDs with stable reason codes. Reverse, duplicate, or unknown IDs are
rejected; they are never auto-swapped.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from typing import Mapping

from arachne_hx6_analysis.architecture_types import (
    LEG_JOINT_SUFFIXES,
    LEG_PREFIXES,
)
from arachne_hx6_analysis.configuration_space_types import (
    EXCL_CAMERA_NOT_AUTHORIZED,
    EXCL_INTER_LEG_DEFERRED_FROM_D1A,
    EXCL_LEG_HEX_ARM_DEFERRED_FROM_D1A,
    EXCL_LEG_HEX_HUB_DEFERRED_FROM_D1A,
    EXCL_POD_FOOT_NOT_A_CONTRACT_PAIR,
    EXCL_SENSOR_POD_DISK_NOT_IN_G4_D0_4_1_1,
    EXCL_URDF_ROTOR_CYLINDER_NOT_HARDWARE_PROP,
    FAMILY_CAMERA,
    FAMILY_INTER_LEG,
    FAMILY_LEG_HEX_ARM,
    FAMILY_LEG_HEX_HUB,
    FAMILY_LEG_SEGMENT_ANALYSIS_DISK,
    FAMILY_LEG_SEGMENT_BASE_LINK,
    FAMILY_LEG_URDF_ROTOR,
    FAMILY_POD_FOOT,
    FAMILY_SENSOR_POD_ANALYSIS_DISK,
    FAMILY_SENSOR_POD_LEG_SEGMENT,
    N_PAIR_INSTANCES_EXCLUDED,
    N_PAIR_INSTANCES_INCLUDED,
)
from arachne_hx6_analysis.model import InvalidInputError

LEG_SEGMENTS = tuple(
    f'{prefix}_{suffix}'
    for prefix in LEG_PREFIXES
    for suffix in LEG_JOINT_SUFFIXES
)
ANALYSIS_DISKS = tuple(f'analysis_disk_hex_{index}' for index in range(1, 7))
SENSOR_PODS = ('left_sensor_pod', 'right_sensor_pod')
BASE_LINK = 'base_link'
CAMERA_LINK = 'camera_link'
HEX_ARMS = tuple(f'hex_{index}_arm' for index in range(1, 7))
HEX_HUB = 'hex_hub'
URDF_ROTORS = tuple(f'hex_{index}_rotor' for index in range(1, 7))
FOOT_LINKS = tuple(f'{prefix}_foot' for prefix in LEG_PREFIXES)

INCLUDE_FAMILY_SPECS = (
    (FAMILY_LEG_SEGMENT_ANALYSIS_DISK, 108, None),
    (FAMILY_SENSOR_POD_LEG_SEGMENT, 36, None),
    (FAMILY_LEG_SEGMENT_BASE_LINK, 18, None),
)
EXCLUDE_FAMILY_SPECS = (
    (FAMILY_SENSOR_POD_ANALYSIS_DISK, 12, EXCL_SENSOR_POD_DISK_NOT_IN_G4_D0_4_1_1),
    (FAMILY_CAMERA, 27, EXCL_CAMERA_NOT_AUTHORIZED),
    (FAMILY_INTER_LEG, 135, EXCL_INTER_LEG_DEFERRED_FROM_D1A),
    (FAMILY_LEG_HEX_ARM, 108, EXCL_LEG_HEX_ARM_DEFERRED_FROM_D1A),
    (FAMILY_LEG_HEX_HUB, 18, EXCL_LEG_HEX_HUB_DEFERRED_FROM_D1A),
    (FAMILY_LEG_URDF_ROTOR, 108, EXCL_URDF_ROTOR_CYLINDER_NOT_HARDWARE_PROP),
    (FAMILY_POD_FOOT, 12, EXCL_POD_FOOT_NOT_A_CONTRACT_PAIR),
)


def pair_id(left: str, right: str) -> str:
    return f'{left}__{right}'


def parse_pair_id(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f'pair id must be a non-empty string, got {value!r}')
    if value.count('__') != 1:
        raise InvalidInputError(f'pair id must contain exactly one __, got {value!r}')
    left, right = value.split('__')
    if not left or not right:
        raise InvalidInputError(f'pair id components must be non-empty, got {value!r}')
    return left, right


def _leg_disk_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(segment, disk)
        for segment in LEG_SEGMENTS
        for disk in ANALYSIS_DISKS
    )


def _pod_leg_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(pod, segment)
        for pod in SENSOR_PODS
        for segment in LEG_SEGMENTS
    )


def _leg_base_pairs() -> tuple[str, ...]:
    return tuple(pair_id(segment, BASE_LINK) for segment in LEG_SEGMENTS)


def _pod_disk_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(pod, disk)
        for pod in SENSOR_PODS
        for disk in ANALYSIS_DISKS
    )


def _camera_pairs() -> tuple[str, ...]:
    targets = ANALYSIS_DISKS + LEG_SEGMENTS + SENSOR_PODS + (BASE_LINK,)
    return tuple(pair_id(CAMERA_LINK, target) for target in targets)


def _inter_leg_pairs() -> tuple[str, ...]:
    pairs: list[str] = []
    for left_index, left_prefix in enumerate(LEG_PREFIXES):
        for right_prefix in LEG_PREFIXES[left_index + 1:]:
            for left_suffix in LEG_JOINT_SUFFIXES:
                for right_suffix in LEG_JOINT_SUFFIXES:
                    pairs.append(
                        pair_id(
                            f'{left_prefix}_{left_suffix}',
                            f'{right_prefix}_{right_suffix}',
                        )
                    )
    return tuple(pairs)


def _leg_hex_arm_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(segment, arm)
        for segment in LEG_SEGMENTS
        for arm in HEX_ARMS
    )


def _leg_hex_hub_pairs() -> tuple[str, ...]:
    return tuple(pair_id(segment, HEX_HUB) for segment in LEG_SEGMENTS)


def _leg_urdf_rotor_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(segment, rotor)
        for segment in LEG_SEGMENTS
        for rotor in URDF_ROTORS
    )


def _pod_foot_pairs() -> tuple[str, ...]:
    return tuple(
        pair_id(pod, foot)
        for pod in SENSOR_PODS
        for foot in FOOT_LINKS
    )


_INCLUDE_BUILDERS = {
    FAMILY_LEG_SEGMENT_ANALYSIS_DISK: _leg_disk_pairs,
    FAMILY_SENSOR_POD_LEG_SEGMENT: _pod_leg_pairs,
    FAMILY_LEG_SEGMENT_BASE_LINK: _leg_base_pairs,
}
_EXCLUDE_BUILDERS = {
    FAMILY_SENSOR_POD_ANALYSIS_DISK: _pod_disk_pairs,
    FAMILY_CAMERA: _camera_pairs,
    FAMILY_INTER_LEG: _inter_leg_pairs,
    FAMILY_LEG_HEX_ARM: _leg_hex_arm_pairs,
    FAMILY_LEG_HEX_HUB: _leg_hex_hub_pairs,
    FAMILY_LEG_URDF_ROTOR: _leg_urdf_rotor_pairs,
    FAMILY_POD_FOOT: _pod_foot_pairs,
}


def included_pair_ids() -> tuple[str, ...]:
    ids: list[str] = []
    for family_id, expected_count, _reason in INCLUDE_FAMILY_SPECS:
        family_ids = _INCLUDE_BUILDERS[family_id]()
        if len(family_ids) != expected_count:
            raise InvalidInputError(
                f'{family_id} include count {len(family_ids)} != {expected_count}'
            )
        ids.extend(family_ids)
    if len(ids) != N_PAIR_INSTANCES_INCLUDED:
        raise InvalidInputError(
            f'include set size {len(ids)} != {N_PAIR_INSTANCES_INCLUDED}'
        )
    if len(set(ids)) != len(ids):
        raise InvalidInputError('include set contains duplicates')
    return tuple(ids)


def excluded_pair_ids() -> tuple[str, ...]:
    ids: list[str] = []
    for family_id, expected_count, _reason in EXCLUDE_FAMILY_SPECS:
        family_ids = _EXCLUDE_BUILDERS[family_id]()
        if len(family_ids) != expected_count:
            raise InvalidInputError(
                f'{family_id} exclude count {len(family_ids)} != {expected_count}'
            )
        ids.extend(family_ids)
    if len(ids) != N_PAIR_INSTANCES_EXCLUDED:
        raise InvalidInputError(
            f'exclude set size {len(ids)} != {N_PAIR_INSTANCES_EXCLUDED}'
        )
    if len(set(ids)) != len(ids):
        raise InvalidInputError('exclude set contains duplicates')
    return tuple(ids)


def exclusion_reasons() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for family_id, _count, reason in EXCLUDE_FAMILY_SPECS:
        if reason is None:
            raise InvalidInputError(f'{family_id} missing exclusion reason')
        for pair in _EXCLUDE_BUILDERS[family_id]():
            mapping[pair] = reason
    return mapping


INCLUDED_PAIR_IDS = included_pair_ids()
EXCLUDED_PAIR_IDS = excluded_pair_ids()
EXCLUSION_REASONS = exclusion_reasons()
INCLUDED_PAIR_SET = set(INCLUDED_PAIR_IDS)
EXCLUDED_PAIR_SET = set(EXCLUDED_PAIR_IDS)

if INCLUDED_PAIR_SET & EXCLUDED_PAIR_SET:
    raise InvalidInputError('include and exclude pair sets overlap')


def pair_kind(pair: str) -> str:
    left, right = parse_pair_id(pair)
    if left in LEG_SEGMENTS and right in ANALYSIS_DISKS:
        return FAMILY_LEG_SEGMENT_ANALYSIS_DISK
    if left in SENSOR_PODS and right in LEG_SEGMENTS:
        return FAMILY_SENSOR_POD_LEG_SEGMENT
    if left in LEG_SEGMENTS and right == BASE_LINK:
        return FAMILY_LEG_SEGMENT_BASE_LINK
    raise InvalidInputError(f'pair is not an included family member: {pair}')


def reversed_pair_id(pair: str) -> str:
    left, right = parse_pair_id(pair)
    return pair_id(right, left)


def require_evaluable_pair(pair: str) -> str:
    """Accept only a canonical included pair ID. Never auto-swap."""
    if not isinstance(pair, str) or not pair.strip():
        raise InvalidInputError(f'pair id must be a non-empty string, got {pair!r}')
    if pair in EXCLUDED_PAIR_SET:
        reason = EXCLUSION_REASONS[pair]
        raise InvalidInputError(
            f'excluded pair may not be evaluated: {pair} ({reason})'
        )
    if pair in INCLUDED_PAIR_SET:
        return pair
    try:
        reversed_id = reversed_pair_id(pair)
    except InvalidInputError:
        reversed_id = ''
    if reversed_id in INCLUDED_PAIR_SET or reversed_id in EXCLUDED_PAIR_SET:
        raise InvalidInputError(
            f'pair id direction is not the registry direction: {pair}'
        )
    raise InvalidInputError(f'undeclared or unknown pair: {pair}')


def require_evaluable_pairs(pairs: tuple[str, ...] | None) -> tuple[str, ...]:
    if pairs is None:
        return INCLUDED_PAIR_IDS
    if not isinstance(pairs, tuple):
        raise InvalidInputError('pair_ids must be a tuple')
    if not pairs:
        raise InvalidInputError('empty pair set is not evaluable')
    seen: set[str] = set()
    validated: list[str] = []
    for pair in pairs:
        canonical = require_evaluable_pair(pair)
        if canonical in seen:
            raise InvalidInputError(f'duplicate pair id: {canonical}')
        seen.add(canonical)
        validated.append(canonical)
    return tuple(validated)


def is_tibia_pair(pair: str) -> bool:
    left, right = parse_pair_id(pair)
    return left.endswith('_tibia') or right.endswith('_tibia')


def uses_aabb_proxy(pair: str) -> bool:
    kind = pair_kind(pair)
    return kind in (
        FAMILY_SENSOR_POD_LEG_SEGMENT,
        FAMILY_LEG_SEGMENT_BASE_LINK,
    )


def registry_metadata() -> Mapping[str, object]:
    return {
        'included_pair_ids': INCLUDED_PAIR_IDS,
        'excluded_pair_ids': EXCLUDED_PAIR_IDS,
        'exclusion_reasons': dict(EXCLUSION_REASONS),
        'n_pair_instances_included': len(INCLUDED_PAIR_IDS),
        'n_pair_instances_excluded': len(EXCLUDED_PAIR_IDS),
    }
