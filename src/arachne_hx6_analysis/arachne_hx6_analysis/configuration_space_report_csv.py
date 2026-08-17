"""CSV serialization of the G4-D1B configuration-space report triplet.

UTF-8, LF, standard csv quoting, frozen union schema.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import csv
from io import StringIO
import json
from typing import Any, Mapping

from arachne_hx6_analysis.configuration_space_report_payload import (
    CSV_COLUMNS,
    METADATA_KEYS,
    RECORD_CSV_COLUMNS,
    compact_json,
    json_roundtrip,
)
from arachne_hx6_analysis.model import InvalidInputError

CSV_RECORD_EMPTY = {column: '' for column in RECORD_CSV_COLUMNS}


def render_configuration_space_csv(
    metadata: Mapping[str, Any],
    records: list[dict[str, Any]],
) -> str:
    if tuple(metadata) != METADATA_KEYS:
        raise InvalidInputError('CSV metadata key order is not the frozen contract')
    buf = StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=list(CSV_COLUMNS),
        lineterminator='\n',
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writeheader()
    for key in METADATA_KEYS:
        row = {
            'row_type': 'metadata',
            'metadata_key': key,
            'metadata_value_json': compact_json(metadata[key]),
        }
        row.update(CSV_RECORD_EMPTY)
        writer.writerow(row)
    for record in records:
        gap = record['nominal_separation_or_intersection']
        writer.writerow(
            {
                'row_type': 'record',
                'metadata_key': '',
                'metadata_value_json': '',
                'sample_id': record['sample_id'],
                'source_state_or_path': record['source_state_or_path'],
                'evaluated_pair': record['evaluated_pair'],
                'joint_values_json': compact_json(record['joint_values']),
                'geometry_source_json': compact_json(record['geometry_source']),
                'proxy_status': record['proxy_status'],
                'hardware_validation_status': record['hardware_validation_status'],
                'nominal_separation_or_intersection_m': (
                    '' if gap is None else compact_json(gap)
                ),
                'result_status': record['result_status'],
                'limitation_reasons_json': compact_json(
                    record['limitation_reasons']
                ),
            }
        )
    return buf.getvalue()


def parse_configuration_space_csv(
    text: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != CSV_COLUMNS:
        raise InvalidInputError('CSV header is not the frozen union schema')
    metadata: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    seen_record = False
    for row in reader:
        extra = [key for key in row if key not in CSV_COLUMNS]
        if extra:
            raise InvalidInputError(f'CSV has extra columns: {extra}')
        row_type = row.get('row_type', '')
        if row_type == 'metadata':
            if seen_record:
                raise InvalidInputError('CSV metadata rows must precede record rows')
            key = row.get('metadata_key') or ''
            if not key:
                raise InvalidInputError('metadata_key must be non-empty')
            if key in metadata:
                raise InvalidInputError(f'duplicate metadata_key: {key}')
            for column in RECORD_CSV_COLUMNS:
                if row.get(column, '') != '':
                    raise InvalidInputError(
                        f'metadata row {key} must leave record columns empty'
                    )
            try:
                metadata[key] = json.loads(row['metadata_value_json'])
            except json.JSONDecodeError as exc:
                raise InvalidInputError(
                    f'metadata_value_json is not JSON for {key}'
                ) from exc
            metadata[key] = json_roundtrip(metadata[key])
        elif row_type == 'record':
            seen_record = True
            if row.get('metadata_key', '') != '' or row.get(
                'metadata_value_json', ''
            ) != '':
                raise InvalidInputError('record rows must leave metadata columns empty')
            records.append(_record_from_csv_row(row))
        else:
            raise InvalidInputError(f'unknown CSV row_type: {row_type!r}')
    if tuple(metadata) != METADATA_KEYS:
        raise InvalidInputError('CSV metadata keys or order do not match the contract')
    return metadata, records


def _record_from_csv_row(row: Mapping[str, str]) -> dict[str, Any]:
    gap_text = row.get('nominal_separation_or_intersection_m', '')
    if gap_text == '':
        gap: float | None = None
    else:
        try:
            parsed_gap = json.loads(gap_text)
        except json.JSONDecodeError as exc:
            raise InvalidInputError(
                'nominal_separation_or_intersection_m is not JSON'
            ) from exc
        if parsed_gap is None:
            gap = None
        elif isinstance(parsed_gap, bool) or not isinstance(parsed_gap, (int, float)):
            raise InvalidInputError(
                'nominal_separation_or_intersection_m must be a number or empty'
            )
        else:
            gap = json_roundtrip(parsed_gap)
            if gap == 0 and parsed_gap != 0:
                raise InvalidInputError('CSV must not convert a missing gap to 0')
    try:
        joint_values = json.loads(row['joint_values_json'])
        geometry_source = json.loads(row['geometry_source_json'])
        limitation_reasons = json.loads(row['limitation_reasons_json'])
    except json.JSONDecodeError as exc:
        raise InvalidInputError('CSV complex field is not JSON') from exc
    return {
        'sample_id': row['sample_id'],
        'source_state_or_path': row['source_state_or_path'],
        'evaluated_pair': row['evaluated_pair'],
        'joint_values': json_roundtrip(joint_values),
        'geometry_source': json_roundtrip(geometry_source),
        'proxy_status': row['proxy_status'],
        'hardware_validation_status': row['hardware_validation_status'],
        'nominal_separation_or_intersection': gap,
        'result_status': row['result_status'],
        'limitation_reasons': json_roundtrip(limitation_reasons),
    }
