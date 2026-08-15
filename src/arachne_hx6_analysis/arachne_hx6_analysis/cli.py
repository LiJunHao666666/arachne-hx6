"""CLI entry point for G1.5 ANALYSIS_ONLY propulsion reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from arachne_hx6_analysis.model import (
    AnalysisError,
    GATE_CONDITIONAL_CANDIDATE,
    STATUS_OVERALL_UNDETERMINED,
)
from arachne_hx6_analysis.report import write_reports
from arachne_hx6_analysis.solver import (
    load_analysis_config,
    solve_all_uncertainty_cases,
)

_DEFAULT_CONFIG_NAME = 'propulsion_scenarios.yaml'


def default_config_path() -> Path:
    """Installed share config, then source-tree fallback."""
    try:
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory('arachne_hx6_analysis'))
        candidate = share / 'config' / _DEFAULT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    return (
        Path(__file__).resolve().parent.parent / 'config' / _DEFAULT_CONFIG_NAME
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Arachne-HX6 G1.5 propulsion feasibility report. '
            'ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.'
        )
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Path to propulsion_scenarios.yaml (planning inputs only).',
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory for JSON, CSV, and Markdown outputs.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config) if args.config else default_config_path()
    try:
        config = load_analysis_config(config_path)
        by_case = solve_all_uncertainty_cases(config)
        results = by_case.get('nominal') or next(iter(by_case.values()))
        paths = write_reports(
            config,
            results,
            args.output_dir,
            results_by_uncertainty=by_case,
        )
    except (AnalysisError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print('ANALYSIS_ONLY')
    print('NOT_FOR_PROCUREMENT')
    print(f'overall_propulsion_feasibility: {STATUS_OVERALL_UNDETERMINED}')
    print(f'config: {config_path}')
    for kind, path in paths.items():
        print(f'{kind}: {path}')
    print(f'rows_nominal: {len(results)}')
    print(
        'energy_mass_closure_nominal: '
        f'{sum(1 for row in results if row.energy_mass_closure)}/{len(results)}'
    )
    print(
        'combined_candidates_nominal: '
        f'{sum(1 for row in results if row.combined_current_baseline_gate == GATE_CONDITIONAL_CANDIDATE)}'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
