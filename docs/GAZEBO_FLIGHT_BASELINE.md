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
The automated takeoff, hover, and landing scenario passes in this simulation.
Simulation success does not establish physical flight readiness.

For the local WSLg workstation, use `scripts/run_gazebo_gui.sh`. The wrapper
selects Mesa D3D12 and the NVIDIA adapter because automatic selection fell back
to CPU llvmpipe. It runs the physics server and ROS bridge independently from a
30 Hz OGRE1 GUI, avoiding the OGRE2 selection-material failures seen while
dragging entities. Set `ARACHNE_GZ_GUI_HZ` to override the visual refresh cap.
The world uses a 2 ms physics step to reduce update overhead while retaining
500 Hz physics.
