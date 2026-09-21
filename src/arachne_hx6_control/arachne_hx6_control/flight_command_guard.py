"""Planning-model command timeout guard for the Gazebo flight hex."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import time

from geometry_msgs.msg import Twist

from nav_msgs.msg import Odometry

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, String


@dataclass(frozen=True)
class MotionCommand:
    """ROS-independent six-axis velocity command."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def is_finite(self) -> bool:
        """Return whether every command component is finite."""
        return all(math.isfinite(value) for value in (
            self.x, self.y, self.z, self.roll, self.pitch, self.yaw,
        ))


@dataclass(frozen=True)
class GuardOutput:
    """One guarded output update."""

    state: str
    reason: str
    enabled: bool
    command: MotionCommand


class GuardLogic:
    """Fail-closed planning logic; not a real flight-controller failsafe."""

    DISARMED = 'DISARMED'
    ACTIVE = 'ACTIVE'
    AIRBORNE_FAILSAFE = 'AIRBORNE_FAILSAFE'
    LANDED_LOCKED = 'LANDED_LOCKED'

    def __init__(
        self,
        timeout_s: float = 0.4,
        descent_speed_mps: float = -0.25,
        landed_altitude_m: float = 0.08,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError('timeout_s must be positive')
        if descent_speed_mps >= 0:
            raise ValueError('descent_speed_mps must be negative')
        if landed_altitude_m < 0:
            raise ValueError('landed_altitude_m must be nonnegative')
        self.timeout_s = timeout_s
        self.descent_speed_mps = descent_speed_mps
        self.landed_altitude_m = landed_altitude_m
        self.state = self.DISARMED
        self.reason = 'INITIAL'
        self.altitude_m = 0.0
        self.last_request_s: float | None = None
        self.requested = MotionCommand()

    def _enter_safe_state(self, reason: str) -> None:
        if self.altitude_m > self.landed_altitude_m:
            self.state = self.AIRBORNE_FAILSAFE
        else:
            self.state = self.LANDED_LOCKED
        self.reason = reason

    def accept(
        self,
        command: MotionCommand,
        enabled: bool,
        now_s: float,
    ) -> bool:
        """Accept a fresh request unless a failsafe latch is active."""
        if not math.isfinite(now_s) or not command.is_finite():
            self._enter_safe_state('INVALID_REQUEST')
            return False
        if self.state in (self.AIRBORNE_FAILSAFE, self.LANDED_LOCKED):
            return False
        self.last_request_s = now_s
        if not enabled:
            if self.altitude_m > self.landed_altitude_m:
                self.state = self.AIRBORNE_FAILSAFE
                self.reason = 'EXPLICIT_DISABLE_AIRBORNE'
            else:
                self.state = self.DISARMED
                self.reason = 'EXPLICIT_DISABLE_GROUND'
            self.requested = MotionCommand()
            return True
        self.requested = command
        self.state = self.ACTIVE
        self.reason = 'FRESH_REQUEST'
        return True

    def reset(self) -> bool:
        """Clear a latch only while the model is at ground altitude."""
        if self.altitude_m > self.landed_altitude_m:
            return False
        self.state = self.DISARMED
        self.reason = 'GROUND_RESET'
        self.last_request_s = None
        self.requested = MotionCommand()
        return True

    def tick(self, now_s: float, altitude_m: float) -> GuardOutput:
        """Advance the state and return the command for this update."""
        if not math.isfinite(now_s) or not math.isfinite(altitude_m):
            self._enter_safe_state('INVALID_FEEDBACK')
        else:
            self.altitude_m = max(0.0, altitude_m)
            if self.state == self.ACTIVE:
                stale = (
                    self.last_request_s is None
                    or now_s - self.last_request_s > self.timeout_s
                )
                if stale:
                    self._enter_safe_state('COMMAND_TIMEOUT')
            if (
                self.state == self.AIRBORNE_FAILSAFE
                and self.altitude_m <= self.landed_altitude_m
            ):
                self.state = self.LANDED_LOCKED
                self.reason = 'LANDED_AFTER_FAILSAFE'

        if self.state == self.ACTIVE:
            return GuardOutput(
                self.state, self.reason, True, self.requested,
            )
        if self.state == self.AIRBORNE_FAILSAFE:
            return GuardOutput(
                self.state,
                self.reason,
                True,
                MotionCommand(z=self.descent_speed_mps),
            )
        return GuardOutput(
            self.state, self.reason, False, MotionCommand(),
        )


def _from_twist(message: Twist) -> MotionCommand:
    return MotionCommand(
        x=message.linear.x,
        y=message.linear.y,
        z=message.linear.z,
        roll=message.angular.x,
        pitch=message.angular.y,
        yaw=message.angular.z,
    )


def _to_twist(command: MotionCommand) -> Twist:
    message = Twist()
    message.linear.x = command.x
    message.linear.y = command.y
    message.linear.z = command.z
    message.angular.x = command.roll
    message.angular.y = command.pitch
    message.angular.z = command.yaw
    return message


class FlightCommandGuardNode(Node):
    """Bridge requested commands through the planning-only timeout guard."""

    def __init__(self) -> None:
        super().__init__('flight_command_guard')
        self.logic = GuardLogic()
        self.requested = MotionCommand()
        self.requested_enable = False
        self.altitude_m = 0.0
        self.last_state = ''
        self.command_publisher = self.create_publisher(
            Twist, '/arachne_hx6/command/twist', 10,
        )
        self.enable_publisher = self.create_publisher(
            Bool, '/arachne_hx6/enable', 10,
        )
        self.state_publisher = self.create_publisher(
            String, '/arachne_hx6/failsafe/state', 10,
        )
        self.create_subscription(
            Twist,
            '/arachne_hx6/request/twist',
            self._twist_callback,
            10,
        )
        self.create_subscription(
            Bool,
            '/arachne_hx6/request/enable',
            self._enable_callback,
            10,
        )
        self.create_subscription(
            Bool,
            '/arachne_hx6/request/reset_failsafe',
            self._reset_callback,
            10,
        )
        self.create_subscription(
            Odometry,
            '/model/arachne_flight_hex/odometry',
            self._odometry_callback,
            10,
        )
        self.create_timer(0.05, self._step)

    def _now(self) -> float:
        return time.monotonic()

    def _submit(self) -> None:
        accepted = self.logic.accept(
            self.requested,
            self.requested_enable,
            self._now(),
        )
        if not accepted:
            self.get_logger().warning(
                'Request rejected while failsafe latch is active',
            )

    def _twist_callback(self, message: Twist) -> None:
        self.requested = _from_twist(message)
        self._submit()

    def _enable_callback(self, message: Bool) -> None:
        self.requested_enable = message.data
        self._submit()

    def _reset_callback(self, message: Bool) -> None:
        if message.data and not self.logic.reset():
            self.get_logger().warning('Airborne failsafe reset rejected')

    def _odometry_callback(self, message: Odometry) -> None:
        self.altitude_m = message.pose.pose.position.z

    def _step(self) -> None:
        output = self.logic.tick(self._now(), self.altitude_m)
        self.command_publisher.publish(_to_twist(output.command))
        enabled = Bool()
        enabled.data = output.enabled
        self.enable_publisher.publish(enabled)
        status = String()
        status.data = json.dumps({
            'state': output.state,
            'reason': output.reason,
            'status': 'ANALYSIS_ONLY',
            'procurement_allowed': False,
        }, separators=(',', ':'))
        self.state_publisher.publish(status)
        if output.state != self.last_state:
            self.get_logger().info(
                f'guard state: {output.state} ({output.reason})',
            )
            self.last_state = output.state


def main() -> None:
    """Run the ROS command guard node."""
    rclpy.init()
    node = FlightCommandGuardNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
