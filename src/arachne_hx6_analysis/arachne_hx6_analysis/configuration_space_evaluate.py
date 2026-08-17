"""G4-D1A offline in-memory configuration-space evaluation.

Reads frozen bytes, verifies Git blob SHA1 without invoking git(1),
evaluates the standing-to-analysis_stowed path over included pairs, and
returns memory objects only.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
No report files, CLI, or write APIs.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
import sys
from typing import Mapping

import yaml

from arachne_hx6_analysis.architecture_baseline import (
    _XACRO_PROPERTY,
    _eval_xacro_expr,
    _g1_baseline_from_xacro,
)
from arachne_hx6_analysis.architecture_kinematics import (
    _capsules_for_pose,
    interpolate_joint_path,
    validate_joint_pose,
)
from arachne_hx6_analysis.architecture_types import G1Baseline
from arachne_hx6_analysis.configuration_space_registry import (
    ANALYSIS_DISKS,
    EXCLUDED_PAIR_IDS,
    EXCLUSION_REASONS,
    EXCLUDE_FAMILY_SPECS,
    FAMILY_LEG_SEGMENT_ANALYSIS_DISK,
    FAMILY_LEG_SEGMENT_BASE_LINK,
    FAMILY_SENSOR_POD_LEG_SEGMENT,
    FOOT_LINKS,
    INCLUDE_FAMILY_SPECS,
    INCLUDED_PAIR_IDS,
    LEG_SEGMENTS,
    is_tibia_pair,
    pair_kind,
    parse_pair_id,
    require_evaluable_pair,
    require_evaluable_pairs,
    uses_aabb_proxy,
)
from arachne_hx6_analysis.configuration_space_types import (
    ANALYSIS_DISK_RECONSTRUCTION,
    APPROVED_SOLVER_TOLERANCE_M,
    ARCHITECTURE_ENVELOPE_RELPATH,
    CONFIGURATION_SPACE_UNSAMPLED,
    ConfigurationSpaceConfig,
    ConfigurationSpaceResult,
    EVALUATED_SCOPE,
    FROZEN_INPUT_RELPATHS,
    FrozenGeometryModelError,
    FrozenInputSpec,
    G1_DESCRIPTION_COMMIT_SHA,
    G1_DESCRIPTION_TREE_SHA,
    G4_D0_CONTRACT_SHA256,
    GEOMETRY_KIND_AABB_PROXY,
    GEOMETRY_KIND_DISK_CAPSULE,
    HARDWARE_VALIDATION_NOT_VALIDATED,
    HEX_ARM_SPAN_M,
    HEX_ROTOR_RADIUS_M,
    IMPLEMENTATION_SCOPE,
    JOINT_UNIT,
    LENGTH_UNIT,
    LIMITATION_AABB_FALSE_POSITIVE,
    LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE,
    LIMITATION_README_ESTIMATE_ONLY,
    LIMITATION_SAMPLED_TRANSITION_ONLY,
    LIMITATION_TIBIA_FOOT_ENDPOINT,
    N_PAIR_INSTANCES_EXCLUDED,
    N_PAIR_INSTANCES_INCLUDED,
    PROXY_STATUS_ANALYSIS_ONLY,
    RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL,
    SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
    SOURCE_STATE_OR_PATH,
    STANDING_POSE_RELPATH,
    SampleRecord,
    SampleSetSummary,
    XACRO_RELPATH,
    require_unique_sample_ids,
    sample_set_status_from_records,
)
from arachne_hx6_analysis.geometry import (
    Aabb,
    Capsule,
    HorizontalDisk,
    box_from_center_size,
    capsule_aabb,
    make_rotor_disks,
    signed_distance_disk_capsule,
    union_aabb,
)
from arachne_hx6_analysis.inputs import (
    as_bool,
    as_float,
    as_int,
    as_list,
    as_mapping,
    as_str,
    require_key,
)
from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    GeometryConvergenceError,
    InvalidInputError,
)

_TOP_LEVEL_KEYS = (
    'status',
    'implementation_authorization_status',
    'implementation_scope',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'report_file_generation_allowed',
    'cli_registration_allowed',
    'gazebo_allowed',
    'px4_allowed',
    'sample_count',
    'source_state_or_path',
    'joint_unit',
    'length_unit',
    'solver',
    'analysis_disks',
    'g4_d0_contract',
    'g1_audit',
    'frozen_inputs',
    'pair_registry',
)
_SOLVER_KEYS = ('tolerance_m', 'tolerance_unit', 'approved_expectation_m')
_DISK_KEYS = (
    'proxy_status',
    'reconstruction',
    'hex_arm_span_m',
    'hex_rotor_radius_m',
)
_CONTRACT_KEYS = ('sha256',)
_G1_AUDIT_KEYS = ('description_commit_sha', 'description_tree_sha')
_FROZEN_FILE_KEYS = ('git_blob_sha1',)
_REGISTRY_KEYS = (
    'include_count',
    'exclude_count',
    'include_families',
    'exclude_families',
)
_INCLUDE_FAMILY_KEYS = ('id', 'count')
_EXCLUDE_FAMILY_KEYS = ('id', 'count', 'reason_code')
_FORBIDDEN_TRUE_FIELDS = (
    'procurement_allowed',
    'hardware_assembly_allowed',
    'report_file_generation_allowed',
    'cli_registration_allowed',
    'gazebo_allowed',
    'px4_allowed',
)


def git_blob_sha1(data: bytes) -> str:
    """Git blob SHA1 of raw file bytes. Does not invoke git(1)."""
    if not isinstance(data, (bytes, bytearray)):
        raise InvalidInputError('blob bytes must be a bytes object')
    payload = b'blob ' + str(len(data)).encode('ascii') + b'\0' + bytes(data)
    return hashlib.sha1(payload).hexdigest()


def default_approved_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_configuration_space_config_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / 'config'
        / 'configuration_space.yaml'
    )


def resolve_under_approved_root(approved_root: Path, relpath: str) -> Path:
    root = Path(approved_root)
    if not isinstance(relpath, str) or not relpath.strip():
        raise InvalidInputError(
            f'relative path must be a non-empty string, got {relpath!r}'
        )
    candidate = Path(relpath)
    if candidate.is_absolute() or '..' in candidate.parts:
        raise InvalidInputError(
            f'input path escapes the approved root: {relpath!r}'
        )
    resolved = (root / candidate).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise InvalidInputError(
            f'input path escapes the approved root: {relpath!r}'
        ) from exc
    return resolved


def _require_exact_keys(
    mapping: Mapping[str, object],
    allowed: tuple[str, ...],
    path: str,
) -> None:
    extra = sorted(set(mapping) - set(allowed))
    missing = [key for key in allowed if key not in mapping]
    if extra:
        raise InvalidInputError(f'{path} unknown keys: {extra}')
    if missing:
        raise InvalidInputError(f'{path} missing keys: {missing}')


def signed_gap_aabb(left: Aabb, right: Aabb) -> float:
    """Deterministic AABB-AABB signed gap in metres.

    Separated on any axis: Euclidean separation of the positive axis gaps.
    Strict positive overlap on all three axes: negative minimum overlap depth.
    Contact returns 0.0 and must not be classified as no-intersection.
    """
    gaps: list[float] = []
    for index in range(3):
        if (
            not math.isfinite(left.minimum[index])
            or not math.isfinite(left.maximum[index])
            or not math.isfinite(right.minimum[index])
            or not math.isfinite(right.maximum[index])
        ):
            raise InvalidInputError('AABB coordinates must be finite')
        if (
            left.maximum[index] < left.minimum[index]
            or right.maximum[index] < right.minimum[index]
        ):
            raise InvalidInputError('AABB maximum must be >= minimum')
        gaps.append(
            max(
                left.minimum[index] - right.maximum[index],
                right.minimum[index] - left.maximum[index],
            )
        )
    positive = [gap for gap in gaps if gap > 0.0]
    if positive:
        return math.sqrt(sum(gap * gap for gap in positive))
    if all(gap < 0.0 for gap in gaps):
        return max(gaps)
    return 0.0


def classify_signed_gap(
    gap: float,
    tolerance_m: float = APPROVED_SOLVER_TOLERANCE_M,
) -> str | None:
    """Return an affirmative result_status, or None when |gap| <= tolerance."""
    if isinstance(gap, bool) or not isinstance(gap, (int, float)):
        raise InvalidInputError(f'signed gap must be a real number, got {gap!r}')
    number = float(gap)
    if not math.isfinite(number):
        raise InvalidInputError('signed gap must be finite')
    if isinstance(tolerance_m, bool) or not isinstance(tolerance_m, (int, float)):
        raise InvalidInputError('solver tolerance must be a real number')
    if tolerance_m != APPROVED_SOLVER_TOLERANCE_M:
        raise InvalidInputError('solver tolerance must remain 1e-9 m')
    if number < -tolerance_m:
        return RESULT_SAMPLED_INTERSECTION_DETECTED
    if number > tolerance_m:
        return RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
    return None


def _load_yaml_mapping(path: Path, path_name: str) -> dict[str, object]:
    if not path.is_file():
        raise InvalidInputError(f'config file not found: {path}')
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {path}: {exc}') from exc
    return as_mapping(raw, path_name)


def load_configuration_space_config(
    path: str | Path | None = None,
) -> ConfigurationSpaceConfig:
    config_path = (
        Path(path) if path is not None else default_configuration_space_config_path()
    )
    root = _load_yaml_mapping(config_path, 'configuration_space')
    _require_exact_keys(root, _TOP_LEVEL_KEYS, 'configuration_space')
    for field in _FORBIDDEN_TRUE_FIELDS:
        as_bool(require_key(root, field, ''), field)
    solver = as_mapping(require_key(root, 'solver', ''), 'solver')
    _require_exact_keys(solver, _SOLVER_KEYS, 'solver')
    if as_str(
        require_key(solver, 'tolerance_unit', 'solver'),
        'solver.tolerance_unit',
    ) != LENGTH_UNIT:
        raise InvalidInputError('solver.tolerance_unit must be m')
    if as_float(
        require_key(solver, 'approved_expectation_m', 'solver'),
        'solver.approved_expectation_m',
    ) != APPROVED_SOLVER_TOLERANCE_M:
        raise InvalidInputError('solver.approved_expectation_m must be 1e-9 m')
    disks = as_mapping(require_key(root, 'analysis_disks', ''), 'analysis_disks')
    _require_exact_keys(disks, _DISK_KEYS, 'analysis_disks')
    if as_str(
        require_key(disks, 'reconstruction', 'analysis_disks'),
        'analysis_disks.reconstruction',
    ) != ANALYSIS_DISK_RECONSTRUCTION:
        raise InvalidInputError(
            'analysis_disks.reconstruction must be FROZEN_G1_GEOMETRY_ONLY'
        )
    contract = as_mapping(require_key(root, 'g4_d0_contract', ''), 'g4_d0_contract')
    _require_exact_keys(contract, _CONTRACT_KEYS, 'g4_d0_contract')
    g1_audit = as_mapping(require_key(root, 'g1_audit', ''), 'g1_audit')
    _require_exact_keys(g1_audit, _G1_AUDIT_KEYS, 'g1_audit')
    frozen_raw = as_mapping(require_key(root, 'frozen_inputs', ''), 'frozen_inputs')
    extra = sorted(set(frozen_raw) - set(FROZEN_INPUT_RELPATHS))
    missing = [key for key in FROZEN_INPUT_RELPATHS if key not in frozen_raw]
    if extra:
        raise InvalidInputError(f'frozen_inputs unknown keys: {extra}')
    if missing:
        raise InvalidInputError(f'frozen_inputs missing keys: {missing}')
    frozen_inputs: list[FrozenInputSpec] = []
    for relpath in FROZEN_INPUT_RELPATHS:
        spec = as_mapping(frozen_raw[relpath], f'frozen_inputs.{relpath}')
        _require_exact_keys(spec, _FROZEN_FILE_KEYS, f'frozen_inputs.{relpath}')
        frozen_inputs.append(
            FrozenInputSpec(
                relpath=relpath,
                git_blob_sha1=as_str(
                    require_key(spec, 'git_blob_sha1', f'frozen_inputs.{relpath}'),
                    f'frozen_inputs.{relpath}.git_blob_sha1',
                ),
            )
        )
    registry = as_mapping(require_key(root, 'pair_registry', ''), 'pair_registry')
    _require_exact_keys(registry, _REGISTRY_KEYS, 'pair_registry')
    include_count = as_int(
        require_key(registry, 'include_count', 'pair_registry'),
        'pair_registry.include_count',
    )
    exclude_count = as_int(
        require_key(registry, 'exclude_count', 'pair_registry'),
        'pair_registry.exclude_count',
    )
    if include_count != N_PAIR_INSTANCES_INCLUDED:
        raise InvalidInputError('pair_registry.include_count must be 162')
    if exclude_count != N_PAIR_INSTANCES_EXCLUDED:
        raise InvalidInputError('pair_registry.exclude_count must be 420')
    include_families = as_list(
        require_key(registry, 'include_families', 'pair_registry'),
        'pair_registry.include_families',
    )
    exclude_families = as_list(
        require_key(registry, 'exclude_families', 'pair_registry'),
        'pair_registry.exclude_families',
    )
    include_ids: list[str] = []
    if len(include_families) != len(INCLUDE_FAMILY_SPECS):
        raise InvalidInputError(
            'pair_registry.include_families has the wrong length'
        )
    for index, (expected_id, expected_count, _reason) in enumerate(INCLUDE_FAMILY_SPECS):
        item = as_mapping(
            include_families[index],
            f'pair_registry.include_families[{index}]',
        )
        _require_exact_keys(
            item, _INCLUDE_FAMILY_KEYS, f'pair_registry.include_families[{index}]'
        )
        family_id = as_str(
            require_key(item, 'id', ''),
            f'pair_registry.include_families[{index}].id',
        )
        count = as_int(
            require_key(item, 'count', ''),
            f'pair_registry.include_families[{index}].count',
        )
        if family_id != expected_id or count != expected_count:
            raise InvalidInputError(
                f'include family mismatch at {index}: {family_id} x {count}'
            )
        include_ids.append(family_id)
    exclude_ids: list[str] = []
    reason_codes: list[str] = []
    if len(exclude_families) != len(EXCLUDE_FAMILY_SPECS):
        raise InvalidInputError(
            'pair_registry.exclude_families has the wrong length'
        )
    for index, (expected_id, expected_count, expected_reason) in enumerate(
        EXCLUDE_FAMILY_SPECS
    ):
        item = as_mapping(
            exclude_families[index],
            f'pair_registry.exclude_families[{index}]',
        )
        _require_exact_keys(
            item, _EXCLUDE_FAMILY_KEYS, f'pair_registry.exclude_families[{index}]'
        )
        family_id = as_str(
            require_key(item, 'id', ''),
            f'pair_registry.exclude_families[{index}].id',
        )
        count = as_int(
            require_key(item, 'count', ''),
            f'pair_registry.exclude_families[{index}].count',
        )
        reason = as_str(
            require_key(item, 'reason_code', ''),
            f'pair_registry.exclude_families[{index}].reason_code',
        )
        if (
            family_id != expected_id
            or count != expected_count
            or reason != expected_reason
        ):
            raise InvalidInputError(f'exclude family mismatch at {index}')
        exclude_ids.append(family_id)
        reason_codes.append(reason)
    if as_str(require_key(root, 'joint_unit', ''), 'joint_unit') != JOINT_UNIT:
        raise InvalidInputError('joint_unit must be rad')
    if as_str(require_key(root, 'length_unit', ''), 'length_unit') != LENGTH_UNIT:
        raise InvalidInputError('length_unit must be m')
    return ConfigurationSpaceConfig(
        status=as_str(require_key(root, 'status', ''), 'status'),
        implementation_authorization_status=as_str(
            require_key(root, 'implementation_authorization_status', ''),
            'implementation_authorization_status',
        ),
        implementation_scope=as_str(
            require_key(root, 'implementation_scope', ''),
            'implementation_scope',
        ),
        procurement_allowed=as_bool(
            require_key(root, 'procurement_allowed', ''),
            'procurement_allowed',
        ),
        hardware_assembly_allowed=as_bool(
            require_key(root, 'hardware_assembly_allowed', ''),
            'hardware_assembly_allowed',
        ),
        report_file_generation_allowed=as_bool(
            require_key(root, 'report_file_generation_allowed', ''),
            'report_file_generation_allowed',
        ),
        cli_registration_allowed=as_bool(
            require_key(root, 'cli_registration_allowed', ''),
            'cli_registration_allowed',
        ),
        gazebo_allowed=as_bool(
            require_key(root, 'gazebo_allowed', ''), 'gazebo_allowed'
        ),
        px4_allowed=as_bool(require_key(root, 'px4_allowed', ''), 'px4_allowed'),
        sample_count=as_int(require_key(root, 'sample_count', ''), 'sample_count'),
        source_state_or_path=as_str(
            require_key(root, 'source_state_or_path', ''),
            'source_state_or_path',
        ),
        joint_unit=as_str(require_key(root, 'joint_unit', ''), 'joint_unit'),
        length_unit=as_str(require_key(root, 'length_unit', ''), 'length_unit'),
        solver_tolerance_m=as_float(
            require_key(solver, 'tolerance_m', 'solver'),
            'solver.tolerance_m',
        ),
        hex_arm_span_m=as_float(
            require_key(disks, 'hex_arm_span_m', 'analysis_disks'),
            'analysis_disks.hex_arm_span_m',
        ),
        hex_rotor_radius_m=as_float(
            require_key(disks, 'hex_rotor_radius_m', 'analysis_disks'),
            'analysis_disks.hex_rotor_radius_m',
        ),
        analysis_disk_proxy_status=as_str(
            require_key(disks, 'proxy_status', 'analysis_disks'),
            'analysis_disks.proxy_status',
        ),
        g4_d0_contract_sha256=as_str(
            require_key(contract, 'sha256', 'g4_d0_contract'),
            'g4_d0_contract.sha256',
        ),
        g1_description_commit_sha=as_str(
            require_key(g1_audit, 'description_commit_sha', 'g1_audit'),
            'g1_audit.description_commit_sha',
        ),
        g1_description_tree_sha=as_str(
            require_key(g1_audit, 'description_tree_sha', 'g1_audit'),
            'g1_audit.description_tree_sha',
        ),
        frozen_inputs=tuple(frozen_inputs),
        include_family_ids=tuple(include_ids),
        exclude_family_ids=tuple(exclude_ids),
        exclusion_reason_codes=tuple(reason_codes),
    )


def verify_frozen_blob_bytes(
    config: ConfigurationSpaceConfig,
    blobs: Mapping[str, bytes],
) -> tuple[str, ...]:
    """Compare provided bytes to approved blob SHAs. Missing keys are returned."""
    missing: list[str] = []
    for spec in config.frozen_inputs:
        if spec.relpath not in blobs:
            missing.append(spec.relpath)
            continue
        digest = git_blob_sha1(blobs[spec.relpath])
        if digest != spec.git_blob_sha1:
            raise InvalidInputError(
                f'frozen blob SHA mismatch for {spec.relpath}: '
                f'got {digest}, expected {spec.git_blob_sha1}'
            )
    extra = sorted(set(blobs) - set(FROZEN_INPUT_RELPATHS))
    if extra:
        raise InvalidInputError(f'frozen blob map has unknown keys: {extra}')
    return tuple(missing)


_FROZEN_PYTHON_RELPATH_PREFIX = 'src/arachne_hx6_analysis/'


def _imported_module_name_for_frozen_relpath(relpath: str) -> str | None:
    if not relpath.endswith('.py') or not relpath.startswith(
        _FROZEN_PYTHON_RELPATH_PREFIX
    ):
        return None
    return relpath[len(_FROZEN_PYTHON_RELPATH_PREFIX) : -3].replace('/', '.')


def verify_imported_frozen_python_modules(config: ConfigurationSpaceConfig) -> None:
    """Compare actually imported module file bytes to approved blob SHAs.

    Reads sys.modules[name].__file__ bytes and hashes them as Git blobs.
    Does not invoke git(1). A matching copy under approved_root is not
    sufficient if the loaded module bytes differ.
    """
    for spec in config.frozen_inputs:
        module_name = _imported_module_name_for_frozen_relpath(spec.relpath)
        if module_name is None:
            continue
        module = sys.modules.get(module_name)
        if module is None:
            raise InvalidInputError(
                f'frozen Python module is not imported: {module_name}'
            )
        file_path = getattr(module, '__file__', None)
        if not isinstance(file_path, str) or not file_path:
            raise InvalidInputError(
                f'imported module {module_name} has no __file__'
            )
        path = Path(file_path)
        if not path.is_file():
            raise InvalidInputError(
                f'imported module file is missing: {file_path}'
            )
        digest = git_blob_sha1(path.read_bytes())
        if digest != spec.git_blob_sha1:
            raise InvalidInputError(
                f'imported module SHA mismatch for {spec.relpath}: '
                f'got {digest}, expected {spec.git_blob_sha1}'
            )


def _parse_xacro_numeric_properties_from_bytes(data: bytes) -> dict[str, float]:
    """Parse Xacro numeric properties from already-hashed frozen bytes."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise InvalidInputError(f'invalid xacro encoding: {exc}') from exc
    matches = list(_XACRO_PROPERTY.finditer(text))
    loose_count = len(re.findall(r'<xacro:property\b', text))
    if loose_count != len(matches):
        raise InvalidInputError(
            'xacro has xacro:property tags that do not match the strict '
            'single-line name= then value= self-closing pattern'
        )
    raw: dict[str, str] = {}
    for match in matches:
        name = match.group(1)
        value = match.group(2)
        if name in raw:
            raise InvalidInputError(f'duplicate xacro property {name!r}')
        raw[name] = value
    if not raw:
        raise InvalidInputError('no xacro properties in frozen xacro bytes')
    numeric: dict[str, float] = {}
    pending: dict[str, str] = {}
    for name, value in raw.items():
        try:
            numeric[name] = float(value)
        except ValueError:
            if value.startswith('${') and value.endswith('}') and len(value) > 3:
                pending[name] = value
            else:
                raise InvalidInputError(
                    f'xacro property {name!r} is not numeric and not a '
                    f'${{expr}}: {value!r}'
                ) from None
    for _iteration in range(len(pending) + 2):
        if not pending:
            break
        resolved: list[str] = []
        for name, value in pending.items():
            expr = value[2:-1]
            try:
                numeric[name] = _eval_xacro_expr(expr, numeric)
                resolved.append(name)
            except InvalidInputError:
                continue
        for name in resolved:
            del pending[name]
        if not resolved:
            break
    if pending:
        raise InvalidInputError(
            'unresolved or unparseable xacro expressions: '
            + ', '.join(f'{name}={pending[name]!r}' for name in sorted(pending))
        )
    return numeric


