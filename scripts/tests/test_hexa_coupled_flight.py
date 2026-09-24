"""Behavioral checks for the coupled six-rotor planning exercise."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import hexa_coupled_flight as flight  # noqa: E402


def test_takeoff_hover_disturbance_recovery_and_landing():
    result = flight.simulate()
    metrics = result['metrics']
    assert result['scenario_result'] == 'PASS'
    assert result['procurement_allowed'] is False
    assert result['flight_readiness'] == 'UNDETERMINED'
    assert metrics['max_altitude_m'] >= 1.0
    assert metrics['max_horizontal_displacement_m'] > 0.05
    assert metrics['recovery_horizontal_error_m'] < (
        metrics['max_horizontal_displacement_m']
    )
    assert metrics['final_altitude_m'] == 0.0


def test_six_motor_outputs_are_bounded_and_reproducible():
    first = flight.simulate()
    second = flight.simulate()
    assert first == second
    limit = first['parameters']['max_thrust_per_rotor_n']
    assert all(
        len(sample['rotor_thrust_n']) == 6
        and all(0 <= value <= limit for value in sample['rotor_thrust_n'])
        for sample in first['samples']
    )


def test_disturbance_is_observable_and_not_needed_for_nominal_hover():
    disturbed = flight.simulate()
    quiet = flight.simulate(
        flight.Parameters(disturbance_acceleration_m_s2=0.0)
    )
    assert quiet['scenario_result'] == 'PASS'
    assert quiet['metrics']['max_horizontal_displacement_m'] < 1e-10
    assert disturbed['metrics']['max_horizontal_displacement_m'] > 0.0


def test_insufficient_headroom_fails_acceptance():
    result = flight.simulate(
        flight.Parameters(max_thrust_per_rotor_n=1.1)
    )
    assert result['scenario_result'] == 'FAIL'
    assert result['metrics']['saturated_channel_steps'] > 0


@pytest.mark.parametrize('kwargs', [
    {'mass_kg': 0},
    {'duration_s': 3.0},
    {'motor_tau_s': float('nan')},
    {'max_thrust_per_rotor_n': 1.0},
    {'disturbance_acceleration_m_s2': -1},
])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        flight.simulate(flight.Parameters(**kwargs))


def test_cli_writes_bounded_analysis_only_evidence(tmp_path):
    output = tmp_path / 'coupled.json'
    process = subprocess.run(
        [sys.executable, str(SCRIPTS / 'hexa_coupled_flight.py'),
         '--output', str(output)],
        capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(output.read_text())
    assert result['scenario_result'] == 'PASS'
    assert result['scope'] == 'COUPLED_SMALL_ANGLE_PLANNING_MODEL'
    assert result['parameter_evidence'] == 'PLANNING_ASSUMPTION'