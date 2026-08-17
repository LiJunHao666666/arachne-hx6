"""G4-D1B JSON payload and shared report-triplet schema.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
implementation_scope: G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from arachne_hx6_analysis.architecture_report import assert_strict_finite_json
from arachne_hx6_analysis.architecture_types import (
    REQUIRED_JOINT_NAMES,
    STOW_POSE_EVIDENCE_UNQUALIFIED,
)
from arachne_hx6_analysis.configuration_space_registry import uses_aabb_proxy
from arachne_hx6_analysis.configuration_space_types import (
    CONFIGURATION_SPACE_UNSAMPLED,
    ConfigurationSpaceResult,
    FROZEN_INPUT_RELPATHS,
    GEOMETRY_KIND_AABB_PROXY,
    GEOMETRY_KIND_DISK_CAPSULE,
    IMPLEMENTATION_SCOPE as D1A_IMPLEMENTATION_SCOPE,
    JOINT_UNIT,
    LENGTH_UNIT,
    LIMITATION_AABB_FALSE_POSITIVE,
    RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE,
    RESULT_SAMPLED_INTERSECTION_DETECTED,
    SampleRecord,
)
from arachne_hx6_analysis.model import (
    InvalidInputError,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
)

IMPLEMENTATION_AUTHORIZATION_STATUS = 'GPT_AUTHORIZED'
IMPLEMENTATION_SCOPE = 'G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY'
SOURCE_EVALUATOR_SCOPE = D1A_IMPLEMENTATION_SCOPE

JSON_NAME = 'configuration_space_report.json'
CSV_NAME = 'configuration_space_report.csv'
MARKDOWN_NAME = 'configuration_space_report.md'
REPORT_NAMES = (JSON_NAME, CSV_NAME, MARKDOWN_NAME)

MD_NULL = '—'

METADATA_KEYS = (
    'status',
    'not_for_procurement',
    'stow_pose_evidence_status',
    'transition_proof_flag',
    'sample_set_status',
    'configuration_space_status',
    'implementation_authorization_status',
    'implementation_scope',
    'report_triplet_generation_allowed',
    'source_evaluator_scope',
    'source_evaluator_report_file_generation_allowed',
    'cli_registration_allowed',
    'procurement_allowed',
    'hardware_assembly_allowed',
    'gazebo_allowed',
    'px4_allowed',
    'evaluated_scope',
    'n_samples_requested',
    'n_samples_valid',
    'n_records_expected',
    'n_records_valid',
    'n_records_undetermined',
    'n_records',
    'n_result_sampled_intersection_detected',
    'n_result_no_intersection_at_evaluated_sample',
    'n_aabb_proxy_records',
    'n_disk_capsule_records',
    'n_aabb_proxy_intersections',
    'n_aabb_false_positive_limitations',
    'included_pair_ids',
    'excluded_pair_ids',
    'exclusion_reasons',
    'limitation_reasons',
    'joint_unit',
    'length_unit',
    'g1_description_commit_sha',
    'g1_description_tree_sha',
    'g4_d0_contract_sha256',
    'frozen_input_blob_sha1',
    'generated_at_utc',
)

RECORD_KEYS = (
    'sample_id',
    'source_state_or_path',
    'evaluated_pair',
    'joint_values',
    'geometry_source',
    'proxy_status',
    'hardware_validation_status',
    'nominal_separation_or_intersection',
    'result_status',
    'limitation_reasons',
)

PLAIN_RECORD_STRING_KEYS = (
    'sample_id',
    'source_state_or_path',
    'evaluated_pair',
    'proxy_status',
    'hardware_validation_status',
    'result_status',
)

CSV_COLUMNS = (
    'row_type',
    'metadata_key',
    'metadata_value_json',
    'sample_id',
    'source_state_or_path',
    'evaluated_pair',
    'joint_values_json',
    'geometry_source_json',
    'proxy_status',
    'hardware_validation_status',
    'nominal_separation_or_intersection_m',
    'result_status',
    'limitation_reasons_json',
)

RECORD_CSV_COLUMNS = (
    'sample_id',
    'source_state_or_path',
    'evaluated_pair',
    'joint_values_json',
    'geometry_source_json',
    'proxy_status',
    'hardware_validation_status',
    'nominal_separation_or_intersection_m',
    'result_status',
    'limitation_reasons_json',
)

FORBIDDEN_REPORT_STATUS_WORDS = (
    'VIABLE',
    'FLYABLE',
    'SAFE_TO_FLY',
    'PROCUREMENT_READY',
    'RECOMMENDED_FOR_PURCHASE',
    'VALIDATED_HARDWARE',
    'STOWED_PASS',
    'VALID_STOWED_POSE',
)

FORBIDDEN_REPORT_PHRASES = (
    'collision-free system',
    'safe configuration space',
)


@dataclass(frozen=True)
class ReportAuthorization:
    status: str
    implementation_authorization_status: str
    implementation_scope: str
    report_triplet_generation_allowed: bool
    cli_registration_allowed: bool
    procurement_allowed: bool
    hardware_assembly_allowed: bool
    gazebo_allowed: bool
    px4_allowed: bool
    source_evaluator_scope: str
    source_evaluator_report_file_generation_allowed: bool
    json_name: str
    csv_name: str
    markdown_name: str


def compact_json(value: Any) -> str:
    """Deterministic compact JSON. Rejects NaN/Infinity."""
    assert_strict_finite_json(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(',', ':'),
            sort_keys=False,
        )
    except ValueError as exc:
        raise InvalidInputError(f'compact JSON is not finite: {exc}') from exc


def official_json_text(payload: Mapping[str, Any]) -> str:
    """Pretty JSON with a single trailing LF."""
    assert_strict_finite_json(payload)
    try:
        return json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            sort_keys=False,
        ) + '\n'
    except ValueError as exc:
        raise InvalidInputError(f'JSON is not finite: {exc}') from exc


def json_roundtrip(value: Any) -> Any:
    return json.loads(compact_json(value))


def geometry_source_is_aabb(tags: tuple[str, ...]) -> bool:
    return GEOMETRY_KIND_AABB_PROXY in tags or 'primitive=aabb_proxy' in tags


def geometry_source_is_disk(tags: tuple[str, ...]) -> bool:
    return (
        GEOMETRY_KIND_DISK_CAPSULE in tags
        or 'primitive=signed_distance_disk_capsule' in tags
    )


def require_exclusive_geometry_family(record: SampleRecord) -> bool:
    """Return True for AABB, False for disk-capsule. Exactly one family."""
    tags = record.geometry_source
    is_aabb = geometry_source_is_aabb(tags)
    is_disk_capsule = geometry_source_is_disk(tags)
    if is_aabb and is_disk_capsule:
        raise InvalidInputError(
            'geometry_source must not contain both AABB and disk-capsule tags'
        )
    if not is_aabb and not is_disk_capsule:
        raise InvalidInputError(
            'geometry_source must be exactly one approved geometry family'
        )
    pair_uses_aabb = uses_aabb_proxy(record.evaluated_pair)
    if pair_uses_aabb and not is_aabb:
        raise InvalidInputError(
            'AABB registry pair must use AABB geometry_source only'
        )
    if not pair_uses_aabb and not is_disk_capsule:
        raise InvalidInputError(
            'included disk-capsule pair must use disk-capsule geometry_source only'
        )
    return is_aabb


def require_plain_string(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError(f'{name} must be a string')
    if value == MD_NULL:
        raise InvalidInputError(
            f'{name} must not be the missing-value marker {MD_NULL!r}'
        )
    return value


def joint_values_object(record: SampleRecord) -> dict[str, float]:
    values = record.joint_values
    missing = [name for name in REQUIRED_JOINT_NAMES if name not in values]
    extra = [name for name in values if name not in REQUIRED_JOINT_NAMES]
    if missing or extra:
        raise InvalidInputError('joint_values must contain exactly 18 official joints')
    return {name: float(values[name]) for name in REQUIRED_JOINT_NAMES}


def record_to_dict(record: SampleRecord) -> dict[str, Any]:
    payload = {
        'sample_id': require_plain_string(record.sample_id, 'sample_id'),
        'source_state_or_path': require_plain_string(
            record.source_state_or_path, 'source_state_or_path'
        ),
        'evaluated_pair': require_plain_string(
            record.evaluated_pair, 'evaluated_pair'
        ),
        'joint_values': joint_values_object(record),
        'geometry_source': list(record.geometry_source),
        'proxy_status': require_plain_string(record.proxy_status, 'proxy_status'),
        'hardware_validation_status': require_plain_string(
            record.hardware_validation_status, 'hardware_validation_status'
        ),
        'nominal_separation_or_intersection': (
            record.nominal_separation_or_intersection
        ),
        'result_status': require_plain_string(
            record.result_status, 'result_status'
        ),
        'limitation_reasons': list(record.limitation_reasons),
    }
    if tuple(payload) != RECORD_KEYS:
        raise InvalidInputError('record key order is not the frozen contract')
    return payload


def dynamic_counts(records: tuple[SampleRecord, ...]) -> dict[str, int]:
    n_inter = 0
    n_clear = 0
    n_aabb = 0
    n_disk = 0
    n_aabb_inter = 0
    n_fp = 0
    for record in records:
        aabb = require_exclusive_geometry_family(record)
        if aabb:
            n_aabb += 1
        else:
            n_disk += 1
        if record.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED:
            n_inter += 1
            if aabb:
                n_aabb_inter += 1
        elif record.result_status == RESULT_NO_INTERSECTION_AT_EVALUATED_SAMPLE:
            n_clear += 1
        has_fp = LIMITATION_AABB_FALSE_POSITIVE in record.limitation_reasons
        if has_fp:
            n_fp += 1
        if aabb and record.result_status == RESULT_SAMPLED_INTERSECTION_DETECTED:
            if not has_fp:
                raise InvalidInputError(
                    'AABB intersection must include '
                    'CONSERVATIVE_AABB_PROXY_POSSIBLE_FALSE_POSITIVE'
                )
        elif has_fp:
            raise InvalidInputError(
                'AABB false-positive limitation is only valid for AABB '
                'intersection records'
            )
    if n_aabb_inter != n_fp:
        raise InvalidInputError(
            'AABB intersection count must equal false-positive limitation count'
        )
    return {
        'n_records': len(records),
        'n_result_sampled_intersection_detected': n_inter,
        'n_result_no_intersection_at_evaluated_sample': n_clear,
        'n_aabb_proxy_records': n_aabb,
        'n_disk_capsule_records': n_disk,
        'n_aabb_proxy_intersections': n_aabb_inter,
        'n_aabb_false_positive_limitations': n_fp,
    }


def ordered_exclusion_reasons(
    result: ConfigurationSpaceResult,
) -> dict[str, str]:
    reasons = dict(result.summary.exclusion_reasons)
    return {
        pair_id: reasons[pair_id]
        for pair_id in result.summary.excluded_pair_ids
    }


def ordered_frozen_blobs(result: ConfigurationSpaceResult) -> dict[str, str]:
    blobs = dict(result.summary.frozen_input_blob_sha1)
    return {path: blobs[path] for path in FROZEN_INPUT_RELPATHS}


def build_metadata(
    result: ConfigurationSpaceResult,
    generated_at_utc: str,
    auth: ReportAuthorization,
) -> dict[str, Any]:
    summary = result.summary
    if summary.status != STATUS_ANALYSIS_ONLY:
        raise InvalidInputError('result status must remain ANALYSIS_ONLY')
    if summary.implementation_scope != SOURCE_EVALUATOR_SCOPE:
        raise InvalidInputError(
            'source evaluator scope must remain '
            f'{SOURCE_EVALUATOR_SCOPE}'
        )
    if summary.report_file_generation_allowed is not False:
        raise InvalidInputError(
            'source_evaluator_report_file_generation_allowed must remain false'
        )
    if summary.cli_registration_allowed is not False:
        raise InvalidInputError('cli_registration_allowed must remain false')
    if summary.procurement_allowed is not False:
        raise InvalidInputError('procurement_allowed must remain false')
    if summary.hardware_assembly_allowed is not False:
        raise InvalidInputError('hardware_assembly_allowed must remain false')
    if summary.gazebo_allowed is not False:
        raise InvalidInputError('gazebo_allowed must remain false')
    if summary.px4_allowed is not False:
        raise InvalidInputError('px4_allowed must remain false')
    if summary.configuration_space_status != CONFIGURATION_SPACE_UNSAMPLED:
        raise InvalidInputError(
            'configuration_space_status must remain '
            f'{CONFIGURATION_SPACE_UNSAMPLED}'
        )
    if len(result.records) != summary.n_records_valid:
        raise InvalidInputError('records length must equal n_records_valid')
    counts = dynamic_counts(result.records)
    if counts['n_records'] != summary.n_records_valid:
        raise InvalidInputError('dynamic n_records must equal n_records_valid')
    metadata = {
        'status': STATUS_ANALYSIS_ONLY,
        'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
        'stow_pose_evidence_status': STOW_POSE_EVIDENCE_UNQUALIFIED,
        'transition_proof_flag': summary.transition_proof_flag,
        'sample_set_status': summary.sample_set_status,
        'configuration_space_status': CONFIGURATION_SPACE_UNSAMPLED,
        'implementation_authorization_status': (
            auth.implementation_authorization_status
        ),
        'implementation_scope': auth.implementation_scope,
        'report_triplet_generation_allowed': True,
        'source_evaluator_scope': SOURCE_EVALUATOR_SCOPE,
        'source_evaluator_report_file_generation_allowed': False,
        'cli_registration_allowed': False,
        'procurement_allowed': False,
        'hardware_assembly_allowed': False,
        'gazebo_allowed': False,
        'px4_allowed': False,
        'evaluated_scope': summary.evaluated_scope,
        'n_samples_requested': summary.n_samples_requested,
        'n_samples_valid': summary.n_samples_valid,
        'n_records_expected': summary.n_records_expected,
        'n_records_valid': summary.n_records_valid,
        'n_records_undetermined': summary.n_records_undetermined,
        'n_records': counts['n_records'],
        'n_result_sampled_intersection_detected': (
            counts['n_result_sampled_intersection_detected']
        ),
        'n_result_no_intersection_at_evaluated_sample': (
            counts['n_result_no_intersection_at_evaluated_sample']
        ),
        'n_aabb_proxy_records': counts['n_aabb_proxy_records'],
        'n_disk_capsule_records': counts['n_disk_capsule_records'],
        'n_aabb_proxy_intersections': counts['n_aabb_proxy_intersections'],
        'n_aabb_false_positive_limitations': (
            counts['n_aabb_false_positive_limitations']
        ),
        'included_pair_ids': list(summary.included_pair_ids),
        'excluded_pair_ids': list(summary.excluded_pair_ids),
        'exclusion_reasons': ordered_exclusion_reasons(result),
        'limitation_reasons': list(summary.limitation_reasons),
        'joint_unit': JOINT_UNIT,
        'length_unit': LENGTH_UNIT,
        'g1_description_commit_sha': summary.g1_description_commit_sha,
        'g1_description_tree_sha': summary.g1_description_tree_sha,
        'g4_d0_contract_sha256': summary.g4_d0_contract_sha256,
        'frozen_input_blob_sha1': ordered_frozen_blobs(result),
        'generated_at_utc': generated_at_utc,
    }
    if tuple(metadata) != METADATA_KEYS:
        raise InvalidInputError('metadata key order is not the frozen contract')
    return metadata


def build_configuration_space_json(
    result: ConfigurationSpaceResult,
    generated_at_utc: str,
    auth: ReportAuthorization,
) -> dict[str, Any]:
    payload = {
        'metadata': build_metadata(result, generated_at_utc, auth),
        'records': [record_to_dict(record) for record in result.records],
    }
    if tuple(payload) != ('metadata', 'records'):
        raise InvalidInputError('JSON top-level keys must be metadata, records')
    return payload
