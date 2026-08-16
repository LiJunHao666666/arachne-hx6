"""Write ANALYSIS_ONLY JSON, CSV, and Markdown G3 reports.

All three artifacts are serialized in memory, written to a staging
directory, then replaced onto the final names. Either the whole trio is
updated, or the previous trio is restored. A failure on an empty output
directory leaves no official report files. Temporary directories are
always removed.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile

from arachne_hx6_analysis.architecture_report import assert_strict_finite_json
from arachne_hx6_analysis.requirements_report_csv import render_requirements_csv
from arachne_hx6_analysis.requirements_report_markdown import (
    MD_NULL,
    render_requirements_markdown,
)
from arachne_hx6_analysis.requirements_report_payload import (
    build_requirements_json,
)
from arachne_hx6_analysis.requirements_types import RequirementsResult

JSON_NAME = 'requirements_evidence_report.json'
CSV_NAME = 'requirements_evidence_report.csv'
MARKDOWN_NAME = 'requirements_evidence_report.md'
REPORT_NAMES = (JSON_NAME, CSV_NAME, MARKDOWN_NAME)


def write_requirements_reports(
    result: RequirementsResult,
    output_dir: str | Path,
    generated_at: datetime | None = None,
) -> dict[str, Path]:
    """Write JSON, CSV, and Markdown into output_dir as one trio."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = generated_at or datetime.now(timezone.utc)
    stamp_text = stamp.astimezone(timezone.utc).isoformat()
    payload = build_requirements_json(result, stamp_text)
    assert_strict_finite_json(payload)
    json_text = json.dumps(
        payload, indent=2, sort_keys=False, allow_nan=False
    ) + '\n'
    csv_text = render_requirements_csv(result)
    md_text = render_requirements_markdown(result, stamp_text)
    contents = {
        JSON_NAME: json_text,
        CSV_NAME: csv_text,
        MARKDOWN_NAME: md_text,
    }
    staging = Path(tempfile.mkdtemp(prefix='.arachne_g3_write_', dir=out))
    backup = Path(tempfile.mkdtemp(prefix='.arachne_g3_backup_', dir=out))
    backed_up = False
    try:
        for name, text in contents.items():
            (staging / name).write_text(text, encoding='utf-8')
        for name in REPORT_NAMES:
            current = out / name
            if current.exists():
                shutil.copy2(current, backup / name)
        backed_up = True
        for name in REPORT_NAMES:
            os.replace(staging / name, out / name)
    except Exception:
        if backed_up:
            _restore_report_trio(out, backup)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)
    return {
        'json': out / JSON_NAME,
        'csv': out / CSV_NAME,
        'markdown': out / MARKDOWN_NAME,
    }


def _restore_report_trio(out: Path, backup: Path) -> None:
    """Restore the previous trio, or remove any newly installed reports."""
    for name in REPORT_NAMES:
        dest = out / name
        previous = backup / name
        if previous.exists():
            shutil.copy2(previous, dest)
        else:
            dest.unlink(missing_ok=True)
