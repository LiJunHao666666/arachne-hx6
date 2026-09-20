# Gazebo flight-hex baseline

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

The repository contains an isolated legless six-rotor Gazebo model using the
Gazebo 8 MulticopterMotorModel and MulticopterVelocityControl systems. Geometry,
mass, inertia, motor constants, and gains are planning assumptions. The model is
local and does not download assets from Gazebo Fuel.

Build with `colcon build --symlink-install --packages-select arachne_hx6_simulation`,
source `install/setup.bash`, then run
`ros2 launch arachne_hx6_simulation flight_hex.launch.py`.
For headless operation pass `gz_args:="-s -r"`.

ROS bridges expose `/arachne_hx6/command/twist`,
`/arachne_hx6/enable`, and `/model/arachne_flight_hex/odometry`.
Automated takeoff, hover, and landing acceptance are still NOT_RUN. Simulation
success will not establish physical flight readiness.
