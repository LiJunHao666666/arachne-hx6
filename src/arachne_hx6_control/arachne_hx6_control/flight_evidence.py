"""Build a reproducible FLIGHT-SIM-04 evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

from .flight_evidence_contract import (
    COMMAND_GUARD,
    CONTROLLER,
    MODEL,
    RESULT_SCHEMA,
)

MANIFEST_SCHEMA = 'arachne.flight-sim-evidence/v1'
REQUIRED_SCENARIOS = {
    'nominal': 'gazebo-takeoff-hover-land',
    'link_loss': 'gazebo-command-dropout-landing',
}
REQUIRED_METRICS = {
    'nominal': {
        'sample_count', 'initial_altitude_m', 'max_altitude_m',
        'final_altitude_m', 'hover_span_m',
        'max_horizontal_displacement_m',
    },
    'link_loss': {
        'sample_count', 'initial_altitude_m', 'max_altitude_m',
        'final_altitude_m', 'failsafe_trigger_delay_s',
        'landed_locked_observed', 'max_horizontal_displacement_m',
        'state_path',
    },
}
REQUIRED_CRITERIA = {
    'nominal': {
        'minimum_max_altitude_m', 'maximum_final_altitude_m',
        'maximum_hover_span_m', 'maximum_horizontal_displacement_m',
    },
    'link_loss': {
        'minimum_max_altitude_m', 'minimum_failsafe_delay_s',
        'maximum_failsafe_delay_s', 'landed_locked_required',
        'maximum_final_altitude_m', 'maximum_horizontal_displacement_m',
    },
}
SOURCE_FILES = (
    'src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf',
    'src/arachne_hx6_simulation/worlds/flight_hex.sdf',
    'src/arachne_hx6_control/arachne_hx6_control/flight_command_guard.py',
    'src/arachne_hx6_control/arachne_hx6_control/gazebo_flight_scenario.py',
    'src/arachne_hx6_control/arachne_hx6_control/gazebo_link_loss_scenario.py',
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ['git', '-C', str(root), *arguments],
        capture_output=True, check=False, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else 'UNKNOWN'


def _validate_result(label: str, payload: dict) -> list[str]:
    expected_id = REQUIRED_SCENARIOS[label]
    expected_components = {
        'model': MODEL,
        'controller': CONTROLLER,
    }
    if label == 'link_loss':
        expected_components['command_guard'] = COMMAND_GUARD
    metrics = payload.get('metrics')
    criteria = payload.get('criteria')
    metrics_complete = (
        isinstance(metrics, dict)
        and REQUIRED_METRICS[label] <= metrics.keys()
        and all(metrics[key] is not None for key in REQUIRED_METRICS[label])
        and all(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or math.isfinite(value)
            for value in metrics.values()
        )
    )
    criteria_complete = (
        isinstance(criteria, dict)
        and REQUIRED_CRITERIA[label] <= criteria.keys()
    )
    checks = {
        'schema': payload.get('schema') == RESULT_SCHEMA,
        'scenario.id': payload.get('scenario', {}).get('id') == expected_id,
        'scenario.version': payload.get('scenario', {}).get('version') == '1',
        'status': payload.get('status') == 'ANALYSIS_ONLY',
        'procurement_allowed': payload.get('procurement_allowed') is False,
        'flight_readiness': payload.get('flight_readiness') == 'UNDETERMINED',
        'scenario_result': payload.get('scenario_result') == 'PASS',
        'criteria': criteria_complete,
        'metrics': metrics_complete,
        'components': payload.get('components') == expected_components,
    }
    return [
        f'{label}: invalid {field}'
        for field, valid in checks.items() if not valid
    ]


def build_manifest(root: Path, result_paths: dict[str, Path]) -> dict:
    """Validate scenario outputs and bind them to exact source hashes."""
    errors = []
    scenarios = {}
    for label, expected_id in REQUIRED_SCENARIOS.items():
        path = result_paths[label]
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f'{label}: unreadable result: {exc}')
            continue
        errors.extend(_validate_result(label, payload))
        scenarios[expected_id] = {
            'result_file_sha256': _sha256(path),
            'result': payload,
        }

    sources = {}
    for relative in SOURCE_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f'missing source file: {relative}')
            continue
        sources[relative] = {'sha256': _sha256(path)}

    revision = _git(root, 'rev-parse', 'HEAD')
    status = _git(root, 'status', '--porcelain', '--untracked-files=all')
    if revision == 'UNKNOWN' or len(revision) != 40:
        errors.append('unable to resolve a full Git source revision')
    if status == 'UNKNOWN':
        errors.append('unable to inspect Git working-tree status')
    return {
        'schema': MANIFEST_SCHEMA,
        'schema_version': 1,
        'milestone': 'FLIGHT-SIM-04',
        'status': 'ANALYSIS_ONLY',
        'procurement_allowed': False,
        'flight_readiness': 'UNDETERMINED',
        'source_revision': revision,
        'working_tree_clean': status == '',
        'source_files': sources,
        'scenarios': scenarios,
        'evidence_result': 'PASS' if not errors else 'FAIL',
        'errors': errors,
        'limitations': [
            'All recorded runs use a Gazebo planning model',
            'Source hashes provide traceability, not hardware validation',
            'Simulation evidence does not establish physical flight readiness',
        ],
    }


def main(argv=None):
    """Build the evidence manifest and return its validation status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--nominal', type=Path, required=True)
    parser.add_argument('--link-loss', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args(argv)
    manifest = build_manifest(
        arguments.repository_root.resolve(),
        {'nominal': arguments.nominal, 'link_loss': arguments.link_loss},
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(manifest, indent=2, allow_nan=False, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    print(
        f"FLIGHT-SIM-04 evidence: {manifest['evidence_result']}; "
        'flight: UNDETERMINED',
        flush=True,
    )
    return 0 if manifest['evidence_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