def _load_standing_joints_from_bytes(data: bytes) -> dict[str, float]:
    try:
        raw = yaml.safe_load(data.decode('utf-8'))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise InvalidInputError(f'invalid standing_pose.yaml: {exc}') from exc
    root = as_mapping(raw, 'standing_pose')
    ns = as_mapping(require_key(root, '/**', 'standing_pose'), 'standing_pose./**')
    params = as_mapping(
        require_key(ns, 'ros__parameters', 'standing_pose./**'),
        'standing_pose./**.ros__parameters',
    )
    joints: dict[str, float] = {}
    for key, value in params.items():
        name = as_str(key, 'standing_pose parameter name')
        if not name.startswith('zeros.'):
            raise InvalidInputError(
                f'standing_pose unexpected key {name!r}; expected zeros.<joint>'
            )
        joint = name[len('zeros.'):]
        joints[joint] = as_float(value, name)
    return joints


def _read_frozen_from_root(
    config: ConfigurationSpaceConfig,
    approved_root: Path,
) -> tuple[tuple[str, ...], dict[str, bytes]]:
    blobs: dict[str, bytes] = {}
    missing: list[str] = []
    for spec in config.frozen_inputs:
        path = resolve_under_approved_root(approved_root, spec.relpath)
        if not path.is_file():
            missing.append(spec.relpath)
            continue
        data = path.read_bytes()
        digest = git_blob_sha1(data)
        if digest != spec.git_blob_sha1:
            raise InvalidInputError(
                f'frozen blob SHA mismatch for {spec.relpath}: '
                f'got {digest}, expected {spec.git_blob_sha1}'
            )
        blobs[spec.relpath] = data
    return tuple(missing), blobs


