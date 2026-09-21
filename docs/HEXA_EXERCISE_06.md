# Exercise 06: command-dropout controlled landing

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

This exercise adds a planning-only command guard in front of the Gazebo
velocity controller. It does not implement, configure, or validate a real
flight-controller failsafe.

The guard uses four states:

1. `DISARMED`: outputs are disabled.
2. `ACTIVE`: fresh requested velocity commands are forwarded.
3. `AIRBORNE_FAILSAFE`: a command timeout or airborne disable request is
   latched; horizontal and angular velocity requests become zero and the model
   receives a limited `-0.25 m/s` vertical command.
4. `LANDED_LOCKED`: after reaching `0.08 m` altitude, output is disabled.
   New commands remain rejected until an explicit reset is received on the
   ground.

Start the guarded headless world:

```bash
ros2 launch arachne_hx6_control gazebo_link_loss.launch.py
```

In another sourced terminal, run the acceptance scenario:

```bash
ros2 run arachne_hx6_control gazebo_link_loss_scenario \
  --output /tmp/arachne_gazebo_link_loss.json
```

The scenario requests takeoff and hover, then deliberately stops publishing at
6 seconds. It requires the guard to enter `AIRBORNE_FAILSAFE` after its
configured timeout, descend, enter `LANDED_LOCKED`, and remain within the
declared horizontal and final-altitude bounds.

All thresholds are planning assumptions. Gazebo odometry is not hardware
evidence, the velocity controller is not a selected flight controller, and a
passing result does not establish physical flight safety or readiness.
