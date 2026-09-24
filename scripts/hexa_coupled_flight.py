#!/usr/bin/env python3
"""Coupled small-angle six-rotor flight exercise with a hover disturbance."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

from hexa_attitude_flight import allocation_matrix, matvec, pseudoinverse


@dataclass(frozen=True)
class Parameters:
    """All values are planning assumptions, not measured hardware data."""

    mass_kg: float = 0.65
    gravity_m_s2: float = 9.80665
    arm_m: float = 0.12
    yaw_torque_per_thrust_m: float = 0.015
    inertia_x_kg_m2: float = 0.004
    inertia_y_kg_m2: float = 0.004
    inertia_z_kg_m2: float = 0.007
    max_thrust_per_rotor_n: float = 2.0
    motor_tau_s: float = 0.08
    dt_s: float = 0.01
    duration_s: float = 10.0
    disturbance_acceleration_m_s2: float = 0.8


def validate(p: Parameters) -> None:
    """Reject malformed or insufficient-thrust planning configurations."""
    for name, value in asdict(p).items():
        if isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f'{name} must be finite')
        if name == 'disturbance_acceleration_m_s2':
            if value < 0:
                raise ValueError(f'{name} must be nonnegative')
        elif value <= 0:
            raise ValueError(f'{name} must be positive')
    if p.duration_s < 10.0:
        raise ValueError('duration_s must include landing and disarm')
    if p.dt_s > p.motor_tau_s:
        raise ValueError('dt_s must not exceed motor_tau_s')
    if 6 * p.max_thrust_per_rotor_n <= p.mass_kg * p.gravity_m_s2:
        raise ValueError('six-motor thrust must exceed weight')


def reference(t: float) -> tuple[float, float, str]:
    """Return target altitude, climb speed, and phase."""
    if t < 2.0:
        return 0.5 * t, 0.5, 'TAKEOFF'
    if t < 6.0:
        return 1.0, 0.0, 'HOVER'
    if t < 8.0:
        return 1.0 - 0.5 * (t - 6.0), -0.5, 'LAND'
    return 0.0, 0.0, 'DISARMED'


def simulate(p: Parameters = Parameters()) -> dict:
    """Run altitude, lateral position, attitude, and six motor states together."""
    validate(p)
    matrix = allocation_matrix(p)
    inverse = pseudoinverse(matrix)
    xyz = [0.0, 0.0, 0.0]
    velocity = [0.0, 0.0, 0.0]
    angles = [0.0, 0.0, 0.0]
    rates = [0.0, 0.0, 0.0]
    motors = [0.0] * 6
    samples = []
    saturated = 0
    for step in range(round(p.duration_s / p.dt_s) + 1):
        t = step * p.dt_s
        target_z, target_vz, phase = reference(t)
        disturbance = p.disturbance_acceleration_m_s2 if 4.0 <= t < 4.3 else 0.0
        desired_ax = -2.0 * xyz[0] - 2.0 * velocity[0]
        desired_ay = -2.0 * xyz[1] - 2.0 * velocity[1]
        target_roll = max(-0.2, min(0.2, -desired_ay / p.gravity_m_s2))
        target_pitch = max(-0.2, min(0.2, desired_ax / p.gravity_m_s2))
        total_request = (p.mass_kg * p.gravity_m_s2
                         + 7.0 * (target_z - xyz[2])
                         + 4.0 * (target_vz - velocity[2]))
        torques = [
            0.08 * (target_roll - angles[0]) - 0.025 * rates[0],
            0.08 * (target_pitch - angles[1]) - 0.025 * rates[1],
            -0.05 * angles[2] - 0.02 * rates[2],
        ]
        requested = matvec(inverse, [max(0.0, total_request)] + torques)
        if phase == 'DISARMED':
            requested = [0.0] * 6
        commanded = [max(0.0, min(p.max_thrust_per_rotor_n, x))
                     for x in requested]
        saturated += sum(abs(a - b) > 1e-9
                         for a, b in zip(requested, commanded))
        motors = [actual + (desired - actual) * p.dt_s / p.motor_tau_s
                  for actual, desired in zip(motors, commanded)]
        thrust, roll_torque, pitch_torque, yaw_torque = matvec(matrix, motors)
        for axis, torque in enumerate((roll_torque, pitch_torque, yaw_torque)):
            inertia = (p.inertia_x_kg_m2, p.inertia_y_kg_m2,
                       p.inertia_z_kg_m2)[axis]
            rates[axis] += torque / inertia * p.dt_s
            angles[axis] += rates[axis] * p.dt_s
        acceleration = [
            thrust / p.mass_kg * math.sin(angles[1]) + disturbance,
            -thrust / p.mass_kg * math.sin(angles[0]),
            thrust / p.mass_kg * math.cos(angles[0])
            * math.cos(angles[1]) - p.gravity_m_s2,
        ]
        for axis in range(3):
            velocity[axis] += acceleration[axis] * p.dt_s
            xyz[axis] += velocity[axis] * p.dt_s
        if xyz[2] < 0:
            xyz[2] = velocity[2] = 0.0
        samples.append({
            'time_s': t, 'phase': phase, 'position_m': list(xyz),
            'velocity_m_s': list(velocity), 'attitude_rad': list(angles),
            'rotor_thrust_n': list(motors),
            'disturbance_acceleration_m_s2': disturbance,
        })

    hover = [s['position_m'][2] - 1.0 for s in samples
             if 3.0 <= s['time_s'] < 6.0]
    horizontal = lambda s: math.hypot(*s['position_m'][:2])
    recovery = [horizontal(s) for s in samples
                if 5.5 <= s['time_s'] < 6.0]
    metrics = {
        'hover_altitude_rmse_m':
            math.sqrt(sum(e * e for e in hover) / len(hover)),
        'max_altitude_m': max(s['position_m'][2] for s in samples),
        'max_horizontal_displacement_m': max(map(horizontal, samples)),
        'recovery_horizontal_error_m': max(recovery),
        'peak_tilt_deg': math.degrees(max(
            max(abs(s['attitude_rad'][0]), abs(s['attitude_rad'][1]))
            for s in samples)),
        'saturated_channel_steps': saturated,
        'final_altitude_m': xyz[2],
        'final_vertical_speed_m_s': velocity[2],
    }
    criteria = {
        'hover_altitude_rmse_m_max': 0.12,
        'max_altitude_m_max': 1.25,
        'max_horizontal_displacement_m_max': 0.30,
        'recovery_horizontal_error_m_max': 0.10,
        'peak_tilt_deg_max': 12.0,
        'saturated_channel_steps_max': 0,
        'final_altitude_m_max': 0.02,
        'final_vertical_speed_abs_m_s_max': 0.05,
    }
    passed = (metrics['hover_altitude_rmse_m'] <= 0.12
              and metrics['max_altitude_m'] <= 1.25
              and metrics['max_horizontal_displacement_m'] <= 0.30
              and metrics['recovery_horizontal_error_m'] <= 0.10
              and metrics['peak_tilt_deg'] <= 12.0
              and saturated == 0 and xyz[2] <= 0.02
              and abs(velocity[2]) <= 0.05)
    return {
        'schema_version': 1, 'status': 'ANALYSIS_ONLY',
        'procurement_allowed': False, 'flight_readiness': 'UNDETERMINED',
        'scope': 'COUPLED_SMALL_ANGLE_PLANNING_MODEL',
        'parameter_evidence': 'PLANNING_ASSUMPTION',
        'parameters': asdict(p), 'rotor_order': [f'R{i}' for i in range(1, 7)],
        'criteria': criteria, 'metrics': metrics,
        'scenario_result': 'PASS' if passed else 'FAIL',
        'samples': samples,
        'limitations': [
            'Small-angle point-mass translation and simplified attitude dynamics',
            'No estimator, aerodynamics, battery sag, ground effect, or structure',
            'Controller and motor values are unmeasured planning assumptions',
            'Not ArduCopter SITL or evidence of physical flight readiness',
        ],
    }


def main() -> int:
    """Write the deterministic scenario result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = simulate()
    except ValueError as exc:
        parser.error(str(exc))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f"Coupled flight scenario: {result['scenario_result']}; "
          'flight: UNDETERMINED')
    return 0 if result['scenario_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())