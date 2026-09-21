# Exercise 08: coupled six-motor flight planning model

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**
procurement_allowed: false

The earlier offline exercises checked vertical flight and six-channel attitude
allocation separately. This exercise runs them in one deterministic small-angle
model. It simulates six independent motor thrust states with first-order lag,
altitude feedback, roll/pitch/yaw feedback, lateral position feedback, and a
short horizontal acceleration disturbance during hover.

Run from the repository root:

    python3 scripts/hexa_coupled_flight.py \
      --output /tmp/arachne_coupled_flight.json

The JSON records every motor thrust, position, velocity, attitude, and injected
disturbance sample. Its acceptance criteria cover hover altitude error, maximum
height and horizontal displacement, horizontal recovery after the disturbance,
peak tilt, motor saturation, and final landed state. The default planning
configuration passed locally on 2026-09-21 with approximately 0.0026 m hover
altitude RMSE, 0.125 m maximum horizontal displacement, 0.058 m recovery
error, 3.23 degrees peak tilt, zero saturated channel steps, and zero final
altitude. These figures are regression outputs of assumed parameters, not
measured performance.

A weak-thrust configuration is also tested: it must fail the acceptance gate
rather than reporting a stable hover. The scenario is deterministic and needs
only Python plus the repository's existing offline attitude allocator.

This is not ArduCopter SITL, a calibrated motor model, or a physical-flight
claim. It omits state estimation, battery voltage sag, aerodynamics, ground
effect, structural dynamics, and uncertain mass or thrust. The remaining
flight-controller integration step is to run a six-output ArduCopter SITL path
against an appropriate motor-level simulator and collect its own evidence.
The Gazebo velocity-controller evidence is kept separate from this offline
planning-model result.