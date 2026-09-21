"""Tests for Gazebo command-dropout acceptance analysis."""

from arachne_hx6_control.gazebo_link_loss_scenario import (
    analyze,
    command_for,
)


def test_command_schedule_contains_real_dropout():
    assert command_for(0.0) == (0.35, 'TAKEOFF')
    assert command_for(4.0) == (0.0, 'HOVER')
    assert command_for(6.0) == (None, 'LINK_LOSS')


def test_accepts_controlled_failsafe_landing():
    samples = [
        {
            'x_m': 0.0,
            'y_m': 0.0,
            'z_m': altitude,
        }
        for altitude in (
            [0.02] * 10
            + [0.7, 1.0, 1.3] * 10
            + [1.2, 0.9, 0.6, 0.3, 0.05] * 10
        )
    ]
    events = [
        {'elapsed_s': 0.1, 'state': 'DISARMED'},
        {'elapsed_s': 0.2, 'state': 'ACTIVE'},
        {'elapsed_s': 6.4, 'state': 'AIRBORNE_FAILSAFE'},
        {'elapsed_s': 12.0, 'state': 'LANDED_LOCKED'},
    ]
    result = analyze(samples, events)
    assert result['scenario_result'] == 'PASS'
    assert result['procurement_allowed'] is False
    assert result['flight_readiness'] == 'UNDETERMINED'


def test_rejects_missing_failsafe_transition():
    samples = [
        {'x_m': 0.0, 'y_m': 0.0, 'z_m': 1.0}
        for _ in range(30)
    ]
    events = [{'elapsed_s': 0.1, 'state': 'ACTIVE'}]
    assert analyze(samples, events)['scenario_result'] == 'FAIL'