def _load_analysis_stowed_joints(envelope_bytes: bytes) -> dict[str, float]:
    try:
        raw = yaml.safe_load(envelope_bytes.decode('utf-8'))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise InvalidInputError(
            f'invalid architecture_envelope.yaml: {exc}'
        ) from exc
    root = as_mapping(raw, 'architecture_envelope')
    stowed = as_mapping(
        require_key(root, 'analysis_stowed', ''),
        'analysis_stowed',
    )
    joints_raw = as_mapping(
        require_key(stowed, 'joints', 'analysis_stowed'),
        'analysis_stowed.joints',
    )
    return {
        as_str(name, 'analysis_stowed.joints key'): as_float(
            value, f'analysis_stowed.joints.{name}'
        )
        for name, value in joints_raw.items()
    }


def _require_frozen_g1_geometry(baseline: G1Baseline, xacro_values: Mapping[str, float]) -> None:
    if abs(baseline.hex_arm_span_m - HEX_ARM_SPAN_M) > 1.0e-12:
        raise InvalidInputError(
            f'G1 hex_arm_span must be {HEX_ARM_SPAN_M} m, got {baseline.hex_arm_span_m}'
        )
    radius = as_float(xacro_values['hex_rotor_radius'], 'hex_rotor_radius')
    if abs(radius - HEX_ROTOR_RADIUS_M) > 1.0e-12:
        raise InvalidInputError(
            f'G1 hex_rotor_radius must be {HEX_ROTOR_RADIUS_M} m, got {radius}'
        )


