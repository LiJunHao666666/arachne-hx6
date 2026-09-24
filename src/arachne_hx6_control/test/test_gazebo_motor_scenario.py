"""Motor-level Gazebo control contracts for the planning model."""

import math
from pathlib import Path
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from arachne_hx6_control.gazebo_motor_scenario import (
    MotorParameters, allocate_wrench, motor_speeds, reference, square_waypoint,
)


def test_reference_has_takeoff_hover_landing_and_disarm():
    assert reference(1)[2] == 'TAKEOFF'
    assert reference(4)[2] == 'HOVER'
    assert reference(7)[2] == 'LAND'
    assert reference(10)[2] == 'DISARMED'


def test_extended_reference_holds_hover_before_delayed_landing():
    assert reference(8.8, 9.5)[2] == 'HOVER'
    assert reference(10.0, 9.5)[2] == 'LAND'
    assert reference(12.6, 9.5)[2] == 'DISARMED'


def test_square_waypoint_visits_four_clockwise_targets_and_origin():
    side = 0.15
    assert square_waypoint(3.9, side) == (0.0, 0.0, 'ORIGIN')
    assert square_waypoint(4.0, side) == (side, 0.0, 'FORWARD')
    assert square_waypoint(5.2, side) == (side, side, 'LEFT')
    assert square_waypoint(6.4, side) == (0.0, side, 'BACKWARD')
    assert square_waypoint(7.6, side) == (0.0, 0.0, 'RIGHT_TO_ORIGIN')
    assert square_waypoint(8.8, side) == (0.0, 0.0, 'ORIGIN')


def test_hover_allocation_has_six_bounded_equal_motor_commands():
    p = MotorParameters()
    speeds, saturated = allocate_wrench(p.mass_kg * p.gravity_m_s2, 0, 0, 0)
    assert len(speeds) == 6 and saturated == 0
    assert max(speeds) - min(speeds) < 1e-9
    assert all(0 < speed <= math.sqrt(p.max_thrust_per_rotor_n / p.motor_constant_n_per_rad_s2)
               for speed in speeds)


def test_motor_command_disarms_and_responds_to_roll_error():
    zero = SimpleNamespace(x=0.0, y=0.0, z=0.0)
    orientation = SimpleNamespace(w=math.cos(0.1), x=math.sin(0.1), y=0.0, z=0.0)
    odometry = SimpleNamespace(
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=0.5),
            orientation=orientation,
        )),
        twist=SimpleNamespace(twist=SimpleNamespace(linear=zero, angular=zero)),
    )
    active, phase, _ = motor_speeds(odometry, 4.0)
    assert phase == 'HOVER' and len(set(round(v, 6) for v in active)) > 1
    stopped, phase, _ = motor_speeds(odometry, 10.0)
    assert phase == 'DISARMED' and stopped == [0.0] * 6


def test_position_targets_generate_expected_body_torques():
    zero = SimpleNamespace(x=0.0, y=0.0, z=0.0)
    odometry = SimpleNamespace(
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=1.22),
            orientation=SimpleNamespace(w=1.0, x=0.0, y=0.0, z=0.0),
        )),
        twist=SimpleNamespace(twist=SimpleNamespace(linear=zero, angular=zero)),
    )
    p = MotorParameters()
    positions = [(p.arm_m * math.cos(math.radians(30 + 60 * i)),
                  p.arm_m * math.sin(math.radians(30 + 60 * i)))
                 for i in range(6)]
    forward, _, _ = motor_speeds(odometry, 4.1, target_x_m=0.15)
    left, _, _ = motor_speeds(odometry, 4.1, target_y_m=0.15)
    forward_thrust = [p.motor_constant_n_per_rad_s2 * speed**2 for speed in forward]
    left_thrust = [p.motor_constant_n_per_rad_s2 * speed**2 for speed in left]
    assert sum(-x * thrust for (x, _), thrust in zip(positions, forward_thrust)) > 0
    assert sum(y * thrust for (_, y), thrust in zip(positions, left_thrust)) < 0


def test_target_heading_holds_rotated_body_without_extra_yaw_torque():
    zero = SimpleNamespace(x=0.0, y=0.0, z=0.0)
    half = math.radians(45) / 2
    odometry = SimpleNamespace(
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=1.22),
            orientation=SimpleNamespace(
                w=math.cos(half), x=0.0, y=0.0, z=math.sin(half),
            ),
        )),
        twist=SimpleNamespace(twist=SimpleNamespace(linear=zero, angular=zero)),
    )
    held, _, _ = motor_speeds(
        odometry, 4.0, target_yaw_rad=math.radians(45),
    )
    recovering, _, _ = motor_speeds(odometry, 4.0)
    assert max(held) - min(held) < 1e-9
    assert max(recovering) - min(recovering) > 1e-6


