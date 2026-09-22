# Gazebo rotor indices and ArduPilot Hexa X: candidate bridge

Status: `ANALYSIS_ONLY`; `procurement_allowed=false`. This is a **comparison**,
not an approved motor-output map. No real motor, ESC, propeller or flight
controller has been selected.

The current generator `scripts/generate_gazebo_hex.py` places six rotors at
`30 + 60*i` degrees counterclockwise from body +X and publishes commands at
actuator indices `0..5`. The local simulation now marks body +X as the nose
with an orange bar on top of the body; +Y is left and +Z is up. This is a
visual-only marker, with no added mass, collision or change to motor mixing.
It establishes the local simulation convention, not a physical FC orientation.

When viewing from above, positive yaw about +Z turns the nose counterclockwise.
The offline allocator's roll/pitch terms are respectively `y * thrust` and
`-x * thrust`, consistent with upward thrust in this body frame. This geometric
check does not validate Gazebo's yaw reaction torque or firmware integration.
The marker appears after reloading a generated world; an already running
Gazebo session does not automatically reload a modified SDF file.

Current Gazebo geometry and plugin spin directions (viewed from above):

- `rotor_0` / actuator 0: front-left, `+30°`, CCW.
- `rotor_1` / actuator 1: left, `+90°`, CW.
- `rotor_2` / actuator 2: rear-left, `+150°`, CCW.
- `rotor_3` / actuator 3: rear-right, `+210°`, CW.
- `rotor_4` / actuator 4: right, `+270°`, CCW.
- `rotor_5` / actuator 5: front-right, `+330°`, CW.

The current ArduPilot `AP_MotorsMatrix` Hexa X definition places Motor 1 at
right/CW, Motor 2 at left/CCW, Motor 3 at front-left/CW, Motor 4 at
rear-right/CCW, Motor 5 at front-right/CCW and Motor 6 at rear-left/CW. Its
motor-test order is **M5, M1, M4, M6, M2, M3**, which is distinct from motor
number order. ArduPilot also permits output-function remapping; a board pad
marked M1 is not automatically a validated physical Motor 1 connection.

Under the +X-nose assumption, the **position-only** candidate association is:

- Ardu M1 → Gazebo `rotor_4` (right).
- Ardu M2 → Gazebo `rotor_1` (left).
- Ardu M3 → Gazebo `rotor_0` (front-left).
- Ardu M4 → Gazebo `rotor_3` (rear-right).
- Ardu M5 → Gazebo `rotor_5` (front-right).
- Ardu M6 → Gazebo `rotor_2` (rear-left).

All six Gazebo plugin spin labels at these positions are currently opposite
to the ArduPilot Hexa X definition. This is a **model/firmware convention
conflict**, not evidence that the physical craft should be wired in the
opposite direction. Keep the KiCad ESC_CH1–CH6 labels as logical channels.
Do not relabel them as Ardu motors or change Gazebo yaw signs based on this
document alone. The nose assumption matters: setting the study nose to +60°
in the same model changes the position mapping and makes all six spin labels
match. That does not establish correct yaw dynamics or authorize adopting
that orientation for the airframe.

Run the read-only comparison with an explicit nose angle:

```sh
python3 scripts/check_rotor_order.py \
  src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf \
  --nose-yaw-deg 0
```

Exit 1 means a spin-label conflict, 0 means labels match under the supplied
orientation, and 2 means unsupported/malformed input. All outcomes retain
`physical_wiring_approved=false`. The tool rejects duplicate actuator indices,
ambiguous geometry and unsupported joint/pose transforms; it does not launch
Gazebo, drive motors or change any model or firmware parameter.

Before a physical output map can be approved: define and visibly mark the
model nose; choose the actual firmware frame type and FC output-function
settings; reconcile the yaw/rotation convention in a dedicated SITL exercise;
then use the selected firmware's motor test with **propellers removed** to
check each physical position and spin direction. Actual connector pinout,
signal protocol and power ratings remain separate gates.

Sources: [ArduPilot Hexa X motor matrix](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Motors/AP_MotorsMatrix.cpp)
and [ArduPilot ESC/motor connection and motor-test guidance](https://ardupilot.org/copter/docs/connect-escs-and-motors.html).
