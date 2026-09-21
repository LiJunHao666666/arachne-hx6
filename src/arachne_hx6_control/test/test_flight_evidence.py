"""Tests for the FLIGHT-SIM-04 evidence manifest."""

import json
from pathlib import Path
import subprocess

from arachne_hx6_control.flight_evidence import build_manifest
from arachne_hx6_control.flight_evidence_contract import result_header


def _result(scenario_id, *, passed=True):
    guarded = scenario_id == 'gazebo-command-dropout-landing'
    if guarded:
        criteria = {
            'minimum_max_altitude_m': 0.6,
            'minimum_failsafe_delay_s': 0.2,
            'maximum_failsafe_delay_s': 0.8,
            'landed_locked_required': True,
            'maximum_final_altitude_m': 0.12,
            'maximum_horizontal_displacement_m': 0.1,
        }
        metrics = {
            'sample_count': 100,
            'initial_altitude_m': 0.02,
            'max_altitude_m': 1.2,
            'final_altitude_m': 0.02,
            'failsafe_trigger_delay_s': 0.4,
            'landed_locked_observed': True,
            'max_horizontal_displacement_m': 0.0,
            'state_path': [
                'DISARMED', 'ACTIVE',
                'AIRBORNE_FAILSAFE', 'LANDED_LOCKED',
            ],
        }
    else:
        criteria = {
            'minimum_max_altitude_m': 0.6,
            'maximum_final_altitude_m': 0.2,
            'maximum_hover_span_m': 0.15,
            'maximum_horizontal_displacement_m': 0.1,
        }
        metrics = {
            'sample_count': 100,
            'initial_altitude_m': 0.02,
            'max_altitude_m': 1.2,
            'final_altitude_m': 0.02,
            'hover_span_m': 0.04,
            'max_horizontal_displacement_m': 0.0,
        }
    return {
        **result_header(scenario_id, '1', guarded=guarded),
        'criteria': criteria,
        'metrics': metrics,
        'scenario_result': 'PASS' if passed else 'FAIL',
    }


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / 'repository'
    for relative in (
        'src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf',
        'src/arachne_hx6_simulation/worlds/flight_hex.sdf',
        'src/arachne_hx6_control/arachne_hx6_control/flight_command_guard.py',
        'src/arachne_hx6_control/arachne_hx6_control/gazebo_flight_scenario.py',
        'src/arachne_hx6_control/arachne_hx6_control/gazebo_link_loss_scenario.py',
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(
        [
            'git', '-C', str(root), '-c', 'user.name=Test',
            '-c', 'user.email=test@localhost',
            'commit', '-qm', 'fixture',
        ],
        check=True,
    )
    return root


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


def test_manifest_binds_passing_results_to_clean_sources(tmp_path):
    root = _repository(tmp_path)
    nominal = _write(
        tmp_path / 'nominal.json',
        _result('gazebo-takeoff-hover-land'),
    )
    link_loss = _write(
        tmp_path / 'link-loss.json',
        _result('gazebo-command-dropout-landing'),
    )
    manifest = build_manifest(
        root, {'nominal': nominal, 'link_loss': link_loss},
    )
    assert manifest['evidence_result'] == 'PASS'
    assert manifest['working_tree_clean'] is True
    assert len(manifest['source_revision']) == 40
    assert len(manifest['source_files']) == 5
    assert all(
        len(item['sha256']) == 64
        for item in manifest['source_files'].values()
    )


def test_manifest_rejects_failed_or_mislabeled_results(tmp_path):
    root = _repository(tmp_path)
    nominal = _write(
        tmp_path / 'nominal.json', _result('wrong-scenario'),
    )
    link_loss = _write(
        tmp_path / 'link-loss.json',
        _result('gazebo-command-dropout-landing', passed=False),
    )
    manifest = build_manifest(
        root, {'nominal': nominal, 'link_loss': link_loss},
    )
    assert manifest['evidence_result'] == 'FAIL'
    assert 'nominal: invalid scenario.id' in manifest['errors']
    assert 'link_loss: invalid scenario_result' in manifest['errors']


def test_manifest_rejects_incomplete_quantitative_evidence(tmp_path):
    root = _repository(tmp_path)
    incomplete = _result('gazebo-takeoff-hover-land')
    incomplete['metrics'] = {}
    link_loss = _result('gazebo-command-dropout-landing')
    link_loss['components'].pop('command_guard')
    manifest = build_manifest(
        root,
        {
            'nominal': _write(tmp_path / 'nominal.json', incomplete),
            'link_loss': _write(tmp_path / 'link-loss.json', link_loss),
        },
    )
    assert manifest['evidence_result'] == 'FAIL'
    assert 'nominal: invalid metrics' in manifest['errors']
    assert 'link_loss: invalid components' in manifest['errors']