def test_rotated_heading_converts_world_diagonal_to_body_forward_torque():
    zero = SimpleNamespace(x=0.0, y=0.0, z=0.0)
    half = math.radians(45) / 2
    odometry = SimpleNamespace(
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=0.0, y=0.0, z=1.22),
            orientation=SimpleNamespace(
                w=math.cos(half), x=0.0, y=0.0, z=math.sin(half),
            ),
        )),
        twist=SimpleNamespace(twist=SimpleNamespace(linear=zero, angular=zero)),
    )
    p = MotorParameters()
    speeds, _, _ = motor_speeds(
        odometry, 4.1, target_x_m=0.15 / math.sqrt(2),
        target_y_m=0.15 / math.sqrt(2), target_yaw_rad=math.radians(45),
    )
    positions = [
        (p.arm_m * math.cos(math.radians(30 + 60 * i)),
         p.arm_m * math.sin(math.radians(30 + 60 * i)))
        for i in range(6)
    ]
    thrusts = [p.motor_constant_n_per_rad_s2 * speed**2 for speed in speeds]
    roll_torque = sum(y * thrust for (_, y), thrust in zip(positions, thrusts))
    pitch_torque = sum(-x * thrust for (x, _), thrust in zip(positions, thrusts))
    assert abs(roll_torque) < 1e-10
    assert pitch_torque > 0

def test_controller_assumptions_match_gazebo_motor_model():
    p = MotorParameters()
    world = Path(__file__).resolve().parents[3] / 'src/arachne_hx6_simulation/worlds/flight_hex_motor.sdf'
    model = ET.parse(world).getroot().find("world/model[@name='arachne_flight_hex']")
    body_mass = float(model.find("link[@name='base_link']/inertial/mass").text)
    rotor_mass = sum(float(model.find(f"link[@name='rotor_{i}']/inertial/mass").text)
                     for i in range(6))
    assert math.isclose(body_mass + rotor_mass, p.mass_kg)
    motors = [plugin for plugin in model.findall('plugin')
              if 'MotorModel' in plugin.get('name', '')]
    assert len(motors) == 6
    assert all(math.isclose(float(motor.findtext('motorConstant')),
                            p.motor_constant_n_per_rad_s2)
               and math.isclose(float(motor.findtext('momentConstant')),
                                p.moment_constant_m)
               and math.isclose(float(motor.findtext('timeConstantUp')),
                                p.motor_time_constant_s)
               for motor in motors)

def test_phase_diagnostics_distinguish_motor_counts_from_control_updates():
    from arachne_hx6_control.gazebo_motor_scenario import summarize_phases
    def row(phase, count, yaw):
        return dict(phase=phase, saturated_motors=count, yaw_deg=yaw,
                    yaw_rate_rad_s=-2.0, requested_yaw_torque_nm=0.1)
    result = summarize_phases([row('HOVER', 6, -170), row('HOVER', 0, 10),
                               row('LAND', 3, 20)])
    assert result['HOVER']['limited_motor_count'] == 6
    assert result['HOVER']['updates_with_any_limit'] == 1
    assert result['HOVER']['limited_motor_fraction'] == 0.5
    assert result['HOVER']['peak_abs_yaw_deg'] == 170
    assert result['LAND']['sample_count'] == 1
    assert 'TAKEOFF' not in result
    assert summarize_phases([]) == {}


def test_allocation_reconstructs_gazebo_reaction_torque():
    p = MotorParameters()
    for yaw in (-0.02, 0.02):
        speeds, saturated = allocate_wrench(p.mass_kg * p.gravity_m_s2, 0, 0, yaw)
        thrusts = [p.motor_constant_n_per_rad_s2 * v*v for v in speeds]
        world = Path(__file__).resolve().parents[3] / 'src/arachne_hx6_simulation/worlds/flight_hex_motor.sdf'
        plugins = ET.parse(world).getroot().find("world/model[@name='arachne_flight_hex']").findall('plugin')
        actual = 0.0
        for motor in plugins:
            index = motor.findtext('actuator_number')
            if index is None:
                continue
            direction = 1 if motor.findtext('turningDirection') == 'ccw' else -1
            actual += -direction * thrusts[int(index)] * float(motor.findtext('momentConstant'))
        assert saturated == 0
        assert math.isclose(actual, yaw, abs_tol=1e-10)


