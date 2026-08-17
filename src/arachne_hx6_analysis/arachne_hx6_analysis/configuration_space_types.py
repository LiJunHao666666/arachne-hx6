"""G4-D1A in-memory configuration-space types and invariants.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY
No report files, CLI, or write APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from arachne_hx6_analysis.architecture_types import (
    REQUIRED_JOINT_NAMES,
    TRANSITION_PROOF_FLAG,
)
from arachne_hx6_analysis.geometry_solver import GEOMETRY_SOLVER_TOLERANCE_M
from arachne_hx6_analysis.model import (
    STATUS_ANALYSIS_ONLY,
    AnalysisError,
    InvalidInputError,
)

IMPLEMENTATION_AUTHORIZATION_STATUS = 'GPT_AUTHORIZED'
IMPLEMENTATION_SCOPE = 'G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY'
SOURCE_STATE_OR_PATH = 'standing_to_analysis_stowed'
EVALUATED_SCOPE = (
    'G4_D1A_INCLUDED_PAIRS_ONLY_STANDING_TO_ANALYSIS_STOWED_SAMPLED_PATH'
)
JOINT_UNIT = 'rad'
LENGTH_UNIT = 'm'
SAMPLE_COUNT_REQUIRED = 101
N_PAIR_INSTANCES_INCLUDED = 162
N_PAIR_INSTANCES_EXCLUDED = 420
N_RECORDS_EXPECTED_FULL = SAMPLE_COUNT_REQUIRED * N_PAIR_INSTANCES_INCLUDED
APPROVED_SOLVER_TOLERANCE_M = 1.0e-9
HEX_ARM_SPAN_M = 0.30
HEX_ROTOR_RADIUS_M = 0.060
ANALYSIS_DISK_RECONSTRUCTION = 'FROZEN_G1_GEOMETRY_ONLY'
G4_D0_CONTRACT_SHA256 = (
    '199babf629d9db67791fcb75b7c4d5e253f6c253ad4762d6027ecb8e3de8450c'
)
G1_DESCRIPTION_COMMIT_SHA = '3dc6f50d3852ad94c32c4fd97f0232e6b941f712'
G1_DESCRIPTION_TREE_SHA = 'd342e65c08d2c94c42323f7fd4d2cdc3d96efe5d'

PROXY_STATUS_ANALYSIS_ONLY = 'ANALYSIS_PROXY_ONLY'
HARDWARE_VALIDATION_NOT_VALIDATED = 'NOT_HARDWARE_VALIDATED'

RESULT_SAMPLED_INTERSECTION_DETECTED = 'SAMPLED_INTERSECTION_DETECTED'
RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE = (
    'NO_INTERSECTION_AT_EVALUATED_SAMPLE'
)
SAMPLE_SET_NO_INTERSECTION = 'NO_INTERSECTION_IN_EVALUATED_SAMPLES'
SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL = 'UNDETERMINED_GEOMETRY_MODEL'
SAMPLE_SET_UNDETERMINED_MISSING_INPUT = 'UNDETERMINED_MISSING_INPUT'
CONFIGURATION_SPACE_UNSAMPLED = (
    'UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE'
)

ALLOWED_RESULT_STATUSES = (
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
)
ALLOWED_SAMPLE_SET_STATUSES = (
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    SAMPLE_SET_NO_INTERSECTION,
    SAMPLE_SET_UNDETERMINED_GEOMETRY_MODEL,
    SAMPLE_SET_UNDETERMINED_MISSING_INPUT,
)
AFFIRMATIVE_SAMPLE_SET_STATUSES = (
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    SAMPLE_SET_NO_INTERSECTION,
)

EXCL_SENSOR_POD_DISK_NOT_IN_G4_D0_4_1_1 = (
    'EXCL_SENSOR_POD_DISK_NOT_IN_G4_D0_4_1_1'
)
EXCL_CAMERA_NOT_AUTHORIZED = 'EXCL_CAMERA_NOT_AUTHORIZED'
EXCL_INTER_LEG_DEFERRED_FROM_D1A = 'EXCL_INTER_LEG_DEFERRED_FROM_D1A'
EXCL_LEG_HEX_ARM_DEFERRED_FROM_D1A = 'EXCL_LEG_HEX_ARM_DEFERRED_FROM_D1A'
EXCL_LEG_HEX_HUB_DEFERRED_FROM_D1A = 'EXCL_LEG_HEX_HUB_DEFERRED_FROM_D1A'
EXCL_URDF_ROTOR_CYLINDER_NOT_HARDWARE_PROP = (
    'EXCL_URDF_ROTOR_CYLINDER_NOT_HARDWARE_PROP'
)
EXCL_POD_FOOT_NOT_A_CONTRACT_PAIR = 'EXCL_POD_FOOT_NOT_A_CONTRACT_PAIR'

ALLOWED_EXCLUSION_REASON_CODES = (
    EXCL_SENSOR_POD_DISK_NOT_IN_G4_D0_4_1_1,
    EXCL_CAMERA_NOT_AUTHORIZED,
    EXCL_INTER_LEG_DEFERRED_FROM_D1A,
    EXCL_LEG_HEX_ARM_DEFERRED_FROM_D1A,
    EXCL_LEG_HEX_HUB_DEFERRED_FROM_D1A,
    EXCL_URDF_ROTOR_CYLINDER_NOT_HARDWARE_PROP,
    EXCL_POD_FOOT_NOT_A_CONTRACT_PAIR,
)

LIMITATION_AABB_FALSE_POSITIVE = (
    'CONSERVATIVE_AABB_PROXY_POSSIBLE_FALSE_POSITIVE'
)
LIMITATION_TIBIA_FOOT_ENDPOINT = (
    'TIBIA_CAPSULE_USES_G2_FOOT_SPHERE_ENDPOINT'
)
LIMITATION_SAMPLED_TRANSITION_ONLY = TRANSITION_PROOF_FLAG
LIMITATION_README_ESTIMATE_ONLY = (
    'README_DISTANCE_IS_BASELINE_REPORTED_ESTIMATE_ONLY'
)
LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE = 'GAP_WITHIN_SOLVER_TOLERANCE'

ALLOWED_LIMITATION_REASONS = (
    LIMITATION_AABB_FALSE_POSITIVE,
    LIMITATION_TIBIA_FOOT_ENDPOINT,
    LIMITATION_SAMPLED_TRANSITION_ONLY,
    LIMITATION_README_ESTIMATE_ONLY,
    LIMITATION_GAP_WITHIN_SOLVER_TOLERANCE,
)

FORBIDDEN_STATUS_WORDS = (
    'VIABLE',
    'FLYABLE',
    'SAFE_TO_FLY',
    'PROCUREMENT_READY',
    'RECOMMENDED_FOR_PURCHASE',
    'VALIDATED_HARDWARE',
    'STOWED_PASS',
    'VALID_STOWED_POSE',
    'UNDETERMINED',
)

FAMILY_LEG_SEGMENT_ANALYSIS_DISK = 'leg_segment__analysis_disk'
FAMILY_SENSOR_POD_LEG_SEGMENT = 'sensor_pod__leg_segment'
FAMILY_LEG_SEGMENT_BASE_LINK = 'leg_segment__base_link'
FAMILY_SENSOR_POD_ANALYSIS_DISK = 'sensor_pod__analysis_disk'
FAMILY_CAMERA = 'camera_link__unauthorized_targets'
FAMILY_INTER_LEG = 'inter_leg_segment'
FAMILY_LEG_HEX_ARM = 'leg_segment__hex_arm'
FAMILY_LEG_HEX_HUB = 'leg_segment__hex_hub'
FAMILY_LEG_URDF_ROTOR = 'leg_segment__urdf_rotor_cylinder'
FAMILY_POD_FOOT = 'sensor_pod__foot'

GEOMETRY_KIND_DISK_CAPSULE = 'disk_capsule'
GEOMETRY_KIND_AABB_PROXY = 'aabb_proxy'

FROZEN_INPUT_RELPATHS = (
    'src/arachne_hx6_description/config/standing_pose.yaml',
    'src/arachne_hx6_description/urdf/arachne_hx6.urdf.xacro',
    'src/arachne_hx6_description/urdf/hexarotor.xacro',
    'src/arachne_hx6_description/urdf/leg.xacro',
    'src/arachne_hx6_analysis/config/architecture_envelope.yaml',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/model.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/inputs.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/geometry.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/geometry_primitives.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/geometry_kinematics.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/geometry_solver.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/architecture_kinematics.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/architecture_baseline.py',
    'src/arachne_hx6_analysis/arachne_hx6_analysis/architecture_types.py',
)

STANDING_POSE_RELPATH = FROZEN_INPUT_RELPATHS[0]
XACRO_RELPATH = FROZEN_INPUT_RELPATHS[1]
ARCHITECTURE_ENVELOPE_RELPATH = FROZEN_INPUT_RELPATHS[4]

if abs(APPROVED_SOLVER_TOLERANCE_M - GEOMETRY_SOLVER_TOLERANCE_M) > 0.0:
    raise InvalidInputError(
        'approved solver tolerance must remain '
        f'{APPROVED_SOLVER_TOLERANCE_M} m'
    )


class FrozenGeometryModelError(AnalysisError):
    """Approved-pair capsule/disk/AABB/certified distance model failed.

    This is not an InvalidInputError. Callers must fail the whole sample
    set closed as UNDETERMINED_GEOMETRY_MODEL.
    """


def _require_non_empty_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f'{name} must be a non-empty string')
    return value


def _require_finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    number = float(value)
    if not math.isfinite(number):
        raise InvalidInputError(f'{name} must be finite, got {value!r}')
    return number


def _require_bool_false(value: object, name: str) -> bool:
    if not isinstance(value, bool) or value is not False:
        raise InvalidInputError(f'{name} must be false, got {value!r}')
    return False


def _require_joint_values(values: Mapping[str, float], path: str) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise InvalidInputError(f'{path} must be a mapping')
    names = list(values.keys())
    if len(names) != len(set(names)):
        raise InvalidInputError(f'{path} has duplicate joint names')
    required = set(REQUIRED_JOINT_NAMES)
    got = set(names)
    missing = sorted(required - got)
    extra = sorted(got - required)
    if missing:
        raise InvalidInputError(f'{path} missing joints: {missing}')
    if extra:
        raise InvalidInputError(f'{path} unknown joints: {extra}')
    validated: dict[str, float] = {}
    for name in REQUIRED_JOINT_NAMES:
        validated[name] = _require_finite_float(values[name], f'{path}.{name}')
    return validated


def _require_limitation_reasons(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise InvalidInputError(f'{path} must be a sequence of strings')
    reasons: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        reason = _require_non_empty_str(item, f'{path}[{index}]')
        if reason not in ALLOWED_LIMITATION_REASONS:
            raise InvalidInputError(f'{path} unknown limitation reason: {reason}')
        if reason in seen:
            continue
        seen.add(reason)
        reasons.append(reason)
    return tuple(reasons)


def _reject_forbidden_status(value: str, path: str) -> None:
    if value in FORBIDDEN_STATUS_WORDS:
        raise InvalidInputError(f'{path} uses a forbidden status word: {value}')


def _pair_involves_tibia(pair: str) -> bool:
    if pair.count('__') != 1:
        return False
    left, right = pair.split('__')
    return left.endswith('_tibia') or right.endswith('_tibia')


def _geometry_source_is_aabb(tags: Sequence[str]) -> bool:
    return (
        GEOMETRY_KIND_AABB_PROXY in tags
        or 'primitive=aabb_proxy' in tags
    )


def sample_set_status_from_records(
    records: Sequence['SampleRecord'],
    n_records_undetermined: int,
) -> str | None:
    """Recompute an affirmative set status, or None when undetermined."""
    if n_records_undetermined > 0:
        return None
    if not records:
        return None
    if any(
        record.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED
        for record in records
    ):
        return RESULT_SAMPLED_INTERSECTION_DETECTED
    if all(
        record.result_status == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE
        for record in records
    ):
        return SAMPLE_SET_NO_INTERSECTION
    return None


@dataclass(frozen=True)
class FrozenInputSpec:
    relpath: str
    git_blob_sha1: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.relpath, 'frozen_inputs.relpath')
        sha = _require_non_empty_str(self.git_blob_sha1, 'frozen_inputs.git_blob_sha1')
        if len(sha) != 40 or any(ch not in '0123456789abcdef' for ch in sha):
            raise InvalidInputError(
                f'frozen blob SHA must be 40 lowercase hex chars, got {sha!r}'
            )


@dataclass(frozen=True)
class ConfigurationSpaceConfig:
    status: str
    implementation_authorization_status: str
    implementation_scope: str
    procurement_allowed: bool
    hardware_assembly_allowed: bool
    report_file_generation_allowed: bool
    cli_registration_allowed: bool
    gazebo_allowed: bool
    px4_allowed: bool
    sample_count: int
    source_state_or_path: str
    joint_unit: str
    length_unit: str
    solver_tolerance_m: float
    hex_arm_span_m: float
    hex_rotor_radius_m: float
    analysis_disk_proxy_status: str
    g4_d0_contract_sha256: str
    g1_description_commit_sha: str
    g1_description_tree_sha: str
    frozen_inputs: tuple[FrozenInputSpec, ...]
    include_family_ids: tuple[str, ...]
    exclude_family_ids: tuple[str, ...]
    exclusion_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status != STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(
                f'status must be {STATUS_ANALYSIS_ONLY}, got {self.status!r}'
            )
        if self.implementation_authorization_status != IMPLEMENTATION_AUTHORIZATION_STATUS:
            raise InvalidInputError(
                'implementation_authorization_status must be '
                f'{IMPLEMENTATION_AUTHORIZATION_STATUS}, got '
                f'{self.implementation_authorization_status!r}'
            )
        if self.implementation_scope != IMPLEMENTATION_SCOPE:
            raise InvalidInputError(
                f'implementation_scope must be {IMPLEMENTATION_SCOPE}, got '
                f'{self.implementation_scope!r}'
            )
        _require_bool_false(self.procurement_allowed, 'procurement_allowed')
        _require_bool_false(
            self.hardware_assembly_allowed, 'hardware_assembly_allowed'
        )
        _require_bool_false(
            self.report_file_generation_allowed, 'report_file_generation_allowed'
        )
        _require_bool_false(
            self.cli_registration_allowed, 'cli_registration_allowed'
        )
        _require_bool_false(self.gazebo_allowed, 'gazebo_allowed')
        _require_bool_false(self.px4_allowed, 'px4_allowed')
        if (
            not isinstance(self.sample_count, int)
            or isinstance(self.sample_count, bool)
            or self.sample_count != SAMPLE_COUNT_REQUIRED
        ):
            raise InvalidInputError(
                f'sample_count must be {SAMPLE_COUNT_REQUIRED}, got '
                f'{self.sample_count!r}'
            )
        if self.source_state_or_path != SOURCE_STATE_OR_PATH:
            raise InvalidInputError(
                f'source_state_or_path must be {SOURCE_STATE_OR_PATH}, got '
                f'{self.source_state_or_path!r}'
            )
        if self.joint_unit != JOINT_UNIT:
            raise InvalidInputError(
                f'joint_unit must be {JOINT_UNIT}, got {self.joint_unit!r}'
            )
        if self.length_unit != LENGTH_UNIT:
            raise InvalidInputError(
                f'length_unit must be {LENGTH_UNIT}, got {self.length_unit!r}'
            )
        if self.solver_tolerance_m != APPROVED_SOLVER_TOLERANCE_M:
            raise InvalidInputError(
                'solver tolerance must be the approved 1e-9 m, got '
                f'{self.solver_tolerance_m}'
            )
        if abs(self.hex_arm_span_m - HEX_ARM_SPAN_M) > 1.0e-12:
            raise InvalidInputError(
                f'hex_arm_span_m must be {HEX_ARM_SPAN_M}, got {self.hex_arm_span_m}'
            )
        if abs(self.hex_rotor_radius_m - HEX_ROTOR_RADIUS_M) > 1.0e-12:
            raise InvalidInputError(
                'hex_rotor_radius_m must be '
                f'{HEX_ROTOR_RADIUS_M}, got {self.hex_rotor_radius_m}'
            )
        if self.analysis_disk_proxy_status != PROXY_STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(
                'analysis disk proxy_status must be '
                f'{PROXY_STATUS_ANALYSIS_ONLY}, got '
                f'{self.analysis_disk_proxy_status!r}'
            )
        if self.g4_d0_contract_sha256 != G4_D0_CONTRACT_SHA256:
            raise InvalidInputError('g4_d0_contract_sha256 does not match the approved value')
        if self.g1_description_commit_sha != G1_DESCRIPTION_COMMIT_SHA:
            raise InvalidInputError('g1_description_commit_sha does not match the approved value')
        if self.g1_description_tree_sha != G1_DESCRIPTION_TREE_SHA:
            raise InvalidInputError('g1_description_tree_sha does not match the approved value')
        if tuple(spec.relpath for spec in self.frozen_inputs) != FROZEN_INPUT_RELPATHS:
            raise InvalidInputError(
                'frozen_inputs paths must match the approved runtime dependency list'
            )


@dataclass(frozen=True)
class SampleRecord:
    sample_id: str
    source_state_or_path: str
    evaluated_pair: str
    joint_values: Mapping[str, float]
    geometry_source: tuple[str, ...]
    proxy_status: str
    hardware_validation_status: str
    nominal_separation_or_intersection: float | None
    result_status: str
    limitation_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        sample_id = _require_non_empty_str(self.sample_id, 'sample_id')
        if sample_id != sample_id.strip() or not sample_id.strip():
            raise InvalidInputError('sample_id must be non-blank')
        if self.source_state_or_path != SOURCE_STATE_OR_PATH:
            raise InvalidInputError(
                'source_state_or_path must be '
                f'{SOURCE_STATE_OR_PATH}, got {self.source_state_or_path!r}'
            )
        _require_non_empty_str(self.evaluated_pair, 'evaluated_pair')
        object.__setattr__(
            self, 'joint_values', _require_joint_values(self.joint_values, 'joint_values')
        )
        if not self.geometry_source:
            raise InvalidInputError('geometry_source must be non-empty')
        for index, item in enumerate(self.geometry_source):
            _require_non_empty_str(item, f'geometry_source[{index}]')
        if self.proxy_status != PROXY_STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(
                f'proxy_status must be {PROXY_STATUS_ANALYSIS_ONLY}'
            )
        if self.hardware_validation_status != HARDWARE_VALIDATION_NOT_VALIDATED:
            raise InvalidInputError(
                'hardware_validation_status must be '
                f'{HARDWARE_VALIDATION_NOT_VALIDATED}'
            )
        if self.result_status not in ALLOWED_RESULT_STATUSES:
            _reject_forbidden_status(str(self.result_status), 'result_status')
            raise InvalidInputError(
                f'result_status must be one of {ALLOWED_RESULT_STATUSES}, got '
                f'{self.result_status!r}'
            )
        gap = self.nominal_separation_or_intersection
        if gap is None:
            raise InvalidInputError(
                'nominal_separation_or_intersection must be a finite length, '
                'not null, for an affirmative sample record'
            )
        finite_gap = _require_finite_float(
            gap, 'nominal_separation_or_intersection'
        )
        if abs(finite_gap) <= APPROVED_SOLVER_TOLERANCE_M:
            raise InvalidInputError(
                'affirmative SampleRecord cannot be built when '
                '|gap| <= solver tolerance'
            )
        if self.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED:
            if not (finite_gap < -APPROVED_SOLVER_TOLERANCE_M):
                raise InvalidInputError(
                    'SAMPLED_INTERSECTION_DETECTED requires gap < -tolerance'
                )
        elif self.result_status == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE:
            if not (finite_gap > APPROVED_SOLVER_TOLERANCE_M):
                raise InvalidInputError(
                    'NO_INTERSECTION_AT_EVALUATED_SAMPLE requires gap > tolerance'
                )
        reasons = _require_limitation_reasons(
            self.limitation_reasons, 'limitation_reasons'
        )
        is_aabb = _geometry_source_is_aabb(self.geometry_source)
        is_tibia = _pair_involves_tibia(self.evaluated_pair)
        if (
            self.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED
            and is_aabb
            and LIMITATION_AABB_FALSE_POSITIVE not in reasons
        ):
            raise InvalidInputError(
                'AABB intersection must include '
                'CONSERVATIVE_AABB_PROXY_POSSIBLE_FALSE_POSITIVE'
            )
        if LIMITATION_AABB_FALSE_POSITIVE in reasons and not (
            self.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED
            and is_aabb
        ):
            raise InvalidInputError(
                'AABB false-positive limitation is only valid for AABB '
                'intersection records'
            )
        if is_tibia and LIMITATION_TIBIA_FOOT_ENDPOINT not in reasons:
            raise InvalidInputError(
                'tibia endpoint usage must include '
                'TIBIA_CAPSULE_USES_G2_FOOT_SPHERE_ENDPOINT'
            )
        if LIMITATION_TIBIA_FOOT_ENDPOINT in reasons and not is_tibia:
            raise InvalidInputError(
                'tibia endpoint limitation requires a tibia pair'
            )
        object.__setattr__(self, 'limitation_reasons', reasons)


@dataclass(frozen=True)
class SampleSetSummary:
    sample_set_status: str
    configuration_space_status: str
    included_pair_ids: tuple[str, ...]
    excluded_pair_ids: tuple[str, ...]
    exclusion_reasons: Mapping[str, str]
    n_pair_instances_included: int
    n_pair_instances_excluded: int
    evaluated_scope: str
    n_samples_requested: int
    n_samples_valid: int
    n_records_expected: int
    n_records_valid: int
    n_records_undetermined: int
    limitation_reasons: tuple[str, ...]
    transition_proof_flag: str
    implementation_scope: str
    status: str
    procurement_allowed: bool
    hardware_assembly_allowed: bool
    report_file_generation_allowed: bool
    cli_registration_allowed: bool
    gazebo_allowed: bool
    px4_allowed: bool
    g1_description_commit_sha: str
    g1_description_tree_sha: str
    g4_d0_contract_sha256: str
    frozen_input_blob_sha1: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.configuration_space_status != CONFIGURATION_SPACE_UNSAMPLED:
            _reject_forbidden_status(
                str(self.configuration_space_status), 'configuration_space_status'
            )
            raise InvalidInputError(
                'configuration_space_status must remain '
                f'{CONFIGURATION_SPACE_UNSAMPLED}'
            )
        if self.sample_set_status not in ALLOWED_SAMPLE_SET_STATUSES:
            _reject_forbidden_status(str(self.sample_set_status), 'sample_set_status')
            raise InvalidInputError(
                f'sample_set_status must be one of {ALLOWED_SAMPLE_SET_STATUSES}, '
                f'got {self.sample_set_status!r}'
            )
        if self.n_pair_instances_included != N_PAIR_INSTANCES_INCLUDED:
            raise InvalidInputError(
                'n_pair_instances_included must be '
                f'{N_PAIR_INSTANCES_INCLUDED}'
            )
        if self.n_pair_instances_excluded != N_PAIR_INSTANCES_EXCLUDED:
            raise InvalidInputError(
                'n_pair_instances_excluded must be '
                f'{N_PAIR_INSTANCES_EXCLUDED}'
            )
        if len(self.included_pair_ids) != N_PAIR_INSTANCES_INCLUDED:
            raise InvalidInputError('included_pair_ids must contain 162 ids')
        if len(self.excluded_pair_ids) != N_PAIR_INSTANCES_EXCLUDED:
            raise InvalidInputError('excluded_pair_ids must contain 420 ids')
        if len(set(self.included_pair_ids)) != len(self.included_pair_ids):
            raise InvalidInputError('included_pair_ids contains duplicates')
        if len(set(self.excluded_pair_ids)) != len(self.excluded_pair_ids):
            raise InvalidInputError('excluded_pair_ids contains duplicates')
        overlap = set(self.included_pair_ids) & set(self.excluded_pair_ids)
        if overlap:
            raise InvalidInputError(f'include/exclude overlap: {sorted(overlap)[:3]}')
        if set(self.exclusion_reasons) != set(self.excluded_pair_ids):
            raise InvalidInputError('exclusion_reasons must cover excluded_pair_ids')
        for pair_id, reason in self.exclusion_reasons.items():
            if reason not in ALLOWED_EXCLUSION_REASON_CODES:
                raise InvalidInputError(f'unknown exclusion reason: {reason}')
        if self.evaluated_scope != EVALUATED_SCOPE:
            raise InvalidInputError(
                f'evaluated_scope must be {EVALUATED_SCOPE}'
            )
        if (
            not isinstance(self.n_samples_requested, int)
            or isinstance(self.n_samples_requested, bool)
            or self.n_samples_requested < 0
        ):
            raise InvalidInputError('n_samples_requested must be an integer >= 0')
        if (
            not isinstance(self.n_samples_valid, int)
            or isinstance(self.n_samples_valid, bool)
            or not (0 <= self.n_samples_valid <= self.n_samples_requested)
        ):
            raise InvalidInputError(
                'n_samples_valid must satisfy '
                '0 <= n_samples_valid <= n_samples_requested'
            )
        if self.n_records_expected != (
            self.n_samples_requested * self.n_pair_instances_included
        ):
            raise InvalidInputError(
                'n_records_expected must equal n_samples_requested * 162'
            )
        if self.n_records_valid < 0 or self.n_records_undetermined < 0:
            raise InvalidInputError('record counts must be >= 0')
        if self.n_records_valid + self.n_records_undetermined != self.n_records_expected:
            raise InvalidInputError(
                'n_records_valid + n_records_undetermined must equal '
                'n_records_expected'
            )
        if (
            self.n_records_undetermined > 0
            and self.sample_set_status in AFFIRMATIVE_SAMPLE_SET_STATUSES
        ):
            raise InvalidInputError(
                'affirmative sample_set_status is forbidden when any record '
                'is undetermined'
            )
        if self.sample_set_status == SAMPLE_SET_NO_INTERSECTION:
            if self.n_samples_valid < 1 or self.n_records_valid < 1:
                raise InvalidInputError(
                    'NO_INTERSECTION_IN_EVALUATED_SAMPLES requires a non-empty '
                    'valid included sample set'
                )
        object.__setattr__(
            self,
            'limitation_reasons',
            _require_limitation_reasons(
                self.limitation_reasons, 'limitation_reasons'
            ),
        )
        if self.transition_proof_flag != LIMITATION_SAMPLED_TRANSITION_ONLY:
            raise InvalidInputError(
                'transition_proof_flag must be '
                f'{LIMITATION_SAMPLED_TRANSITION_ONLY}'
            )
        if self.implementation_scope != IMPLEMENTATION_SCOPE:
            raise InvalidInputError(
                f'implementation_scope must be {IMPLEMENTATION_SCOPE}'
            )
        if self.status != STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(f'status must be {STATUS_ANALYSIS_ONLY}')
        _require_bool_false(self.procurement_allowed, 'procurement_allowed')
        _require_bool_false(
            self.hardware_assembly_allowed, 'hardware_assembly_allowed'
        )
        _require_bool_false(
            self.report_file_generation_allowed, 'report_file_generation_allowed'
        )
        _require_bool_false(
            self.cli_registration_allowed, 'cli_registration_allowed'
        )
        _require_bool_false(self.gazebo_allowed, 'gazebo_allowed')
        _require_bool_false(self.px4_allowed, 'px4_allowed')
        if self.g1_description_commit_sha != G1_DESCRIPTION_COMMIT_SHA:
            raise InvalidInputError('summary g1 commit SHA mismatch')
        if self.g1_description_tree_sha != G1_DESCRIPTION_TREE_SHA:
            raise InvalidInputError('summary g1 tree SHA mismatch')
        if self.g4_d0_contract_sha256 != G4_D0_CONTRACT_SHA256:
            raise InvalidInputError('summary G4-D0 contract SHA mismatch')
        if set(self.frozen_input_blob_sha1) != set(FROZEN_INPUT_RELPATHS):
            raise InvalidInputError('summary frozen SHA map must cover all frozen inputs')


@dataclass(frozen=True)
class ConfigurationSpaceResult:
    records: tuple[SampleRecord, ...]
    summary: SampleSetSummary

    def __post_init__(self) -> None:
        ids = [record.sample_id for record in self.records]
        if any(not item.strip() for item in ids):
            raise InvalidInputError('blank sample_id')
        if len(ids) != len(set(ids)):
            raise InvalidInputError('duplicate sample_id')
        if len(self.records) != self.summary.n_records_valid:
            raise InvalidInputError(
                'records length must equal n_records_valid'
            )
        for record in self.records:
            if record.evaluated_pair not in self.summary.included_pair_ids:
                raise InvalidInputError(
                    'SampleRecord pair is outside included scope: '
                    f'{record.evaluated_pair}'
                )
            if record.evaluated_pair in self.summary.excluded_pair_ids:
                raise InvalidInputError(
                    'SampleRecord pair is excluded: '
                    f'{record.evaluated_pair}'
                )
        recomputed = sample_set_status_from_records(
            self.records, self.summary.n_records_undetermined
        )
        if recomputed is None:
            if self.summary.sample_set_status in AFFIRMATIVE_SAMPLE_SET_STATUSES:
                raise InvalidInputError(
                    'affirmative sample_set_status is forbidden when the '
                    'record set is incomplete or undetermined'
                )
        elif self.summary.sample_set_status != recomputed:
            raise InvalidInputError(
                'sample_set_status must be recomputed from records: '
                f'got {self.summary.sample_set_status!r}, expected {recomputed!r}'
            )


def require_unique_sample_ids(records: Sequence[SampleRecord]) -> None:
    ids = [record.sample_id for record in records]
    if any(not item.strip() for item in ids):
        raise InvalidInputError('blank sample_id')
    if len(ids) != len(set(ids)):
        raise InvalidInputError('duplicate sample_id')
