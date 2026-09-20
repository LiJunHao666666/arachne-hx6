# Exercise 04: six-rotor attitude allocation

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

Run `python3 scripts/hexa_attitude_flight.py --output /tmp/arachne-attitude.json`.

The model builds a 4-by-6 matrix from the six rotor positions and alternating
rotation directions. A pseudoinverse maps total thrust plus roll, pitch, and yaw
torques to six rotor thrusts. A PD controller then recovers from an assumed
initial attitude error in a deterministic small-angle rigid-body simulation.

All parameters are PLANNING_ASSUMPTION. Fixed total thrust removes translational
and altitude coupling. Motor lag, nonlinear orientation, aerodynamics, battery,
estimator, noise, disturbances, and structure remain outside this exercise.
PASS does not establish physical flight readiness.
