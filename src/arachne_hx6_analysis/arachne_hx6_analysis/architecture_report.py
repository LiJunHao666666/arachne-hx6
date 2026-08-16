"""Write ANALYSIS_ONLY JSON, CSV, and Markdown architecture-envelope reports.

JSON payload construction, Markdown rendering, and CSV rendering live in
sibling modules. This façade owns atomic write-out and the public names
used by the CLI and tests.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from arachne_hx6_analysis.architecture import ArchitectureResult
from arachne_hx6_analysis.architecture_report_csv import render_architecture_csv
from arachne_hx6_analysis.architecture_report_markdown import (
    MD_NULL,
    render_architecture_markdown,
)
from arachne_hx6_analysis.architecture_report_payload import (
    EQUATIONS,
    build_architecture_json,
)
from arachne_hx6_analysis.model import InvalidInputError
import math

JSON_NAME = 'architecture_envelope.json'
CSV_NAME = 'architecture_envelope.csv'
MARKDOWN_NAME = 'architecture_envelope.md'


def write_architecture_reports(
    result: ArchitectureResult,
    output_dir: str | Path,
    generated_at: datetime | None = None,
) -> dict[str, Path]:
    """Write JSON, CSV, and Markdown into output_dir.

    All three artifacts are serialized in memory first, written to a staging
    directory, then replaced onto the final names so a failure does not leave
    a partial official report set.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = generated_at or datetime.now(timezone.utc)
    stamp_text = stamp.astimezone(timezone.utc).isoformat()
    payload = build_architecture_json(result, stamp_text)
    assert_strict_finite_json(payload)
    json_text = json.dumps(
        payload, indent=2, sort_keys=False, allow_nan=False
    ) + '\n'
    csv_text = render_architecture_csv(result)
    md_text = render_architecture_markdown(result, stamp_text)
    json_path = out / JSON_NAME
    csv_path = out / CSV_NAME
    md_path = out / MARKDOWN_NAME
    staging = Path(tempfile.mkdtemp(prefix='.arachne_g2_write_', dir=out))
    try:
        (staging / JSON_NAME).write_text(json_text, encoding='utf-8')
        (staging / CSV_NAME).write_text(csv_text, encoding='utf-8')
        (staging / MARKDOWN_NAME).write_text(md_text, encoding='utf-8')
        os.replace(staging / JSON_NAME, json_path)
        os.replace(staging / CSV_NAME, csv_path)
        os.replace(staging / MARKDOWN_NAME, md_path)
    except Exception:
        for path in (json_path, csv_path, md_path):
            if path.exists() and path.stat().st_size == 0:
                path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {'json': json_path, 'csv': csv_path, 'markdown': md_path}


def assert_strict_finite_json(value: Any, path: str = 'json') -> None:
    """Reject NaN, Infinity, and non-JSON numeric types before writing."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidInputError(
                f'{path} is not a finite JSON number: {value!r}'
            )
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            assert_strict_finite_json(item, f'{path}.{key}')
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_strict_finite_json(item, f'{path}[{index}]')
        return
    raise InvalidInputError(
        f'{path} has unsupported JSON type {type(value).__name__}'
    )
