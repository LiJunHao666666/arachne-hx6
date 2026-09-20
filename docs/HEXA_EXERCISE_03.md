# Exercise 03: vertical closed-loop flight baseline

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

Run:

`python3 scripts/hexa_vertical_flight.py --output /tmp/arachne-vertical-flight.json`

This deterministic planning model commands six equal rotor thrusts through a
first-order actuator, vertical rigid-body dynamics, ground contact, and a PD
altitude controller. The scenario contains takeoff, one-metre hover, descent,
and disarm. It reports hover error, overshoot, saturation, and landing state.

Every numeric parameter is tagged PLANNING_ASSUMPTION. The model omits attitude,
horizontal motion, aerodynamics, battery behavior, estimator error, sensor
noise, disturbances, and structure. PASS applies only to this vertical scenario
and leaves flight_readiness UNDETERMINED.

Test with:

`python3 -m pytest -q scripts/tests/test_hexa_vertical_flight.py`
