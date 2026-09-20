# Exercise 05: Gazebo takeoff, hover, and landing

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

Start the headless world:

`ros2 launch arachne_hx6_simulation flight_hex.launch.py gz_args:="-s -r"`

In a second sourced terminal, run:

`ros2 run arachne_hx6_control gazebo_flight_scenario --output /tmp/arachne_gazebo_acceptance.json`

The node publishes enable and body vertical-velocity commands at 20 Hz, records
Gazebo odometry, and evaluates takeoff, hover variation, landing altitude, and
horizontal drift. The first verified local run collected 650 samples, reached
1.386 m, held a 0.049 m hover span, landed at 0.020 m, and passed the declared
planning-model criteria.

These results use assumed geometry, mass, inertia, motor constants, and Gazebo's
velocity controller. They do not validate a selected flight controller,
propulsion hardware, battery, aerodynamics, estimator, wind response, structural
strength, or physical flight readiness.