def _analysis_disks(baseline: G1Baseline) -> dict[str, HorizontalDisk]:
    try:
        disks = make_rotor_disks(
            HEX_ARM_SPAN_M,
            2.0 * HEX_ROTOR_RADIUS_M,
            baseline.rotor_plane_z_m,
            6,
            baseline.first_motor_yaw_rad,
        )
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            'analysis disk model construction failed'
        ) from exc
    named = {f'analysis_disk_{disk.name}': disk for disk in disks}
    if tuple(named) != ANALYSIS_DISKS:
        raise FrozenGeometryModelError(
            'analysis disk names do not match the registry'
        )
    return named


def _static_boxes(baseline: G1Baseline) -> dict[str, Aabb]:
    try:
        return {
            'base_link': box_from_center_size(
                (0.0, 0.0, 0.0),
                (baseline.body_length_m, baseline.body_width_m, baseline.body_height_m),
            ),
            'left_sensor_pod': box_from_center_size(
                (0.0, baseline.sensor_pod_y_m, baseline.sensor_pod_z_m),
                (
                    baseline.sensor_pod_size_x_m,
                    baseline.sensor_pod_size_y_m,
                    baseline.sensor_pod_size_z_m,
                ),
            ),
            'right_sensor_pod': box_from_center_size(
                (0.0, -baseline.sensor_pod_y_m, baseline.sensor_pod_z_m),
                (
                    baseline.sensor_pod_size_x_m,
                    baseline.sensor_pod_size_y_m,
                    baseline.sensor_pod_size_z_m,
                ),
            ),
        }
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            'static AABB model construction failed'
        ) from exc