def test_acceptance_rejects_yaw_spin_despite_good_height():
    from arachne_hx6_control.gazebo_motor_scenario import analyze
    samples = []
    for phase, elapsed, z in [('SETTLE', 0.1, 0.02), ('TAKEOFF', 2, 0.7),
                              ('HOVER', 5, 1.22), ('LAND', 8, 0.3), ('DISARMED', 10, 0.02)]:
        for _ in range(12):
            samples.append(dict(phase=phase, elapsed_s=elapsed, z_m=z, x_m=0, y_m=0,
                                tilt_deg=0, yaw_deg=0, yaw_rate_rad_s=0,
                                requested_yaw_torque_nm=0, saturated_motors=0))
    assert analyze(samples, 0)['scenario_result'] == 'PASS'
    samples[20]['yaw_deg'] = 170
    assert analyze(samples, 0)['scenario_result'] == 'FAIL'
    samples[20]['yaw_deg'] = 0
    assert analyze(samples, 300)['scenario_result'] == 'FAIL'


def test_yaw_recovery_requires_injection_and_convergence():
    from arachne_hx6_control.gazebo_motor_scenario import check_yaw_recovery
    def evidence(initial, final):
        return dict(scenario_result='PASS', acceptance_checks={'base': True}, samples=[
            dict(yaw_deg=initial, phase='SETTLE', elapsed_s=0),
            dict(yaw_deg=final, phase='HOVER', elapsed_s=5)])
    assert check_yaw_recovery(evidence(5, 0.2), 5)['scenario_result'] == 'PASS'
    assert check_yaw_recovery(evidence(-5, -0.2), -5)['scenario_result'] == 'PASS'
    assert check_yaw_recovery(evidence(0, 0), 5)['scenario_result'] == 'FAIL'
    assert check_yaw_recovery(evidence(5, 4), 5)['scenario_result'] == 'FAIL'


def test_feedback_watchdog_missing_stale_duplicate_and_reversed_time():
    from arachne_hx6_control.gazebo_motor_scenario import FeedbackWatchdog
    w = FeedbackWatchdog(0)
    assert w.check(4.9) is None
    assert w.check(5) == 'no_odometry'
    assert not w.observe(100, 5.1)  # Failure stays latched.
    w = FeedbackWatchdog(0)
    assert w.observe(100, 1)
    assert not w.observe(100, 1.2)  # Replayed timestamp cannot feed watchdog.
    assert w.check(1.29) is None
    assert w.check(1.31) == 'odometry_stale_or_sim_paused'
    w = FeedbackWatchdog(0)
    assert w.observe(100, 1)
    assert w.observe(101, 1.2)
    assert w.check(1.4) is None
    assert not w.observe(99, 1.41)
    assert w.check(1.42) == 'odometry_time_reversed'


def test_pulse_acceptance_requires_signed_response_and_recovery():
    from arachne_hx6_control.gazebo_motor_scenario import check_yaw_pulse
    def evidence(sign=1, recovery=0.2, injected=True):
        rows = [dict(elapsed_s=4.01+i*0.02, yaw_deg=sign*0.4,
                     injected_yaw_command_nm=sign*0.01 if injected else 0) for i in range(12)]
        rows += [dict(elapsed_s=5.51+i*0.02, yaw_deg=recovery,
                      injected_yaw_command_nm=0) for i in range(12)]
        return dict(samples=rows, acceptance_checks={'base': True}, scenario_result='PASS')
    assert check_yaw_pulse(evidence(), 0.01)['scenario_result'] == 'PASS'
    assert check_yaw_pulse(evidence(-1), -0.01)['scenario_result'] == 'PASS'
    assert check_yaw_pulse(evidence(-1), 0.01)['scenario_result'] == 'FAIL'
    assert check_yaw_pulse(evidence(recovery=3), 0.01)['scenario_result'] == 'FAIL'
    assert check_yaw_pulse(evidence(injected=False), 0.01)['scenario_result'] == 'FAIL'


