"""Unit tests for the planning-model flight command guard."""

import math

from arachne_hx6_control.flight_command_guard import (
    GuardLogic,
    MotionCommand,
)


def test_active_request_is_forwarded():
    guard = GuardLogic()
    guard.tick(0.0, 0.02)
    command = MotionCommand(x=0.1, z=0.3, yaw=0.2)
    assert guard.accept(command, True, 0.0)
    output = guard.tick(0.2, 0.4)
    assert output.state == GuardLogic.ACTIVE
    assert output.enabled
    assert output.command == command


def test_airborne_timeout_commands_controlled_descent():
    guard = GuardLogic(timeout_s=0.4, descent_speed_mps=-0.25)
    guard.tick(0.0, 0.02)
    assert guard.accept(MotionCommand(z=0.35), True, 0.0)
    output = guard.tick(0.41, 1.0)
    assert output.state == GuardLogic.AIRBORNE_FAILSAFE
    assert output.reason == 'COMMAND_TIMEOUT'
    assert output.enabled
    assert output.command == MotionCommand(z=-0.25)


def test_failsafe_latches_until_ground_reset():
    guard = GuardLogic()
    guard.tick(0.0, 0.02)
    guard.accept(MotionCommand(z=0.35), True, 0.0)
    guard.tick(0.5, 1.0)
    assert not guard.accept(MotionCommand(z=0.2), True, 0.6)
    landed = guard.tick(1.0, 0.05)
    assert landed.state == GuardLogic.LANDED_LOCKED
    assert not landed.enabled
    assert guard.reset()
    assert guard.state == GuardLogic.DISARMED
    assert guard.accept(MotionCommand(z=0.2), True, 1.1)


def test_airborne_reset_is_rejected():
    guard = GuardLogic()
    guard.tick(0.0, 1.0)
    guard.accept(MotionCommand(), False, 0.0)
    assert guard.state == GuardLogic.AIRBORNE_FAILSAFE
    assert not guard.reset()


def test_invalid_request_fails_closed():
    guard = GuardLogic()
    guard.tick(0.0, 1.0)
    assert not guard.accept(MotionCommand(z=math.nan), True, 0.0)
    output = guard.tick(0.1, 1.0)
    assert output.state == GuardLogic.AIRBORNE_FAILSAFE
    assert output.command.z < 0