def _capsules_by_name(
    pose: Mapping[str, float],
    baseline: G1Baseline,
) -> dict[str, Capsule]:
    try:
        capsules = _capsules_for_pose(pose, baseline)
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            'capsule model construction failed'
        ) from exc
    named: dict[str, Capsule] = {}
    for capsule in capsules:
        if capsule.name in named:
            raise FrozenGeometryModelError(
                f'duplicate capsule name: {capsule.name}'
            )
        named[capsule.name] = capsule
    missing_capsules = [name for name in LEG_SEGMENTS if name not in named]
    if missing_capsules:
        raise FrozenGeometryModelError(
            f'missing capsule: {missing_capsules[0]}'
        )
    missing_feet = [name for name in FOOT_LINKS if name not in named]
    if missing_feet:
        raise FrozenGeometryModelError(
            f'missing foot endpoint: {missing_feet[0]}'
        )
    return named


def _require_named_model(mapping: Mapping[str, object], name: str, kind: str):
    item = mapping.get(name)
    if item is None:
        raise FrozenGeometryModelError(f'missing {kind}: {name}')
    return item


def _tibia_foot(capsules: Mapping[str, Capsule], segment: str) -> Capsule:
    prefix = segment[: -len('_tibia')]
    foot = capsules.get(f'{prefix}_foot')
    if foot is None:
        raise FrozenGeometryModelError(
            f'missing tibia foot endpoint for {segment}'
        )
    return foot