def test_position_pulse_acceptance_checks_direction_cross_axis_and_recovery():
    from arachne_hx6_control.gazebo_motor_scenario import check_position_pulse

    def evidence(axis='x', request_sign=1, response_sign=None, cross=0.01, recovery=0.02):
        if response_sign is None:
            response_sign = request_sign
        rows = []
        for index in range(30):
            elapsed = 4.01 + index * 0.02
            fraction = min(1.0, index / 15)
            rows.append(
                {
                    'elapsed_s': elapsed,
                    'x_m': response_sign * 0.05 * fraction if axis == 'x' else cross,
                    'y_m': response_sign * 0.05 * fraction if axis == 'y' else cross,
                    'yaw_deg': 0.2,
                    'requested_position_x_m': request_sign * 0.15 if axis == 'x' else 0.0,
                    'requested_position_y_m': request_sign * 0.15 if axis == 'y' else 0.0,
                }
            )
        rows.extend(
            {
                'elapsed_s': 5.51 + index * 0.02,
                'x_m': recovery if axis == 'x' else cross,
                'y_m': recovery if axis == 'y' else cross,
                'yaw_deg': 0.1,
                'requested_position_x_m': 0.0,
                'requested_position_y_m': 0.0,
            }
            for index in range(12)
        )
        return {
            'samples': rows,
            'acceptance_checks': {'base': True},
            'scenario_result': 'PASS',
        }

    for axis in ('x', 'y'):
        for request_sign in (-1, 1):
            result = check_position_pulse(
                evidence(axis, request_sign),
                request_sign * 0.15 if axis == 'x' else 0.0,
                request_sign * 0.15 if axis == 'y' else 0.0,
            )
            assert result['scenario_result'] == 'PASS'

    wrong_direction = check_position_pulse(evidence('x', 1, response_sign=-1), 0.15, 0.0)
    excessive_cross_axis = check_position_pulse(evidence('x', 1, cross=0.08), 0.15, 0.0)
    poor_recovery = check_position_pulse(evidence('x', 1, recovery=0.10), 0.15, 0.0)

    assert wrong_direction['scenario_result'] == 'FAIL'
    assert excessive_cross_axis['scenario_result'] == 'FAIL'
    assert poor_recovery['scenario_result'] == 'FAIL'


def test_body_forward_acceptance_projects_rotated_world_trajectory():
    from arachne_hx6_control.gazebo_motor_scenario import check_body_forward_pulse

    def evidence(heading_deg=45, request=0.15, cross=0.01,
                 recovery=0.02, observed_heading=None):
        heading = math.radians(heading_deg)
        if observed_heading is None:
            observed_heading = heading_deg
        rows = [{
            'elapsed_s': 0.0,
            'x_m': 0.0,
            'y_m': 0.0,
            'yaw_deg': observed_heading,
            'requested_body_forward_m': 0.0,
        }]
        direction = 1 if request > 0 else -1
        for index in range(30):
            elapsed = 4.01 + index * 0.02
            along = direction * 0.05 * min(1.0, index / 15)
            rows.append({
                'elapsed_s': elapsed,
                'x_m': along * math.cos(heading) - cross * math.sin(heading),
                'y_m': along * math.sin(heading) + cross * math.cos(heading),
                'yaw_deg': heading_deg + 0.2,
                'requested_body_forward_m': request,
            })
        rows.extend({
            'elapsed_s': 5.51 + index * 0.02,
            'x_m': recovery * math.cos(heading),
            'y_m': recovery * math.sin(heading),
            'yaw_deg': heading_deg + 0.1,
            'requested_body_forward_m': 0.0,
        } for index in range(12))
        return {
            'samples': rows,
            'acceptance_checks': {'base': True},
            'scenario_result': 'PASS',
        }

    for heading_deg in (-45, 45):
        for request in (-0.15, 0.15):
            result = check_body_forward_pulse(
                evidence(heading_deg, request), request, heading_deg,
            )
            assert result['scenario_result'] == 'PASS'

    cross_fail = check_body_forward_pulse(
        evidence(cross=0.08), 0.15, 45,
    )
    heading_fail = check_body_forward_pulse(
        evidence(observed_heading=0), 0.15, 45,
    )
    assert cross_fail['scenario_result'] == 'FAIL'
    assert heading_fail['scenario_result'] == 'FAIL'


def test_square_path_acceptance_requires_every_commanded_waypoint():
    from arachne_hx6_control.gazebo_motor_scenario import check_square_path

    side = 0.15
    legs = [
        ('FORWARD', 4.0, side, 0.0),
        ('LEFT', 5.2, side, side),
        ('BACKWARD', 6.4, 0.0, side),
        ('RIGHT_TO_ORIGIN', 7.6, 0.0, 0.0),
    ]

    def evidence(bad_leg=None, wrong_command=False):
        rows = []
        for name, start, target_x, target_y in legs:
            for index in range(60):
                offset = 0.10 if name == bad_leg else 0.0
                rows.append({
                    'elapsed_s': start + index * 0.02,
                    'x_m': target_x + offset,
                    'y_m': target_y,
                    'yaw_deg': 0.2,
                    'requested_position_x_m': target_x,
                    'requested_position_y_m': target_y,
                    'requested_path_leg': (
                        'WRONG' if wrong_command and name == 'LEFT' else name
                    ),
                })
        return {
            'samples': rows,
            'acceptance_checks': {'base': True},
            'scenario_result': 'PASS',
        }

    assert check_square_path(evidence(), side)['scenario_result'] == 'PASS'
    assert check_square_path(
        evidence(bad_leg='LEFT'), side,
    )['scenario_result'] == 'FAIL'
    assert check_square_path(
        evidence(wrong_command=True), side,
    )['scenario_result'] == 'FAIL'
