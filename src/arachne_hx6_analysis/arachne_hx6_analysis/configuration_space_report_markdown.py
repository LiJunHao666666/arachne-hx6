"""Markdown serialization of the G4-D1B configuration-space report triplet.

Full records table. Controlled parse/unescape. Missing values are —.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from arachne_hx6_analysis.configuration_space_report_payload import (
    MD_NULL,
    METADATA_KEYS,
    RECORD_KEYS,
    compact_json,
    json_roundtrip,
    require_plain_string,
)
from arachne_hx6_analysis.model import InvalidInputError

BANNER_LINES = (
    '**ANALYSIS_ONLY**',
    '**NOT_FOR_PROCUREMENT**',
    '**UNQUALIFIED_ANALYSIS_POSE**',
    '**SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF**',
    '**ANALYSIS_PROXY_ONLY**',
    '**NOT_HARDWARE_VALIDATED**',
)

LIMITATION_LINES = (
    '- AABB proxy intersection is a conservative analysis-proxy intersection '
    'and a possible false positive. It is not a real mesh collision, URDF '
    'collision, hardware collision, or safety proof.',
    '- `NO_INTERSECTION_AT_EVALUATED_SAMPLE` applies only to that evaluated '
    'discrete sample.',
    '- `NO_INTERSECTION_IN_EVALUATED_SAMPLES` applies only to the evaluated '
    'discrete sample set. It is not a complete configuration-space proof, '
    'hardware validation, qualified stow, flyable result, or procurement '
    'result.',
    '- `configuration_space_status` remains '
    '`UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE` and is not overwritten by '
    'sample-set status.',
)

RECORD_HEADER = '| ' + ' | '.join(RECORD_KEYS) + ' |'
RECORD_SEPARATOR = '|' + '|'.join(['---'] * len(RECORD_KEYS)) + '|'


def escape_markdown_cell(text: str) -> str:
    return (
        text.replace('\\', '\\\\')
        .replace('|', '\\|')
        .replace('\r', '\\r')
        .replace('\n', '\\n')
    )


def unescape_markdown_cell(text: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\' and index + 1 < len(text):
            nxt = text[index + 1]
            if nxt == '\\':
                out.append('\\')
            elif nxt == '|':
                out.append('|')
            elif nxt == 'n':
                out.append('\n')
            elif nxt == 'r':
                out.append('\r')
            else:
                raise InvalidInputError(
                    f'unknown markdown cell escape \\{nxt}'
                )
            index += 2
            continue
        out.append(char)
        index += 1
    return ''.join(out)


def split_markdown_row(line: str) -> list[str]:
    raw = line.rstrip('\n')
    if not raw.startswith('|'):
        raise InvalidInputError('markdown table row must start with |')
    cells: list[str] = []
    buf: list[str] = []
    index = 1
    while index < len(raw):
        char = raw[index]
        if char == '\\' and index + 1 < len(raw):
            buf.append('\\')
            buf.append(raw[index + 1])
            index += 2
            continue
        if char == '|':
            cells.append(''.join(buf).strip())
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    if ''.join(buf).strip():
        raise InvalidInputError('markdown table row must end with |')
    return cells


def render_configuration_space_markdown(
    metadata: Mapping[str, Any],
    records: list[dict[str, Any]],
) -> str:
    if tuple(metadata) != METADATA_KEYS:
        raise InvalidInputError(
            'markdown metadata key order is not the frozen contract'
        )
    lines = [
        '# Arachne-HX6 G4 Configuration-Space Report',
        '',
        *BANNER_LINES,
        '',
        '## Summary',
        '',
        '| key | value |',
        '|---|---|',
    ]
    for key in METADATA_KEYS:
        value_cell = escape_markdown_cell(compact_json(metadata[key]))
        lines.append(f'| {escape_markdown_cell(key)} | {value_cell} |')
    lines.extend(
        [
            '',
            '## Records',
            '',
            RECORD_HEADER,
            RECORD_SEPARATOR,
        ]
    )
    for record in records:
        lines.append(_render_record_row(record))
    lines.extend(['', '## Limitations', ''])
    lines.extend(LIMITATION_LINES)
    lines.append('')
    return '\n'.join(lines)


def _render_record_row(record: Mapping[str, Any]) -> str:
    cells: list[str] = []
    for key in RECORD_KEYS:
        if key not in record:
            raise InvalidInputError(f'record missing {key}')
        value = record[key]
        if key in (
            'joint_values',
            'geometry_source',
            'limitation_reasons',
        ):
            cells.append(escape_markdown_cell(compact_json(value)))
            continue
        if key == 'nominal_separation_or_intersection':
            if value is None:
                cells.append(MD_NULL)
            else:
                cells.append(escape_markdown_cell(compact_json(value)))
            continue
        text = require_plain_string(value, key)
        cells.append(escape_markdown_cell(text))
    return '| ' + ' | '.join(cells) + ' |'


def parse_configuration_space_markdown(
    text: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lines = text.split('\n')
    if not lines or lines[0] != '# Arachne-HX6 G4 Configuration-Space Report':
        raise InvalidInputError('markdown title is not the frozen contract')
    banner_index = _require_section_index(lines, BANNER_LINES[0])
    for offset, expected in enumerate(BANNER_LINES):
        if lines[banner_index + offset] != expected:
            raise InvalidInputError('markdown safety banner is not the frozen contract')
    summary_index = _require_heading(lines, '## Summary')
    records_index = _require_heading(lines, '## Records')
    limits_index = _require_heading(lines, '## Limitations')
    metadata = _parse_summary_table(lines[summary_index + 1:records_index])
    records = _parse_records_table(lines[records_index + 1:limits_index])
    limitation_text = '\n'.join(lines[limits_index + 1:])
    for expected in LIMITATION_LINES:
        if expected not in limitation_text:
            raise InvalidInputError('markdown limitation section is incomplete')
    return metadata, records


def _require_heading(lines: list[str], heading: str) -> int:
    for index, line in enumerate(lines):
        if line == heading:
            return index
    raise InvalidInputError(f'markdown missing heading {heading}')


def _require_section_index(lines: list[str], first: str) -> int:
    for index, line in enumerate(lines):
        if line == first:
            return index
    raise InvalidInputError('markdown missing safety banner')


def _parse_summary_table(lines: list[str]) -> dict[str, Any]:
    rows = [line for line in lines if line.startswith('|')]
    if len(rows) < 2:
        raise InvalidInputError('markdown summary table is missing')
    header = split_markdown_row(rows[0])
    if header != ['key', 'value']:
        raise InvalidInputError('markdown summary header is not the frozen contract')
    if not _is_separator_row(rows[1], 2):
        raise InvalidInputError('markdown summary separator is invalid')
    metadata: dict[str, Any] = {}
    for line in rows[2:]:
        cells = split_markdown_row(line)
        if len(cells) != 2:
            raise InvalidInputError('markdown summary row must have two cells')
        key = unescape_markdown_cell(cells[0])
        raw = unescape_markdown_cell(cells[1])
        try:
            metadata[key] = json_roundtrip(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise InvalidInputError(
                f'markdown summary value is not JSON for {key}'
            ) from exc
    if tuple(metadata) != METADATA_KEYS:
        raise InvalidInputError(
            'markdown summary keys or order do not match the contract'
        )
    return metadata


def _parse_records_table(lines: list[str]) -> list[dict[str, Any]]:
    rows = [line for line in lines if line.startswith('|')]
    if len(rows) < 2:
        raise InvalidInputError('markdown records table is missing')
    header = split_markdown_row(rows[0])
    if tuple(header) != RECORD_KEYS:
        raise InvalidInputError('markdown records header is not the frozen contract')
    if not _is_separator_row(rows[1], len(RECORD_KEYS)):
        raise InvalidInputError('markdown records separator is invalid')
    records: list[dict[str, Any]] = []
    for line in rows[2:]:
        cells = split_markdown_row(line)
        if len(cells) != len(RECORD_KEYS):
            raise InvalidInputError('markdown record row has the wrong column count')
        records.append(_record_from_markdown_cells(cells))
    return records


def _is_separator_row(line: str, n_columns: int) -> bool:
    cells = split_markdown_row(line)
    if len(cells) != n_columns:
        return False
    return all(set(cell) <= {'-', ':'} and '-' in cell for cell in cells)


def _record_from_markdown_cells(cells: list[str]) -> dict[str, Any]:
    raw = {
        key: unescape_markdown_cell(cell)
        for key, cell in zip(RECORD_KEYS, cells)
    }
    gap_text = raw['nominal_separation_or_intersection']
    if gap_text == MD_NULL:
        gap: float | None = None
    else:
        try:
            parsed = json.loads(gap_text)
        except json.JSONDecodeError as exc:
            raise InvalidInputError(
                'markdown gap cell is not JSON'
            ) from exc
        gap = json_roundtrip(parsed)
    try:
        joint_values = json.loads(raw['joint_values'])
        geometry_source = json.loads(raw['geometry_source'])
        limitation_reasons = json.loads(raw['limitation_reasons'])
    except json.JSONDecodeError as exc:
        raise InvalidInputError('markdown complex field is not JSON') from exc
    record = {
        'sample_id': require_plain_string(raw['sample_id'], 'sample_id'),
        'source_state_or_path': require_plain_string(
            raw['source_state_or_path'], 'source_state_or_path'
        ),
        'evaluated_pair': require_plain_string(
            raw['evaluated_pair'], 'evaluated_pair'
        ),
        'joint_values': json_roundtrip(joint_values),
        'geometry_source': json_roundtrip(geometry_source),
        'proxy_status': require_plain_string(raw['proxy_status'], 'proxy_status'),
        'hardware_validation_status': require_plain_string(
            raw['hardware_validation_status'], 'hardware_validation_status'
        ),
        'nominal_separation_or_intersection': gap,
        'result_status': require_plain_string(
            raw['result_status'], 'result_status'
        ),
        'limitation_reasons': json_roundtrip(limitation_reasons),
    }
    return record