def _leg_aabb(capsules: Mapping[str, Capsule], segment: str) -> Aabb:
    capsule = _require_named_model(capsules, segment, 'capsule')
    boxes = [capsule_aabb(capsule)]
    if segment.endswith('_tibia'):
        boxes.append(capsule_aabb(_tibia_foot(capsules, segment)))
    try:
        return union_aabb(boxes)
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            f'AABB model is invalid for {segment}'
        ) from exc


def _sample_id(index: int, pair: str) -> str:
    return f'path:{SOURCE_STATE_OR_PATH}:i={index:05d}:pair={pair}'


def _geometry_source_tags(
    pair: str,
    frozen_shas: Mapping[str, str],
) -> tuple[str, ...]:
    kind = (
        GEOMETRY_KIND_AABB_PROXY if uses_aabb_proxy(pair) else GEOMETRY_KIND_DISK_CAPSULE
    )
    tags = [
        kind,
        f'proxy_status={PROXY_STATUS_ANALYSIS_ONLY}',
        f'xacro_blob={frozen_shas[XACRO_RELPATH]}',
        f'standing_pose_blob={frozen_shas[STANDING_POSE_RELPATH]}',
    ]
    if kind == GEOMETRY_KIND_DISK_CAPSULE:
        tags.append('primitive=signed_distance_disk_capsule')
    else:
        tags.append('primitive=aabb_proxy')
        tags.append('aabb_proxy')
    return tuple(tags)


