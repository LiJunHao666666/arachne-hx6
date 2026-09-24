# Exercise 02: offline six-channel command safety

Status: **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**

Run `python3 scripts/hexa_channel_state.py --output /tmp/arachne-channel-demo.json`
and `python3 -m pytest -q scripts/tests/test_hexa_channel_state.py`.

The report demonstrates IDLE, one-at-a-time CHANNEL_TEST, latched STOP,
rejection while latched, explicit RESET, timestamp checks, and simulated link
timeout. No flight controller, ESC, motor, serial port, or network is connected.

Passing provides a regression-tested basis for SIM-02 through SIM-04. It does
not validate dynamics, physical stopping, lift, attitude stability, or flight
readiness. Desktop stop behavior is not an airborne failsafe policy.
