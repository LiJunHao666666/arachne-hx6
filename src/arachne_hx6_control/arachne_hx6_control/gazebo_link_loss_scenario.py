"""Gazebo command-dropout and controlled-landing acceptance scenario."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from geometry_msgs.msg import Twist

from nav_msgs.msg import Odometry

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, String

from .flight_evidence_contract import result_header

LINK_LOSS_START_S = 6.0
SCENARIO_ID = 'gazebo-command-dropout-landing'
SCENARIO_VERSION = '1'


def command_for(elapsed_s: float) -> tuple[float | None, str]:
    """Return requested vertical speed; None represents command dropout."""
    if elapsed_s < 4.0:
        return 0.35, 'TAKEOFF'
    if elapsed_s < LINK_LOSS_START_S:
        return 0.0, 'HOVER'
    return None, 'LINK_LOSS'


def _state_path(events: list[dict]) -> list[str]:
    path = []
    for event in events:
        state = event['state']
        if not path or state != path[-1]:
            path.append(state)
    return path


def analyze(samples: list[dict], state_events: list[dict]) -> dict:
    """Evaluate the planning-only command-dropout scenario."""
    if not samples:
        return {
            **result_header(
                SCENARIO_ID, SCENARIO_VERSION, guarded=True,
            ),
            'scenario_result': 'FAIL',
            'reason': 'no_odometry',
        }
    altitudes = [sample['z_m'] for sample in samples]
    horizontal = max(
        math.hypot(sample['x_m'], sample['y_m'])
        for sample in samples
    )
    failsafe_events = [
        event for event in state_events
        if event['state'] == 'AIRBORNE_FAILSAFE'
    ]
    locked = any(
        event['state'] == 'LANDED_LOCKED'
        for event in state_events
    )
    delay = (
        failsafe_events[0]['elapsed_s'] - LINK_LOSS_START_S
        if failsafe_events else None
    )
    metrics = {
        'sample_count': len(samples),
        'initial_altitude_m': altitudes[0],
        'max_altitude_m': max(altitudes),
        'final_altitude_m': altitudes[-1],
        'failsafe_trigger_delay_s': delay,
        'landed_locked_observed': locked,
        'max_horizontal_displacement_m': horizontal,
        'state_path': _state_path(state_events),
    }
    passed = (
        metrics['sample_count'] >= 20
        and metrics['max_altitude_m'] >= 0.6
        and delay is not None
        and 0.2 <= delay <= 0.8
        and locked
        and metrics['final_altitude_m'] <= 0.12
        and horizontal <= 0.1
    )
    return {
        **result_header(
            SCENARIO_ID, SCENARIO_VERSION, guarded=True,
        ),
        'fault': 'SIMULATED_COMMAND_DROPOUT',
        'criteria': {
            'minimum_max_altitude_m': 0.6,
            'minimum_failsafe_delay_s': 0.2,
            'maximum_failsafe_delay_s': 0.8,
            'landed_locked_required': True,
            'maximum_final_altitude_m': 0.12,
            'maximum_horizontal_displacement_m': 0.1,
        },
        'metrics': metrics,
        'scenario_result': 'PASS' if passed else 'FAIL',
        'limitations': [
            'Command dropout is injected in a Gazebo planning model',
            'The guard is not a selected or validated flight controller',
            'A simulation pass does not establish physical flight safety',
        ],
    }


class LinkLossScenario(Node):
    """Publish requests, stop them in flight, and record the guard response."""

    def __init__(self, output: Path) -> None:
        super().__init__('gazebo_link_loss_scenario')
        self.output = output
        self.start = time.monotonic()
        self.samples: list[dict] = []
        self.state_events: list[dict] = []
        self.current_state = 'UNKNOWN'
        self.done = False
        self.command_publisher = self.create_publisher(
            Twist, '/arachne_hx6/request/twist', 10,
        )
        self.enable_publisher = self.create_publisher(
            Bool, '/arachne_hx6/request/enable', 10,
        )
        self.reset_publisher = self.create_publisher(
            Bool, '/arachne_hx6/request/reset_failsafe', 10,
        )
        self.create_subscription(
            Odometry,
            '/model/arachne_flight_hex/odometry',
            self._odometry_callback,
            10,
        )
        self.create_subscription(
            String,
            '/arachne_hx6/failsafe/state',
            self._state_callback,
            10,
        )
        self.create_timer(0.05, self._step)

    def _elapsed(self) -> float:
        return time.monotonic() - self.start

    def _state_callback(self, message: String) -> None:
        try:
            state = json.loads(message.data)['state']
        except (KeyError, TypeError, json.JSONDecodeError):
            return
        if state != self.current_state:
            self.current_state = state
            self.state_events.append({
                'elapsed_s': self._elapsed(),
                'state': state,
            })

    def _odometry_callback(self, message: Odometry) -> None:
        elapsed = self._elapsed()
        _, phase = command_for(elapsed)
        position = message.pose.pose.position
        self.samples.append({
            'elapsed_s': elapsed,
            'phase': phase,
            'guard_state': self.current_state,
            'x_m': position.x,
            'y_m': position.y,
            'z_m': position.z,
        })

    def _publish_reset(self) -> None:
        message = Bool()
        message.data = True
        self.reset_publisher.publish(message)

    def _publish_request(self, vertical_speed: float) -> None:
        enabled = Bool()
        enabled.data = True
        self.enable_publisher.publish(enabled)
        command = Twist()
        command.linear.z = vertical_speed
        self.command_publisher.publish(command)

    def _step(self) -> None:
        elapsed = self._elapsed()
        speed, _ = command_for(elapsed)
        if elapsed < 0.5:
            self._publish_reset()
        if speed is not None:
            self._publish_request(speed)
        if elapsed >= 14.0 and not self.done:
            self.done = True
            result = analyze(self.samples, self.state_events)
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(
                json.dumps(result, indent=2, allow_nan=False) + '\n',
            )
            print(
                'Gazebo link-loss scenario: '
                f"{result['scenario_result']}; flight: UNDETERMINED",
                flush=True,
            )
            rclpy.shutdown()


def main() -> int:
    """Run the link-loss scenario and return its acceptance status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    rclpy.init()
    node = LinkLossScenario(arguments.output)
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