def _pair_limitations(pair: str, result_status: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if is_tibia_pair(pair):
        reasons.append(LIMITATION_TIBIA_FOOT_ENDPOINT)
    if (
        uses_aabb_proxy(pair)
        and result_status == RESULT_SAMPLED_INTERSECTION_DETECTED
    ):
        reasons.append(LIMITATION_AABB_FALSE_POSITIVE)
    return tuple(reasons)


def _require_finite_model_gap(gap: object, context: str) -> float:
    if isinstance(gap, bool) or not isinstance(gap, (int, float)):
        raise FrozenGeometryModelError(f'{context} gap is not a real number')
    number = float(gap)
    if not math.isfinite(number):
        raise FrozenGeometryModelError(f'{context} gap is not finite')
    return number


def _certified_disk_capsule_gap(disk: HorizontalDisk, capsule: Capsule) -> float:
    try:
        gap = signed_distance_disk_capsule(disk, capsule)
    except GeometryConvergenceError:
        raise
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            f'certified disk-capsule model is invalid for {capsule.name}'
        ) from exc
    return _require_finite_model_gap(gap, f'disk-capsule {capsule.name}')


def _disk_capsule_gap(
    disk: HorizontalDisk,
    capsules: Mapping[str, Capsule],
    segment: str,
) -> float:
    capsule = _require_named_model(capsules, segment, 'capsule')
    gap = _certified_disk_capsule_gap(disk, capsule)
    if segment.endswith('_tibia'):
        gap = min(
            gap,
            _certified_disk_capsule_gap(disk, _tibia_foot(capsules, segment)),
        )
    return gap


def _signed_gap_aabb_for_approved_pair(left: Aabb, right: Aabb) -> float:
    try:
        gap = signed_gap_aabb(left, right)
    except InvalidInputError as exc:
        raise FrozenGeometryModelError(
            'AABB distance model is invalid or inconsistent'
        ) from exc
    return _require_finite_model_gap(gap, 'AABB')


def evaluate_declared_pair_gap(
    pair: str,
    capsules: Mapping[str, Capsule],
    disks: Mapping[str, HorizontalDisk],
    boxes: Mapping[str, Aabb],
) -> float:
    canonical = require_evaluable_pair(pair)
    kind = pair_kind(canonical)
    left, right = parse_pair_id(canonical)
    if kind == FAMILY_LEG_SEGMENT_ANALYSIS_DISK:
        disk = _require_named_model(disks, right, 'analysis disk')
        gap = _disk_capsule_gap(disk, capsules, left)
    elif kind == FAMILY_SENSOR_POD_LEG_SEGMENT:
        pod = _require_named_model(boxes, left, 'sensor pod AABB')
        gap = _signed_gap_aabb_for_approved_pair(pod, _leg_aabb(capsules, right))
    elif kind == FAMILY_LEG_SEGMENT_BASE_LINK:
        body = _require_named_model(boxes, right, 'base_link AABB')
        gap = _signed_gap_aabb_for_approved_pair(_leg_aabb(capsules, left), body)
    else:
        raise InvalidInputError(f'undeclared pair family: {canonical}')
    return _require_finite_model_gap(gap, f'pair {canonical}')


def _build_summary(
    config: ConfigurationSpaceConfig,
    *,
    sample_set_status: str,
    n_samples_valid: int,
    n_records_valid: int,
    extra_limitations: tuple[str, ...],
) -> SampleSetSummary:
    expected = config.sample_count * N_PAIR_INSTANCES_INCLUDED
    limitations = [
        LIMITATION_SAMPLED_TRANSITION_ONLY,
        LIMITATION_README_ESTIMATE_ONLY,
    ]
    for item in extra_limitations:
        if item not in limitations:
            limitations.append(item)
    return SampleSetSummary(
        sample_set_status=sample_set_status,
        configuration_space_status=CONFIGURATION_SPACE_UNSAMPLED,
        included_pair_ids=INCLUDED_PAIR_IDS,
        excluded_pair_ids=EXCLUDED_PAIR_IDS,
        exclusion_reasons=dict(EXCLUSION_REASONS),
        n_pair_instances_included=N_PAIR_INSTANCES_INCLUDED,
        n_pair_instances_excluded=N_PAIR_INSTANCES_EXCLUDED,
        evaluated_scope=EVALUATED_SCOPE,
        n_samples_requested=config.sample_count,
        n_samples_valid=n_samples_valid,
        n_records_expected=expected,
        n_records_valid=n_records_valid,
        n_records_undetermined=expected - n_records_valid,
        limitation_reasons=tuple(limitations),
        transition_proof_flag=LIMITATION_SAMPLED_TRANSITION_ONLY,
        implementation_scope=IMPLEMENTATION_SCOPE,
        status=STATUS_ANALYSIS_ONLY,
        procurement_allowed=False,
        hardware_assembly_allowed=False,
        report_file_generation_allowed=False,
        cli_registration_allowed=False,
        gazebo_allowed=False,
        px4_allowed=False,
        g1_description_commit_sha=G1_DESCRIPTION_COMMIT_SHA,
        g1_description_tree_sha=G1_DESCRIPTION_TREE_SHA,
        g4_d0_contract_sha256=G4_D0_CONTRACT_SHA256,
        frozen_input_blob_sha1={
            spec.relpath: spec.git_blob_sha1 for spec in config.frozen_inputs
        },
    )


