"""CLI entry point for G3 ANALYSIS_ONLY requirements and evidence reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from arachne_hx6_analysis.model import (
    AnalysisError,
    STATUS_OVERALL_UNDETERMINED,
)
from arachne_hx6_analysis.requirements import (
    evaluate_requirements,
    load_requirements_config,
)
from arachne_hx6_analysis.requirements_report import write_requirements_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Arachne-HX6 G3 requirements, evidence ledger, and uncertainty '
            'gates. ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.'
        )
    )
    parser.add_argument(
        '--requirements-config',
        default=None,
        help='Path to system_requirements.yaml.',
    )
    parser.add_argument(
        '--evidence-config',
        default=None,
        help='Path to evidence_ledger.yaml.',
    )
    parser.add_argument(
        '--uncertainty-config',
        default=None,
        help='Path to geometry_uncertainty_budget.yaml.',
    )
    parser.add_argument(
        '--stow-config',
        default=None,
        help='Path to stow_requirements.yaml.',
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory for JSON, CSV, and Markdown outputs.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_requirements_config(
            requirements_path=args.requirements_config,
            evidence_path=args.evidence_config,
            uncertainty_path=args.uncertainty_config,
            stow_path=args.stow_config,
        )
        result = evaluate_requirements(config)
        paths = write_requirements_reports(result, args.output_dir)
    except (AnalysisError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print('ANALYSIS_ONLY')
    print('NOT_FOR_PROCUREMENT')
    print(f'overall_system_readiness: {STATUS_OVERALL_UNDETERMINED}')
    print(f'readiness_gate: {result.readiness_gate}')
    print(f'requirements_total: {result.traceability.requirements_total}')
    print(f'requirements_specified: {result.traceability.requirements_specified}')
    print(
        'requirements_incomplete_specification: '
        f'{result.traceability.requirements_incomplete_specification}'
    )
    print(f'requirements_verified: {result.traceability.requirements_verified}')
    print(f'requirements_satisfied: {result.traceability.requirements_satisfied}')
    print(
        'incomplete_blocking_requirement_ids: '
        f'{len(result.traceability.incomplete_blocking_requirement_ids)}'
    )
    print(
        'evidence_blocked_requirement_ids: '
        f'{len(result.traceability.evidence_blocked_requirement_ids)}'
    )
    print(
        'all_blocking_requirement_ids: '
        f'{len(result.traceability.all_blocking_requirement_ids)}'
    )
    print(
        'planning_assumption_only_requirement_ids: '
        f'{len(result.traceability.planning_assumption_only_requirement_ids)}'
    )
    print(
        'mixed_insufficient_evidence_requirement_ids: '
        f'{len(result.traceability.mixed_insufficient_evidence_requirement_ids)}'
    )
    print(f'requirements_status: {result.requirements_status}')
    print(f'evidence_ledger_status: {result.evidence_ledger_status}')
    print(f'mass_ledger_status: {result.mass_ledger_status}')
    print(f'geometry_uncertainty_budget_status: {result.geometry_uncertainty_budget_status}')
    print(f'stow_requirements_status: {result.stow_requirements_status}')
    print(f'arm_radius_mass_coupling_status: {result.arm_radius_mass_coupling_status}')
    print(f'procurement_allowed: {str(result.procurement_allowed).lower()}')
    print(f'requirements_config: {config.requirements_path}')
    for kind, path in paths.items():
        print(f'{kind}: {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
