"""CLI entry point for G2 ANALYSIS_ONLY architecture-envelope reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from arachne_hx6_analysis.architecture import (
    default_architecture_config_path,
    evaluate_architecture,
    load_architecture_config,
)
from arachne_hx6_analysis.architecture_report import write_architecture_reports
from arachne_hx6_analysis.model import (
    AnalysisError,
    STATUS_OVERALL_UNDETERMINED,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Arachne-HX6 G2 architecture envelope report. '
            'ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.'
        )
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Path to architecture_envelope.yaml (planning inputs only).',
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory for JSON, CSV, and Markdown outputs.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = (
        Path(args.config) if args.config else default_architecture_config_path()
    )
    try:
        config = load_architecture_config(config_path)
        result = evaluate_architecture(config)
        paths = write_architecture_reports(result, args.output_dir)
    except (AnalysisError, OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print('ANALYSIS_ONLY')
    print('NOT_FOR_PROCUREMENT')
    print(f'overall_architecture_feasibility: {STATUS_OVERALL_UNDETERMINED}')
    print(f'mass_ledger_status: {result.mass_ledger_status}')
    print(f'stow_requirements_status: {result.stow_requirements_status}')
    print(f'robust_geometry_status: {result.robust_geometry_status}')
    print(f'config: {config_path}')
    for kind, path in paths.items():
        print(f'{kind}: {path}')
    print(f'geometry_candidates: {len(result.geometry_candidates)}')
    print(f'joint_gate_rows: {len(result.joint_gate_rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
