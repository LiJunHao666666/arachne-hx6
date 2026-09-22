#!/usr/bin/env python3
"""Compare a local six-rotor SDF with the ArduPilot Hexa X reference.

Read-only structural study, not a SITL run or physical wiring approval.
"""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

# ArduPilot AP_MotorsMatrix.cpp, setup_hexa_matrix / MOTOR_FRAME_TYPE_X.
# Angle: clockwise from the nose; spin: viewed from above; test order: 1..6.
HEXA_X = [(90, 'cw', 2), (-90, 'ccw', 5), (-30, 'cw', 6),
          (150, 'ccw', 3), (30, 'ccw', 1), (-150, 'cw', 4)]
SOURCE = 'https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Motors/AP_MotorsMatrix.cpp'


def compare(xml_text, nose_yaw_deg):
    """Require an explicit nose angle in the model's XY plane (+Z upward)."""
    if not math.isfinite(nose_yaw_deg):
        raise ValueError('nose angle must be finite')
    root = ET.fromstring(xml_text)
    models = [m for m in root.iter('model') if m.get('name') == 'arachne_flight_hex']
    if len(models) != 1:
        raise ValueError('expected one arachne_flight_hex model')
    model = models[0]
    rotors = []
    for plugin in model.findall('plugin'):
        if plugin.get('name') != 'gz::sim::systems::MulticopterMotorModel':
            continue
        index = int(plugin.findtext('actuator_number', '-1'))
        spin = plugin.findtext('turningDirection')
        link_name = plugin.findtext('linkName')
        links = [l for l in model.findall('link') if l.get('name') == link_name]
        joints = [j for j in model.findall('joint')
                  if j.get('name') == plugin.findtext('jointName')]
        if len(links) != 1 or len(joints) != 1:
            raise ValueError('motor must resolve to one link and joint')
        pose = links[0].find('pose')
        if pose is None or pose.get('relative_to') != 'base_link':
            raise ValueError('only explicit base_link-relative rotor poses are supported')
        values = [float(v) for v in (pose.text or '').split()]
        if len(values) != 6 or not all(math.isfinite(v) for v in values):
            raise ValueError('invalid rotor pose')
        x, y, _, roll, pitch, yaw = values
        if any(abs(v) > 1e-9 for v in (roll, pitch, yaw)) or math.hypot(x, y) < 1e-6:
            raise ValueError('only unrotated, noncentral rotors are supported')
        axis = joints[0].find('axis/xyz')
        if (axis is None or axis.get('expressed_in') or joints[0].find('pose') is not None or
                [float(v) for v in (axis.text or '').split()] != [0., 0., 1.] or
                joints[0].findtext('parent') != 'base_link' or
                joints[0].findtext('child') != link_name):
            raise ValueError('unsupported motor joint or axis')
        if spin not in {'cw', 'ccw'}:
            raise ValueError('invalid turningDirection')
        rotors.append({'actuator_index': index, 'link': link_name,
                       'angle_deg': math.degrees(math.atan2(y, x)) % 360,
                       'spin': spin})
    if len(rotors) != 6 or {r['actuator_index'] for r in rotors} != set(range(6)):
        raise ValueError('expected six unique actuator indices 0..5')
    rows, used = [], set()
    for number, (angle, spin, test_order) in enumerate(HEXA_X, 1):
        target = (nose_yaw_deg - angle) % 360
        matches = [r for r in rotors if abs((r['angle_deg'] - target + 180) % 360 - 180) < 0.1]
        if len(matches) != 1 or matches[0]['actuator_index'] in used:
            raise ValueError('geometry does not uniquely match regular Hexa X at this nose angle')
        rotor = matches[0]
        used.add(rotor['actuator_index'])
        rows.append({'ardupilot_motor': number, 'test_order': test_order,
                     'gazebo_actuator': rotor['actuator_index'], 'link': rotor['link'],
                     'expected_spin': spin, 'observed_spin': rotor['spin'],
                     'spin_matches': rotor['spin'] == spin})
    return {'status': 'ANALYSIS_ONLY', 'procurement_allowed': False,
            'physical_wiring_approved': False, 'nose_yaw_deg': nose_yaw_deg,
            'reference': SOURCE, 'reference_checked_on': '2026-09-22',
            'result': 'LABELS_MATCH' if all(r['spin_matches'] for r in rows) else 'SPIN_LABEL_CONFLICT',
            'mapping': rows,
            'limitations': ['Compares geometry and spin labels only, not yaw torque or dynamics',
                            'Motor functions are not physical FC connector pin numbers',
                            'Nose angle is a caller assumption, not an observed airframe orientation',
                            'Reference is a dated Hexa X snapshot, not the installed firmware']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sdf', type=Path)
    parser.add_argument('--nose-yaw-deg', required=True, type=float)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.sdf.read_text(encoding='utf-8'), args.nose_yaw_deg)
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.error(str(exc))
    result['input'] = args.sdf.as_posix()
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0 if result['result'] == 'LABELS_MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
