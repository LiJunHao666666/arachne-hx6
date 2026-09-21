"""Gazebo takeoff-hover-land scenario for the isolated flight hex."""

import argparse
import json
import math
from pathlib import Path
import time

from geometry_msgs.msg import Twist

from nav_msgs.msg import Odometry

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool


def command_for(elapsed_s):
    """Return vertical speed and phase for the nominal flight schedule."""
    if elapsed_s < 4:
        return 0.35, 'TAKEOFF'
    if elapsed_s < 7:
        return 0.0, 'HOVER'
    if elapsed_s < 12:
        return -0.25, 'LAND'
    return 0.0, 'DISARMED'


def analyze(samples):
    """Evaluate nominal takeoff, hover, and landing samples."""
    if not samples:
        return {
            'scenario_result': 'FAIL',
            'reason': 'no_odometry',
        }
    altitudes = [sample['z_m'] for sample in samples]
    hover = [
        sample['z_m']
        for sample in samples
        if sample['phase'] == 'HOVER'
    ]
    horizontal = max(
        math.hypot(sample['x_m'], sample['y_m'])
        for sample in samples
    )
    metrics = {
        'sample_count': len(samples),
        'initial_altitude_m': altitudes[0],
        'max_altitude_m': max(altitudes),
        'final_altitude_m': altitudes[-1],
        'hover_span_m': max(hover) - min(hover) if hover else None,
        'max_horizontal_displacement_m': horizontal,
    }
    passed = (
        metrics['sample_count'] >= 20
        and metrics['max_altitude_m'] >= 0.6
        and metrics['final_altitude_m'] <= 0.2
        and metrics['hover_span_m'] is not None
        and metrics['hover_span_m'] <= 0.15
        and horizontal <= 0.1
    )
    return {
        'schema_version': 1,
        'status': 'ANALYSIS_ONLY',
        'procurement_allowed': False,
        'flight_readiness': 'UNDETERMINED',
        'scope': 'GAZEBO_PLANNING_MODEL',
        'parameter_evidence': 'PLANNING_ASSUMPTION',
        'criteria': {
            'minimum_max_altitude_m': 0.6,
            'maximum_final_altitude_m': 0.2,
            'maximum_hover_span_m': 0.15,
            'maximum_horizontal_displacement_m': 0.1,
        },
        'metrics': metrics,
        'scenario_result': 'PASS' if passed else 'FAIL',
        'limitations': [
            'Gazebo parameters are not measured hardware data',
            'Velocity plugin is not a selected flight controller',
            'Simulation pass does not prove physical flight readiness',
        ],
    }


class Scenario(Node):
    """Publish the nominal flight schedule and record Gazebo odometry."""

    def __init__(self, output):
        super().__init__('gazebo_flight_scenario')
        self.output = output
        self.start = time.monotonic()
        self.samples = []
        self.done = False
        self.command_publisher = self.create_publisher(
            Twist, '/arachne_hx6/command/twist', 10,
        )
        self.enable_publisher = self.create_publisher(
            Bool, '/arachne_hx6/enable', 10,
        )
        self.create_subscription(
            Odometry,
            '/model/arachne_flight_hex/odometry',
            self._odometry_callback,
            10,
        )
        self.create_timer(0.05, self._step)

    def _elapsed(self):
        return time.monotonic() - self.start

    def _odometry_callback(self, message):
        elapsed = self._elapsed()
        _, phase = command_for(elapsed)
        position = message.pose.pose.position
        self.samples.append({
            'elapsed_s': elapsed,
            'phase': phase,
            'x_m': position.x,
            'y_m': position.y,
            'z_m': position.z,
        })

    def _step(self):
        elapsed = self._elapsed()
        speed, phase = command_for(elapsed)
        enabled = Bool()
        enabled.data = phase != 'DISARMED'
        self.enable_publisher.publish(enabled)
        command = Twist()
        command.linear.z = speed
        self.command_publisher.publish(command)
        if elapsed >= 13 and not self.done:
            self.done = True
            result = analyze(self.samples)
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(
                json.dumps(result, indent=2, allow_nan=False) + '\n',
            )
            print(
                'Gazebo flight scenario: '
                f"{result['scenario_result']}; flight: UNDETERMINED",
                flush=True,
            )
            rclpy.shutdown()


def main():
    """Run the nominal Gazebo flight scenario."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    rclpy.init()
    node = Scenario(arguments.output)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    result = (
        json.loads(arguments.output.read_text())
        if arguments.output.exists()
        else {'scenario_result': 'FAIL'}
    )
    return 0 if result['scenario_result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
