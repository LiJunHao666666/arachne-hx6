"""Planning-only six-motor takeoff, hover, and landing in Gazebo."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import subprocess
import time

from actuator_msgs.msg import Actuators
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node


SQUARE_START_S = 4.0
SQUARE_LEG_DURATION_S = 3.5
SQUARE_MOVE_DURATION_S = 2.0
SQUARE_END_S = SQUARE_START_S + 4 * SQUARE_LEG_DURATION_S
SQUARE_HOVER_UNTIL_S = SQUARE_END_S + 0.7


@dataclass(frozen=True)
class MotorParameters:
    """Unmeasured values shared with the Gazebo planning model."""

    mass_kg: float = 0.65
    gravity_m_s2: float = 9.80665
    arm_m: float = 0.12
    motor_constant_n_per_rad_s2: float = 1.269e-5
    moment_constant_m: float = 0.016754
    max_thrust_per_rotor_n: float = 2.0
    motor_time_constant_s: float = 0.0182
    altitude_kp_n_per_m: float = 4.0
    vertical_speed_kd_n_per_mps: float = 2.0
    attitude_kp_nm_per_rad: float = 0.08
    attitude_kd_nm_per_rad_s: float = 0.025
    position_kp_mps2_per_m: float = 2.0
    position_kd_mps2_per_mps: float = 2.5


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def reference(elapsed_s: float, hover_until_s: float = 6.0
              ) -> tuple[float, float, str]:
    """Return target height, vertical speed, and phase."""
    if elapsed_s < 0.5:
        return 0.02, 0.0, 'SETTLE'
    if elapsed_s < 3.5:
        return 0.02 + 0.4 * (elapsed_s - 0.5), 0.4, 'TAKEOFF'
    if elapsed_s < hover_until_s:
        return 1.22, 0.0, 'HOVER'
    if elapsed_s < hover_until_s + 3.0:
        return max(0.02, 1.22 - 0.4 * (elapsed_s - hover_until_s)), -0.4, 'LAND'
    return 0.02, 0.0, 'DISARMED'


def square_trajectory(elapsed_s: float, side_m: float
                      ) -> tuple[float, float, float, float, str]:
    """Return a smooth +X, +Y, -X, -Y world-axis square reference."""
    legs = [
        ('FORWARD', (0.0, 0.0), (side_m, 0.0)),
        ('LEFT', (side_m, 0.0), (side_m, side_m)),
        ('BACKWARD', (side_m, side_m), (0.0, side_m)),
        ('RIGHT_TO_ORIGIN', (0.0, side_m), (0.0, 0.0)),
    ]
    if elapsed_s < SQUARE_START_S or elapsed_s >= SQUARE_END_S:
        return 0.0, 0.0, 0.0, 0.0, 'ORIGIN'
    leg_index = min(
        int((elapsed_s - SQUARE_START_S) / SQUARE_LEG_DURATION_S),
        len(legs) - 1,
    )
    name, start, end = legs[leg_index]
    leg_elapsed = elapsed_s - (
        SQUARE_START_S + SQUARE_LEG_DURATION_S * leg_index
    )
    u = clamp(leg_elapsed / SQUARE_MOVE_DURATION_S, 0.0, 1.0)
    blend = 10 * u**3 - 15 * u**4 + 6 * u**5
    blend_rate = (
        (30 * u**2 - 60 * u**3 + 30 * u**4) /
        SQUARE_MOVE_DURATION_S
        if 0.0 < u < 1.0 else 0.0
    )
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]
    return (
        start[0] + delta_x * blend,
        start[1] + delta_y * blend,
        delta_x * blend_rate,
        delta_y * blend_rate,
        name,
    )


def allocate_wrench(
    thrust_n: float, roll_nm: float, pitch_nm: float, yaw_nm: float,
    parameters: MotorParameters = MotorParameters(),
) -> tuple[list[float], int]:
    """Invert the regular-hex wrench matrix in rotor order 0..5."""
    p = parameters
    positions = [
        (p.arm_m * math.cos(math.radians(30 + 60 * i)),
         p.arm_m * math.sin(math.radians(30 + 60 * i)))
        for i in range(6)
    ]
    x_norm = sum(x * x for x, _ in positions)
    y_norm = sum(y * y for _, y in positions)
    # Gazebo reaction torque: -turningDirection * thrust * momentConstant.
    requested = [
        thrust_n / 6 + y * roll_nm / y_norm - x * pitch_nm / x_norm
        + (-1 if i % 2 == 0 else 1) * yaw_nm
        / (6 * p.moment_constant_m)
        for i, (x, y) in enumerate(positions)
    ]
    limited = [clamp(value, 0.0, p.max_thrust_per_rotor_n)
               for value in requested]
    saturated = sum(abs(a - b) > 1e-9
                    for a, b in zip(requested, limited))
    return [math.sqrt(value / p.motor_constant_n_per_rad_s2)
            for value in limited], saturated


def euler_from_quaternion(q) -> tuple[float, float, float]:
    roll = math.atan2(
        2 * (q.w * q.x + q.y * q.z),
        1 - 2 * (q.x * q.x + q.y * q.y),
    )
    pitch = math.asin(clamp(2 * (q.w * q.y - q.z * q.x), -1, 1))
    yaw = math.atan2(
        2 * (q.w * q.z + q.x * q.y),
        1 - 2 * (q.y * q.y + q.z * q.z),
    )
    return roll, pitch, yaw


def world_linear_velocity(odometry: Odometry) -> tuple[float, float, float]:
    """Rotate child-frame odometry linear velocity into the fixed pose frame."""
    q = odometry.pose.pose.orientation
    v = odometry.twist.twist.linear
    # Gazebo OdometryPublisher reports twist in the body frame (dimensions=3).
    # Include roll/pitch so vertical motion is not mistaken for horizontal drift.
    return (
        (1 - 2 * (q.y**2 + q.z**2)) * v.x
        + 2 * (q.x * q.y - q.w * q.z) * v.y
        + 2 * (q.x * q.z + q.w * q.y) * v.z,
        2 * (q.x * q.y + q.w * q.z) * v.x
        + (1 - 2 * (q.x**2 + q.z**2)) * v.y
        + 2 * (q.y * q.z - q.w * q.x) * v.z,
        2 * (q.x * q.z - q.w * q.y) * v.x
        + 2 * (q.y * q.z + q.w * q.x) * v.y
        + (1 - 2 * (q.x**2 + q.y**2)) * v.z,
    )


def motor_speeds(odometry: Odometry, elapsed_s: float,
                 parameters: MotorParameters = MotorParameters(),
                 yaw_pulse_nm: float = 0.0,
                 target_x_m: float = 0.0,
                 target_y_m: float = 0.0,
                 target_vx_m_s: float = 0.0,
                 target_vy_m_s: float = 0.0,
                 target_yaw_rad: float = 0.0,
                 hover_until_s: float = 6.0,
                 ) -> tuple[list[float], str, int]:
    p = parameters
    target_z, target_vz, phase = reference(elapsed_s, hover_until_s)
    if phase in ('SETTLE', 'DISARMED'):
        return [0.0] * 6, phase, 0
    position = odometry.pose.pose.position
    velocity_x, velocity_y, velocity_z = world_linear_velocity(odometry)
    roll, pitch, yaw = euler_from_quaternion(odometry.pose.pose.orientation)
    rates = odometry.twist.twist.angular
    desired_ax = (p.position_kp_mps2_per_m * (target_x_m - position.x)
                  + p.position_kd_mps2_per_mps *
                  (target_vx_m_s - velocity_x))
    desired_ay = (p.position_kp_mps2_per_m * (target_y_m - position.y)
                  + p.position_kd_mps2_per_mps *
                  (target_vy_m_s - velocity_y))
    desired_body_ax = math.cos(yaw) * desired_ax + math.sin(yaw) * desired_ay
    desired_body_ay = -math.sin(yaw) * desired_ax + math.cos(yaw) * desired_ay
    target_roll = clamp(-desired_body_ay / p.gravity_m_s2, -0.15, 0.15)
    target_pitch = clamp(desired_body_ax / p.gravity_m_s2, -0.15, 0.15)
    total = (
        p.mass_kg * p.gravity_m_s2
        + p.altitude_kp_n_per_m * (target_z - position.z)
        + p.vertical_speed_kd_n_per_mps * (target_vz - velocity_z)
    )
    roll_nm = (
        p.attitude_kp_nm_per_rad * (target_roll - roll)
        - p.attitude_kd_nm_per_rad_s * rates.x
    )
    pitch_nm = (
        p.attitude_kp_nm_per_rad * (target_pitch - pitch)
        - p.attitude_kd_nm_per_rad_s * rates.y
    )
    yaw_error = math.atan2(
        math.sin(target_yaw_rad - yaw), math.cos(target_yaw_rad - yaw),
    )
    yaw_nm = (p.attitude_kp_nm_per_rad * yaw_error
              - p.attitude_kd_nm_per_rad_s * rates.z)
    speeds, saturated = allocate_wrench(
        max(0.0, total), roll_nm, pitch_nm, yaw_nm + yaw_pulse_nm, p,
    )
    return speeds, phase, saturated


def analyze(samples: list[dict], saturated_updates: int,
            parameters: MotorParameters = MotorParameters(),
            target_yaw_deg: float = 0.0,
            horizontal_limit_m: float = 0.25) -> dict:
    if not samples:
        return {'scenario_result': 'FAIL', 'reason': 'no_odometry'}
    altitudes = [s['z_m'] for s in samples]
    horizontal = max(math.hypot(s['x_m'], s['y_m']) for s in samples)
    metrics = {
        'sample_count': len(samples),
        'maximum_altitude_m': max(altitudes),
        'final_altitude_m': altitudes[-1],
        'maximum_horizontal_displacement_m': horizontal,
        'saturated_motor_updates': saturated_updates,
        'peak_tilt_deg': max(s['tilt_deg'] for s in samples),
    }
    phase_metrics = summarize_phases(samples)
    hover = [s for s in samples if s['phase'] == 'HOVER' and s['elapsed_s'] >= 4.5]
    yaw_errors = [
        abs(math.degrees(math.atan2(
            math.sin(math.radians(target_yaw_deg - s['yaw_deg'])),
            math.cos(math.radians(target_yaw_deg - s['yaw_deg'])),
        )))
        for s in samples
    ]
    metrics['peak_abs_yaw_deg'] = max(abs(s['yaw_deg']) for s in samples)
    metrics['peak_abs_yaw_error_deg'] = max(yaw_errors)
    metrics['limited_motor_fraction'] = saturated_updates / (6 * len(samples))
    metrics['hover_max_error_m'] = max((abs(s['z_m'] - 1.22) for s in hover), default=None)
    checks = {
        'yaw_within_10_deg': metrics['peak_abs_yaw_error_deg'] <= 10,
        'limited_motor_fraction_below_5_percent': metrics['limited_motor_fraction'] <= 0.05,
        'hover_within_20_cm': len(hover) >= 10 and metrics['hover_max_error_m'] <= 0.20,
        'all_phases_observed': all(
            phase in phase_metrics
            for phase in ('SETTLE', 'TAKEOFF', 'HOVER', 'LAND', 'DISARMED')
        ),
    }
    passed = (all(checks.values()) and len(samples) >= 20 and metrics['maximum_altitude_m'] >= 0.6
              and metrics['final_altitude_m'] <= 0.15
              and horizontal <= horizontal_limit_m
              and metrics['peak_tilt_deg'] <= 15)
    return {
        'schema': 'arachne.motor-level-gazebo/v2',
        'acceptance_checks': checks,
        'status': 'ANALYSIS_ONLY',
        'procurement_allowed': False,
        'flight_readiness': 'UNDETERMINED',
        'scope': 'GAZEBO_PLANNING_MODEL',
        'parameter_evidence': 'PLANNING_ASSUMPTION',
        'controller': 'arachne-six-output-planning-controller',
        'parameters': asdict(parameters),
        'metrics': metrics,
        'phase_metrics': phase_metrics,
        'samples': samples,
        'diagnostic_note': 'Motor speeds are commands, not measured rotor speeds',
        'scenario_result': 'PASS' if passed else 'FAIL',
        'limitations': [
            'Gazebo motor values are unmeasured assumptions',
            'The odometry feed is idealized and not a hardware estimator',
            'A simulation pass does not establish physical flight readiness',
        ],
    }


def summarize_phases(samples: list[dict]) -> dict:
    """Count limited motors separately from updates containing any limit."""
    result = {}
    for phase in ('SETTLE', 'TAKEOFF', 'HOVER', 'LAND', 'DISARMED'):
        rows = [s for s in samples if s['phase'] == phase]
        if not rows:
            continue
        counts = [s['saturated_motors'] for s in rows]
        result[phase] = {
            'sample_count': len(rows),
            'limited_motor_count': sum(counts),
            'updates_with_any_limit': sum(c > 0 for c in counts),
            'limited_motor_fraction': sum(counts) / (6 * len(rows)),
            'peak_abs_yaw_deg': max(abs(s['yaw_deg']) for s in rows),
            'peak_abs_yaw_rate_rad_s': max(abs(s['yaw_rate_rad_s']) for s in rows),
            'peak_abs_requested_yaw_torque_nm': max(
                abs(s['requested_yaw_torque_nm']) for s in rows
            ),
        }
    return result


def check_yaw_recovery(result: dict, requested_deg: float) -> dict:
    """Require evidence that the injected initial error existed and recovered."""
    samples = result['samples']
    initial = samples[0]['yaw_deg']
    late_hover = [abs(s['yaw_deg']) for s in samples
                  if s['phase'] == 'HOVER' and s['elapsed_s'] >= 4.5]
    result['initial_yaw_test'] = {
        'requested_deg': requested_deg,
        'observed_deg': initial,
        'late_hover_peak_abs_deg': max(late_hover) if late_hover else None,
        'scope': 'INITIAL_HEADING_ERROR_NOT_WIND',
    }
    result['acceptance_checks']['initial_yaw_injection_observed'] = (
        abs(initial - requested_deg) <= 0.5
    )
    result['acceptance_checks']['yaw_recovered_below_1_deg'] = (
        bool(late_hover) and max(late_hover) <= 1.0
    )
    if not all(result['acceptance_checks'].values()):
        result['scenario_result'] = 'FAIL'
    return result


def check_yaw_pulse(result: dict, requested_nm: float) -> dict:
    """Check a commanded motor-torque pulse, not external wind."""
    rows = result['samples']
    active = [s for s in rows if s.get('injected_yaw_command_nm', 0) != 0]
    response = [s['yaw_deg'] for s in rows if 4.0 <= s['elapsed_s'] <= 5.0]
    recovery = [abs(s['yaw_deg']) for s in rows if 5.5 <= s['elapsed_s'] < 6.0]
    direction = 1 if requested_nm > 0 else -1
    peak = max((direction * y for y in response), default=0.0)
    checks = result['acceptance_checks']
    checks['pulse_recorded'] = (
        len(active) >= 10 and all(
            abs(s['injected_yaw_command_nm'] - requested_nm) < 1e-9
            for s in active
        )
    )
    checks['yaw_response_observed'] = peak >= 0.1
    checks['post_pulse_recovery_below_1_deg'] = len(recovery) >= 10 and max(recovery) <= 1.0
    result['yaw_pulse_test'] = {
        'scope': 'MOTOR_COMMAND_TORQUE_PULSE_NOT_EXTERNAL_WIND',
        'requested_nm': requested_nm, 'window_s': [4.0, 4.3],
        'peak_signed_response_deg': peak,
        'recovery_peak_abs_deg': max(recovery) if recovery else None,
    }
    if not all(checks.values()):
        result['scenario_result'] = 'FAIL'
    return result


def check_position_pulse(result: dict, requested_x_m: float,
                         requested_y_m: float) -> dict:
    """Check a single world-axis target pulse with zero initial heading."""
    if bool(requested_x_m) == bool(requested_y_m):
        raise ValueError('exactly one position pulse axis must be nonzero')
    rows = result['samples']
    axis = 'x' if requested_x_m else 'y'
    cross_axis = 'y' if axis == 'x' else 'x'
    requested = requested_x_m if axis == 'x' else requested_y_m
    direction = 1 if requested > 0 else -1
    active = [s for s in rows if (s.get('requested_position_x_m', 0) != 0 or
                                  s.get('requested_position_y_m', 0) != 0)]
    response = [s for s in rows if 4.0 <= s['elapsed_s'] <= 5.2]
    recovery = [s for s in rows if 5.5 <= s['elapsed_s'] < 6.0]
    signed_peak = max((direction * s[f'{axis}_m'] for s in response), default=0.0)
    cross_peak = max((abs(s[f'{cross_axis}_m']) for s in response), default=math.inf)
    recovery_final = abs(recovery[-1][f'{axis}_m']) if recovery else math.inf
    heading_peak = max((abs(s['yaw_deg']) for s in response), default=math.inf)
    checks = result['acceptance_checks']
    checks['position_pulse_recorded'] = (len(active) >= 20 and all(
        abs(s.get('requested_position_x_m', 0) - requested_x_m) < 1e-9 and
        abs(s.get('requested_position_y_m', 0) - requested_y_m) < 1e-9
        for s in active))
    checks['position_response_in_requested_direction'] = signed_peak >= 0.03
    checks['cross_axis_below_5_cm'] = cross_peak <= 0.05
    checks['position_recovered_below_8_cm'] = (
        len(recovery) >= 10 and recovery_final <= 0.08
    )
    checks['heading_stable_below_1_deg'] = heading_peak <= 1.0
    result['position_pulse_test'] = {
        'scope': 'WORLD_AXIS_TARGET_WITH_ZERO_BODY_YAW',
        'body_frame_equivalence': 'WORLD_XY_EQUALS_BODY_XY_ONLY_AT_ZERO_YAW',
        'axis': axis, 'requested_m': requested, 'window_s': [4.0, 4.6],
        'peak_signed_response_m': signed_peak,
        'peak_cross_axis_m': cross_peak,
        'recovery_final_abs_m': recovery_final,
        'peak_abs_heading_deg': heading_peak,
    }
    if not all(checks.values()):
        result['scenario_result'] = 'FAIL'
    return result


def check_body_forward_pulse(result: dict, requested_m: float,
                             heading_deg: float) -> dict:
    """Project a position pulse onto the commanded body heading."""
    rows = result['samples']
    heading = math.radians(heading_deg)
    direction = 1 if requested_m > 0 else -1
    active = [s for s in rows if s.get('requested_body_forward_m', 0) != 0]
    response = [s for s in rows if 4.0 <= s['elapsed_s'] <= 5.2]
    recovery = [s for s in rows if 5.5 <= s['elapsed_s'] < 6.0]

    def projected(sample: dict) -> tuple[float, float]:
        along = sample['x_m'] * math.cos(heading) + sample['y_m'] * math.sin(heading)
        cross = -sample['x_m'] * math.sin(heading) + sample['y_m'] * math.cos(heading)
        return along, cross

    signed_peak = max(
        (direction * projected(sample)[0] for sample in response), default=0.0,
    )
    cross_peak = max(
        (abs(projected(sample)[1]) for sample in response), default=math.inf,
    )
    recovery_final = (
        abs(projected(recovery[-1])[0]) if recovery else math.inf
    )
    heading_errors = [
        abs(math.degrees(math.atan2(
            math.sin(math.radians(heading_deg - sample['yaw_deg'])),
            math.cos(math.radians(heading_deg - sample['yaw_deg'])),
        )))
        for sample in response
    ]
    checks = result['acceptance_checks']
    initial_heading_error = abs(math.degrees(math.atan2(
        math.sin(math.radians(heading_deg - rows[0]['yaw_deg'])),
        math.cos(math.radians(heading_deg - rows[0]['yaw_deg'])),
    )))
    checks['body_heading_injection_observed'] = initial_heading_error <= 0.5
    checks['body_forward_pulse_recorded'] = (
        len(active) >= 20 and
        all(abs(s['requested_body_forward_m'] - requested_m) < 1e-9
            for s in active)
    )
    checks['body_forward_response_observed'] = signed_peak >= 0.03
    checks['body_cross_track_below_5_cm'] = cross_peak <= 0.05
    checks['body_forward_recovered_below_8_cm'] = (
        len(recovery) >= 10 and recovery_final <= 0.08
    )
    checks['body_heading_error_below_1_deg'] = (
        bool(heading_errors) and max(heading_errors) <= 1.0
    )
    result['body_forward_pulse_test'] = {
        'scope': 'BODY_FORWARD_PROJECTED_INTO_WORLD_XY',
        'requested_m': requested_m,
        'target_heading_deg': heading_deg,
        'observed_initial_heading_deg': rows[0]['yaw_deg'],
        'window_s': [4.0, 4.6],
        'peak_signed_response_m': signed_peak,
        'peak_cross_track_m': cross_peak,
        'recovery_final_abs_m': recovery_final,
        'peak_abs_heading_error_deg': (
            max(heading_errors) if heading_errors else None
        ),
    }
    if not all(checks.values()):
        result['scenario_result'] = 'FAIL'
    return result


def check_square_path(result: dict, side_m: float,
                      heading_deg: float = 0.0) -> dict:
    """Require the smooth reference, all four corners, and stable heading."""
    targets = [
        ('FORWARD', side_m, 0.0),
        ('LEFT', side_m, side_m),
        ('BACKWARD', 0.0, side_m),
        ('RIGHT_TO_ORIGIN', 0.0, 0.0),
    ]
    metrics = {}
    recorded = True
    reached = True
    for index, (name, target_x, target_y) in enumerate(targets):
        start = SQUARE_START_S + index * SQUARE_LEG_DURATION_S
        end = start + SQUARE_LEG_DURATION_S
        rows = [
            sample for sample in result['samples']
            if start <= sample['elapsed_s'] < end
        ]
        for sample in rows:
            expected = square_trajectory(sample['elapsed_s'], side_m)
            recorded = recorded and (
                sample.get('requested_path_leg') == name and
                abs(sample.get('requested_position_x_m', math.inf) -
                    expected[0]) < 1e-9 and
                abs(sample.get('requested_position_y_m', math.inf) -
                    expected[1]) < 1e-9 and
                abs(sample.get('requested_velocity_x_m_s', math.inf) -
                    expected[2]) < 1e-9 and
                abs(sample.get('requested_velocity_y_m_s', math.inf) -
                    expected[3]) < 1e-9
            )
        settled = [
            sample for sample in rows
            if sample['elapsed_s'] >= end - (
                SQUARE_LEG_DURATION_S - SQUARE_MOVE_DURATION_S
            )
        ]
        recorded = recorded and len(rows) >= 70 and len(settled) >= 20
        endpoint_error = (
            math.hypot(settled[-1]['x_m'] - target_x,
                       settled[-1]['y_m'] - target_y)
            if settled else math.inf
        )
        metrics[name] = {
            'target_x_m': target_x,
            'target_y_m': target_y,
            'endpoint_error_m': endpoint_error if settled else None,
            'sample_count': len(rows),
            'corner_speed_m_s': (
                math.hypot(settled[-1]['velocity_x_m_s'],
                           settled[-1]['velocity_y_m_s'])
                if settled else None
            ),
        }
        reached = reached and endpoint_error <= 0.08
    path_rows = [
        sample for sample in result['samples']
        if SQUARE_START_S <= sample['elapsed_s'] < SQUARE_END_S
    ]
    heading_peak = max(
        (abs(sample['yaw_deg']) for sample in path_rows), default=math.inf,
    )

    def heading_error(observed: float) -> float:
        difference = math.radians(heading_deg - observed)
        return abs(math.degrees(math.atan2(
            math.sin(difference), math.cos(difference),
        )))

    initial = result['samples'][0] if result['samples'] else None
    heading_error_peak = max(
        (heading_error(sample['yaw_deg']) for sample in path_rows),
        default=math.inf,
    )
    checks = result['acceptance_checks']
    checks['square_path_commands_recorded'] = recorded
    checks['square_waypoints_reached_within_8_cm'] = reached
    checks['square_heading_injection_observed'] = bool(
        initial and 0.0 <= initial['elapsed_s'] < 0.5 and
        heading_error(initial['yaw_deg']) <= 0.5
    )
    checks['square_target_heading_recorded'] = bool(path_rows) and all(
        'target_heading_deg' in sample and
        heading_error(sample['target_heading_deg']) < 1e-9
        for sample in path_rows
    )
    checks['square_path_heading_error_below_1_deg'] = heading_error_peak <= 1.0
    reference_speeds = [
        math.hypot(sample.get('requested_velocity_x_m_s', math.inf),
                   sample.get('requested_velocity_y_m_s', math.inf))
        for sample in path_rows
    ]
    peak_reference_speed = max(reference_speeds, default=math.inf)
    speed_limit = 1.875 * side_m / SQUARE_MOVE_DURATION_S
    tracking_errors = [
        math.hypot(sample['x_m'] - sample['requested_position_x_m'],
                   sample['y_m'] - sample['requested_position_y_m'])
        for sample in path_rows
    ]
    max_tracking_error = max(tracking_errors, default=math.inf)
    corner_speeds = [
        waypoint['corner_speed_m_s'] for waypoint in metrics.values()
    ]
    checks['square_reference_speed_within_limit'] = (
        peak_reference_speed <= speed_limit + 1e-9
    )
    checks['square_tracking_error_within_10_cm'] = (
        max_tracking_error <= 0.10
    )
    checks['square_corner_speed_below_10_cm_s'] = (
        all(speed is not None and speed <= 0.10 for speed in corner_speeds)
    )
    result['square_path_test'] = {
        'scope': 'SMOOTH_WORLD_AXIS_SQUARE_WITH_HELD_BODY_HEADING',
        'world_axis_order': ['+X', '+Y', '-X', '-Y'],
        'target_heading_deg': heading_deg,
        'observed_initial_heading_deg': initial['yaw_deg'] if initial else None,
        'side_m': side_m,
        'leg_duration_s': SQUARE_LEG_DURATION_S,
        'move_duration_s': SQUARE_MOVE_DURATION_S,
        'corner_settle_duration_s': (
            SQUARE_LEG_DURATION_S - SQUARE_MOVE_DURATION_S
        ),
        'peak_reference_speed_m_s': peak_reference_speed if path_rows else None,
        'reference_speed_limit_m_s': speed_limit,
        'maximum_tracking_error_m': max_tracking_error if path_rows else None,
        'waypoints': metrics,
        'peak_abs_heading_deg': heading_peak if path_rows else None,
        'peak_abs_heading_error_deg': heading_error_peak if path_rows else None,
        'linear_velocity_frame': 'WORLD',
    }
    if not all(checks.values()):
        result['scenario_result'] = 'FAIL'
    return result


@dataclass
class FeedbackWatchdog:
    created_s: float
    stamp_ns: int | None = None
    advanced_s: float | None = None
    fault: str | None = None

    def observe(self, stamp_ns: int, now_s: float) -> bool:
        if self.fault:
            return False
        if self.stamp_ns is not None and stamp_ns < self.stamp_ns:
            self.fault = 'odometry_time_reversed'
            return False
        if self.stamp_ns is None or stamp_ns > self.stamp_ns:
            self.stamp_ns = stamp_ns
            self.advanced_s = now_s
            return True
        return False

    def check(self, now_s: float) -> str | None:
        if self.fault is None:
            if self.advanced_s is None and now_s - self.created_s >= 5.0:
                self.fault = 'no_odometry'
            elif self.advanced_s is not None and now_s - self.advanced_s >= 0.3:
                self.fault = 'odometry_stale_or_sim_paused'
        return self.fault


class MotorScenario(Node):
    def __init__(self, output: Path, initial_yaw_deg: float = 0.0,
                 yaw_pulse_nm: float = 0.0, position_pulse_x_m: float = 0.0,
                 position_pulse_y_m: float = 0.0,
                 body_forward_pulse_m: float = 0.0,
                 body_heading_deg: float = 0.0,
                 square_path_side_m: float = 0.0):
        super().__init__('gazebo_motor_scenario')
        self.output = output
        self.initial_yaw_deg = initial_yaw_deg
        self.yaw_pulse_nm = yaw_pulse_nm
        self.position_pulse_x_m = position_pulse_x_m
        self.position_pulse_y_m = position_pulse_y_m
        self.body_forward_pulse_m = body_forward_pulse_m
        self.body_heading_deg = body_heading_deg
        self.square_path_side_m = square_path_side_m
        self.parameters = MotorParameters()
        self.start: float | None = None
        self.odometry: Odometry | None = None
        self.samples: list[dict] = []
        self.saturated_updates = 0
        self.done = False
        self.watchdog = FeedbackWatchdog(time.monotonic())
        self.abort_started: float | None = None
        self.result: dict | None = None
        self.publisher = self.create_publisher(
            Actuators, '/arachne_hx6/command/motor_speed', 10,
        )
        self.create_subscription(
            Odometry, '/model/arachne_flight_hex/odometry',
            self._odometry_callback, 10,
        )
        self.create_timer(0.02, self._step)

    def _odometry_callback(self, message: Odometry) -> None:
        stamp = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
        if self.watchdog.observe(stamp, time.monotonic()):
            self.odometry = message

    def _step(self) -> None:
        now = time.monotonic()
        fault = self.watchdog.check(now)
        if fault:
            command = Actuators()
            command.velocity = [0.0] * 6
            self.publisher.publish(command)
            if self.abort_started is None:
                self.abort_started = now
            if now - self.abort_started >= 0.2:
                self._finish({
                    'schema': 'arachne.motor-level-gazebo/v2',
                    'status': 'ANALYSIS_ONLY', 'procurement_allowed': False,
                    'flight_readiness': 'UNDETERMINED', 'scenario_result': 'FAIL',
                    'abort_reason': fault, 'samples': self.samples,
                    'protection': {'action': 'PUBLISH_ZERO_MOTOR_COMMANDS',
                                   'feedback_timeout_s': 0.3,
                                   'zero_publish_window_s': now - self.abort_started,
                                   'delivery_confirmed': False},
                })
            return
        if self.odometry is None:
            return
        if self.start is None:
            self.start = now
        elapsed = now - self.start
        pulse = self.yaw_pulse_nm if 4.0 <= elapsed < 4.3 else 0.0
        position_active = 4.0 <= elapsed < 4.6
        body_forward = self.body_forward_pulse_m if position_active else 0.0
        target_heading_rad = math.radians(self.body_heading_deg)
        target_x = (
            self.position_pulse_x_m if position_active else 0.0
        ) + body_forward * math.cos(target_heading_rad)
        target_y = (
            self.position_pulse_y_m if position_active else 0.0
        ) + body_forward * math.sin(target_heading_rad)
        target_vx = 0.0
        target_vy = 0.0
        path_leg = 'NONE'
        if self.square_path_side_m:
            target_x, target_y, target_vx, target_vy, path_leg = square_trajectory(
                elapsed, self.square_path_side_m,
            )
        hover_until_s = (
            SQUARE_HOVER_UNTIL_S if self.square_path_side_m else 6.0
        )
        end_s = hover_until_s + 4.5
        speeds, phase, saturated = motor_speeds(
            self.odometry, elapsed, self.parameters, yaw_pulse_nm=pulse,
            target_x_m=target_x, target_y_m=target_y,
            target_vx_m_s=target_vx, target_vy_m_s=target_vy,
            target_yaw_rad=target_heading_rad,
            hover_until_s=hover_until_s,
        )
        self.saturated_updates += saturated
        command = Actuators()
        command.velocity = speeds
        self.publisher.publish(command)
        pos = self.odometry.pose.pose.position
        roll, pitch, yaw = euler_from_quaternion(
            self.odometry.pose.pose.orientation,
        )
        velocity_x, velocity_y, velocity_z = world_linear_velocity(self.odometry)
        self.samples.append({
            'elapsed_s': elapsed, 'phase': phase,
            'x_m': pos.x, 'y_m': pos.y, 'z_m': pos.z,
            'velocity_x_m_s': velocity_x,
            'velocity_y_m_s': velocity_y,
            'velocity_z_m_s': velocity_z,
            'linear_velocity_frame': 'WORLD',
            'tilt_deg': math.degrees(math.hypot(roll, pitch)),
            'yaw_deg': math.degrees(yaw),
            'injected_yaw_command_nm': pulse,
            'requested_position_x_m': target_x,
            'requested_position_y_m': target_y,
            'requested_velocity_x_m_s': target_vx,
            'requested_velocity_y_m_s': target_vy,
            'requested_body_forward_m': body_forward,
            'requested_path_leg': path_leg,
            'target_heading_deg': self.body_heading_deg,
            'yaw_rate_rad_s': self.odometry.twist.twist.angular.z,
            'requested_yaw_torque_nm': (
                self.parameters.attitude_kp_nm_per_rad * math.atan2(
                    math.sin(target_heading_rad - yaw),
                    math.cos(target_heading_rad - yaw),
                )
                - self.parameters.attitude_kd_nm_per_rad_s
                * self.odometry.twist.twist.angular.z
            ) if phase not in ('SETTLE', 'DISARMED') else 0.0,
            'saturated_motors': saturated,
            'commanded_motor_speed_rad_s': list(speeds),
            'odometry_stamp_s': (self.odometry.header.stamp.sec
                                 + self.odometry.header.stamp.nanosec * 1e-9),
        })
        if elapsed >= end_s and not self.done:
            self.done = True
            horizontal_limit = (
                math.hypot(self.square_path_side_m,
                           self.square_path_side_m) + 0.08
                if self.square_path_side_m else 0.25
            )
            result = analyze(
                self.samples, self.saturated_updates, self.parameters,
                self.body_heading_deg, horizontal_limit,
            )
            if self.initial_yaw_deg:
                result = check_yaw_recovery(result, self.initial_yaw_deg)
            if self.yaw_pulse_nm:
                result = check_yaw_pulse(result, self.yaw_pulse_nm)
            if self.position_pulse_x_m or self.position_pulse_y_m:
                result = check_position_pulse(
                    result, self.position_pulse_x_m, self.position_pulse_y_m,
                )
            if self.body_forward_pulse_m:
                result = check_body_forward_pulse(
                    result, self.body_forward_pulse_m, self.body_heading_deg,
                )
            if self.square_path_side_m:
                result = check_square_path(
                    result, self.square_path_side_m, self.body_heading_deg,
                )
            self._finish(result)

    def _finish(self, result: dict) -> None:
        self.done = True
        self.result = result
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(
            f"Gazebo motor-level scenario: {result['scenario_result']}; "
            f"reason: {result.get('abort_reason', 'completed')}; "
            'flight: UNDETERMINED',
            flush=True,
        )
        rclpy.shutdown()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Validate experiment combinations before any Gazebo or ROS side effects."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reset-world', action='store_true',
                        help='Reset the isolated arachne_flight simulation before running')
    parser.add_argument('--initial-yaw-deg', type=float, default=0.0,
                        help='Initial heading error in [-8, 8] degrees; requires --reset-world')
    parser.add_argument('--yaw-pulse-nm', type=float, default=0.0,
                        help='Motor yaw-command pulse at 4.0-4.3 s; max absolute 0.01 Nm')
    parser.add_argument('--position-pulse-x-m', type=float, default=0.0,
                        help='World +X/-X target at 4.0-4.6 s; max absolute 0.20 m')
    parser.add_argument('--position-pulse-y-m', type=float, default=0.0,
                        help='World +Y/-Y target at 4.0-4.6 s; max absolute 0.20 m')
    parser.add_argument('--body-forward-pulse-m', type=float, default=0.0,
                        help='Body forward/back target at 4.0-4.6 s; max absolute 0.20 m')
    parser.add_argument('--body-heading-deg', type=float, default=0.0,
                        help='Held heading for body-forward or square mode; [-180, 180]')
    parser.add_argument('--square-path-side-m', type=float, default=0.0,
                        help='World +X/+Y/-X/-Y square side; within (0, 0.15] m')
    args = parser.parse_args(argv)
    position_values = (args.position_pulse_x_m, args.position_pulse_y_m)
    if any(not math.isfinite(value) or abs(value) > 0.20
           for value in position_values):
        parser.error('position pulses must be finite and within [-0.20, 0.20] m')
    if all(position_values):
        parser.error('only one position pulse axis may be nonzero')
    if any(position_values) and (not args.reset_world or args.initial_yaw_deg or
                                 args.yaw_pulse_nm):
        parser.error('position pulse requires --reset-world, zero initial yaw, and zero yaw pulse')
    if (not math.isfinite(args.body_forward_pulse_m) or
            abs(args.body_forward_pulse_m) > 0.20):
        parser.error('--body-forward-pulse-m must be finite and within [-0.20, 0.20]')
    if (not math.isfinite(args.body_heading_deg) or
            abs(args.body_heading_deg) > 180):
        parser.error('--body-heading-deg must be finite and within [-180, 180]')
    if args.body_heading_deg and not (
            args.body_forward_pulse_m or args.square_path_side_m):
        parser.error('--body-heading-deg requires body-forward or square mode')
    if args.body_forward_pulse_m and (
            not args.reset_world or args.initial_yaw_deg or args.yaw_pulse_nm or
            any(position_values)):
        parser.error(
            'body-forward pulse requires --reset-world and cannot combine '
            'with other pulse modes'
        )
    if (not math.isfinite(args.square_path_side_m) or
            args.square_path_side_m < 0 or args.square_path_side_m > 0.15):
        parser.error('--square-path-side-m must be finite and within (0, 0.15] when used')
    if args.square_path_side_m and (
            not args.reset_world or args.initial_yaw_deg or args.yaw_pulse_nm or
            any(position_values) or args.body_forward_pulse_m):
        parser.error(
            'square path requires --reset-world and cannot combine with '
            'other experiment modes'
        )
    if not math.isfinite(args.yaw_pulse_nm) or abs(args.yaw_pulse_nm) > 0.01:
        parser.error('--yaw-pulse-nm must be finite and within [-0.01, 0.01]')
    if args.yaw_pulse_nm and (not args.reset_world or args.initial_yaw_deg):
        parser.error('--yaw-pulse-nm requires --reset-world and zero initial yaw')
    if not math.isfinite(args.initial_yaw_deg) or abs(args.initial_yaw_deg) > 8:
        parser.error('--initial-yaw-deg must be finite and between -8 and 8')
    if args.initial_yaw_deg and not args.reset_world:
        parser.error('--initial-yaw-deg requires --reset-world')
    return args


def main() -> int:
    args = parse_args()
    if args.reset_world:
        response = subprocess.run([
            'gz', 'service', '-s', '/world/arachne_flight/control',
            '--reqtype', 'gz.msgs.WorldControl', '--reptype', 'gz.msgs.Boolean',
            '--timeout', '3000', '--req', 'reset: {all: true}, pause: false',
        ], capture_output=True, text=True, timeout=5, check=True)
        if 'data: true' not in response.stdout:
            raise RuntimeError('Gazebo did not acknowledge world reset')
        time.sleep(1.0)  # Allow the spawn height to settle before subscribing.
    pose_yaw_deg = (
        args.body_heading_deg if (args.body_forward_pulse_m or args.square_path_side_m)
        else args.initial_yaw_deg
    )
    if pose_yaw_deg:
        half = math.radians(pose_yaw_deg) / 2
        pose = ('name: "arachne_flight_hex", position: {x: 0, y: 0, z: 0.02}, '
                f'orientation: {{x: 0, y: 0, z: {math.sin(half)}, w: {math.cos(half)}}}')
        response = subprocess.run([
            'gz', 'service', '-s', '/world/arachne_flight/set_pose',
            '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
            '--timeout', '3000', '--req', pose,
        ], capture_output=True, text=True, timeout=5, check=True)
        if 'data: true' not in response.stdout:
            raise RuntimeError('Gazebo did not acknowledge initial yaw injection')
    rclpy.init()
    node = MotorScenario(
        args.output, args.initial_yaw_deg, args.yaw_pulse_nm,
        args.position_pulse_x_m, args.position_pulse_y_m,
        args.body_forward_pulse_m, args.body_heading_deg,
        args.square_path_side_m,
    )
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    result = node.result or {'scenario_result': 'FAIL'}
    return 0 if result['scenario_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
