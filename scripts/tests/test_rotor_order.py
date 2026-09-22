"""Reject ambiguous geometry and distinguish orientation from spin labels."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rotor_order', ROOT / 'scripts/check_rotor_order.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
MODEL = ROOT / 'src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf'


def test_current_x_forward_model_has_six_conflicts():
    report = check.compare(MODEL.read_text(), 0)
    assert report['result'] == 'SPIN_LABEL_CONFLICT'
    assert [r['gazebo_actuator'] for r in report['mapping']] == [4, 1, 0, 3, 5, 2]
    assert not any(r['spin_matches'] for r in report['mapping'])


def test_nose_rotation_changes_association_without_approving_wiring():
    report = check.compare(MODEL.read_text(), 60)
    assert report['result'] == 'LABELS_MATCH'
    assert report['physical_wiring_approved'] is False
    assert report['procurement_allowed'] is False


def test_xml_order_does_not_define_actuator_number():
    root = ET.fromstring(MODEL.read_text())
    model = root.find('model')
    model[:] = list(reversed(list(model)))
    assert check.compare(ET.tostring(root, encoding='unicode'), 0) == check.compare(MODEL.read_text(), 0)


def test_duplicate_indices_rejected():
    root = ET.fromstring(MODEL.read_text())
    indices = root.findall('.//actuator_number')
    indices[1].text = indices[0].text
    with pytest.raises(ValueError, match='unique actuator'):
        check.compare(ET.tostring(root, encoding='unicode'), 0)


@pytest.mark.parametrize('nose', [float('nan'), float('inf'), 15])
def test_invalid_or_nonmatching_orientation_rejected(nose):
    with pytest.raises(ValueError):
        check.compare(MODEL.read_text(), nose)


def test_tilted_axis_rejected():
    root = ET.fromstring(MODEL.read_text())
    root.find('.//joint/axis/xyz').text = '0 1 0'
    with pytest.raises(ValueError, match='axis'):
        check.compare(ET.tostring(root, encoding='unicode'), 0)