def evaluate_configuration_space(
    config: ConfigurationSpaceConfig | None = None,
    *,
    approved_root: Path | None = None,
    poses: tuple[Mapping[str, float], ...] | None = None,
    pair_ids: tuple[str, ...] | None = None,
) -> ConfigurationSpaceResult:
    """Evaluate included pairs in memory. Never writes a report file.

    Frozen Xacro and standing pose are parsed from the same approved_root
    file bytes that were SHA-verified. Caller-supplied file_bytes are not
    accepted.
    """
    loaded = config if config is not None else load_configuration_space_config()
    verify_imported_frozen_python_modules(loaded)
    root = Path(approved_root) if approved_root is not None else default_approved_root()
    requested_pairs = require_evaluable_pairs(pair_ids)
    missing, blobs = _read_frozen_from_root(loaded, root)
    if missing:
        summary = _build_summary(
            loaded,
            sample_set_status=SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
            n_samples_valid=0,
            n_records_valid=0,
            extra_limitations=(),
        )
        return ConfigurationSpaceResult(records=(), summary=summary)

    xacro_values = _parse_xacro_numeric_properties_from_bytes(blobs[XACRO_RELPATH])
    baseline = _g1_baseline_from_xacro(xacro_values)
    _require_frozen_g1_geometry(baseline, xacro_values)
    standing = validate_joint_pose(
        _load_standing_joints_from_bytes(blobs[STANDING_POSE_RELPATH]),
        baseline.joint_limits,
        'standing_pose',
    )
    stowed = validate_joint_pose(
        _load_analysis_stowed_joints(blobs[ARCHITECTURE_ENVELOPE_RELPATH]),
        baseline.joint_limits,
        'analysis_stowed.joints',
    )
    if poses is None:
        path_poses = interpolate_joint_path(standing, stowed, loaded.sample_count)
    else:
        if len(poses) == 0:
            raise InvalidInputError('empty sample set')
        path_poses = tuple(
            validate_joint_pose(pose, baseline.joint_limits, f'poses[{index}]')
            for index, pose in enumerate(poses)
        )
    if len(path_poses) == 0:
        raise InvalidInputError('empty sample set')

    try:
        disks = _analysis_disks(baseline)
        boxes = _static_boxes(baseline)
    except FrozenGeometryModelError:
        summary = _build_summary(
            loaded,
            sample_set_status=SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL,
            n_samples_valid=0,
            n_records_valid=0,
            extra_limitations=(),
        )
        return ConfigurationSpaceResult(records=(), summary=summary)

    frozen_shas = {spec.relpath: spec.git_blob_sha1 for spec in loaded.frozen_inputs}
    records: list[SampleRecord] = []
    extra_limitations: list[str] = []
    geometry_undetermined = False
    for index, pose in enumerate(path_poses):
        try:
            capsules = _capsules_by_name(pose, baseline)
        except FrozenGeometryModelError:
            geometry_undetermined = True
            continue
        for pair in requested_pairs:
            try:
                gap = evaluate_declared_pair_gap(pair, capsules, disks, boxes)
            except GeometryConvergenceError:
                geometry_undetermined = True
                if LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE not in extra_limitations:
                    extra_limitations.append(LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE)
                continue
            except FrozenGeometryModelError:
                geometry_undetermined = True
                continue
            if (
                isinstance(gap, bool)
                or not isinstance(gap, (int, float))
                or not math.isfinite(gap)
            ):
                geometry_undetermined = True
                continue
            status = classify_signed_gap(gap, loaded.solver_tolerance_m)
            if status is None:
                geometry_undetermined = True
                if LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE not in extra_limitations:
                    extra_limitations.append(LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE)
                continue
            records.append(
                SampleRecord(
                    sample_id=_sample_id(index, pair),
                    source_state_or_path=SOURCE_STATE_OR_PATH,
                    evaluated_pair=pair,
                    joint_values=pose,
                    geometry_source=_geometry_source_tags(pair, frozen_shas),
                    proxy_status=PROXY_STATUS_ANALYSIS_ONLY,
                    hardware_validation_status=HARDWARE_VALIDATION_NOT_VALIDATED,
                    nominal_separation_or_intersection=gap,
                    result_status=status,
                    limitation_reasons=_pair_limitations(pair, status),
                )
            )

    require_unique_sample_ids(records)
    expected = loaded.sample_count * N_PAIR_INSTANCES_INCLUDED
    evaluated_slots = len(path_poses) * len(requested_pairs)
    n_records_valid = len(records)
    n_undetermined = expected - n_records_valid
    if evaluated_slots != expected:
        geometry_undetermined = True
    if geometry_undetermined or n_records_valid != expected:
        sample_set_status = SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
    else:
        recomputed = sample_set_status_from_records(records, n_undetermined)
        if recomputed is None:
            sample_set_status = SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL
        else:
            sample_set_status = recomputed
    summary = _build_summary(
        loaded,
        sample_set_status=sample_set_status,
        n_samples_valid=len(path_poses),
        n_records_valid=n_records_valid,
        extra_limitations=tuple(extra_limitations),
    )
    return ConfigurationSpaceResult(records=tuple(records), summary=summary)
