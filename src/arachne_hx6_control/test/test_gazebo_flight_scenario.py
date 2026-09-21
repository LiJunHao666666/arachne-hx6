"""Tests for the nominal Gazebo flight scenario."""

from arachne_hx6_control.gazebo_flight_scenario import (
    analyze,
    command_for,
)


def test_phase_schedule():
    """The schedule contains takeoff, hover, landing, and disarm."""
    assert command_for(0) == (0.35, 'TAKEOFF')
    assert command_for(4) == (0.0, 'HOVER')
    assert command_for(7) == (-0.25, 'LAND')
    assert command_for(12) == (0.0, 'DISARMED')


def test_accepts_complete_flight_shape():
    """A complete bounded flight shape passes the acceptance analysis."""
    samples = [
        {
            'phase': 'TAKEOFF',
            'x_m': 0,
            'y_m': 0,
            'z_m': 0.02,
        }
        for _ in range(10)
    ]
    samples += [
        {
            'phase': 'HOVER',
            'x_m': 0.01,
            'y_m': 0,
            'z_m': altitude,
        }
        for altitude in [0.68, 0.70, 0.72] * 5
    ]
    samples += [
        {
            'phase': 'LAND',
            'x_m': 0,
            'y_m': 0,
            'z_m': 0.05,
        }
        for _ in range(10)
    ]
    result = analyze(samples)
    assert result['scenario_result'] == 'PASS'
    assert result['procurement_allowed'] is False


def test_rejects_missing_or_unsafe_evidence():
    """Missing samples and excessive drift fail the scenario."""
    assert analyze([])['scenario_result'] == 'FAIL'
    unsafe = [
        {
            'phase': 'HOVER',
            'x_m': 0.2,
            'y_m': 0,
            'z_m': 0.1,
        }
        for _ in range(30)
    ]
    assert analyze(unsafe)['scenario_result'] == 'FAIL'
