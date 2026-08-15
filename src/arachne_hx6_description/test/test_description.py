"""GUI-free G1 digital-skeleton regression checks for arachne_hx6_description."""

from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_XACRO_FILE = _PACKAGE_ROOT / 'urdf' / 'arachne_hx6.urdf.xacro'
_STANDING_POSE_FILE = _PACKAGE_ROOT / 'config' / 'standing_pose.yaml'

_LEG_PREFIXES = ('lf', 'lm', 'lr', 'rf', 'rm', 'rr')
_LEG_SEGMENTS = ('coxa', 'femur', 'tibia')
_EXPECTED_REVOLUTE = {
    f'{prefix}_{segment}_joint'
    for prefix in _LEG_PREFIXES
    for segment in _LEG_SEGMENTS
}
_PAYLOAD_FIXED_JOINTS = (
    'camera_joint',
    'left_sensor_pod_joint',
    'right_sensor_pod_joint',
)


def _child_text_or_attrib(element, tag, attr):
    node = element.find(tag)
    assert node is not None, f'missing <{tag}>'
    value = node.get(attr)
    assert value is not None, f'missing {tag}.{attr}'
    return value


@pytest.fixture(scope='module')
def expanded_urdf():
    xacro_bin = shutil.which('xacro')
    assert xacro_bin is not None, 'xacro executable is not on PATH'
    assert _XACRO_FILE.is_file(), f'missing Xacro file: {_XACRO_FILE}'
    completed = subprocess.run(
        [xacro_bin, str(_XACRO_FILE)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f'xacro failed ({completed.returncode}): {completed.stderr}'
    )
    xml_text = completed.stdout.strip()
    assert xml_text, 'xacro produced empty output'
    robot = ET.fromstring(xml_text)
    assert robot.tag == 'robot' or robot.tag.endswith('}robot')
    return robot


@pytest.fixture(scope='module')
def links(expanded_urdf):
    return expanded_urdf.findall('link')


@pytest.fixture(scope='module')
def joints(expanded_urdf):
    return expanded_urdf.findall('joint')


@pytest.fixture(scope='module')
def joints_by_name(joints):
    mapping = {}
    for joint in joints:
        name = joint.get('name')
        assert name, 'joint is missing a name'
        assert name not in mapping, f'duplicate joint name: {name}'
        mapping[name] = joint
    return mapping


def test_xacro_expands_to_xml(expanded_urdf):
    assert expanded_urdf is not None
    assert len(list(expanded_urdf)) > 0


def test_robot_name_and_root_link(expanded_urdf, links, joints):
    assert expanded_urdf.get('name') == 'arachne_hx6'
    link_names = {link.get('name') for link in links}
    assert 'base_link' in link_names
    child_links = {joint.find('child').get('link') for joint in joints}
    roots = link_names - child_links
    assert roots == {'base_link'}


def test_link_and_joint_counts(links, joints):
    assert len(links) == 41
    assert len(joints) == 40
    revolute = [j for j in joints if j.get('type') == 'revolute']
    fixed = [j for j in joints if j.get('type') == 'fixed']
    assert len(revolute) == 18
    assert len(fixed) == 22
    other = [j.get('type') for j in joints if j.get('type') not in ('revolute', 'fixed')]
    assert other == []


def test_revolute_joint_names(joints):
    revolute_names = {j.get('name') for j in joints if j.get('type') == 'revolute'}
    assert revolute_names == _EXPECTED_REVOLUTE


def test_revolute_joint_limits(joints):
    revolute = [j for j in joints if j.get('type') == 'revolute']
    assert len(revolute) == 18
    for joint in revolute:
        name = joint.get('name')
        limit = joint.find('limit')
        assert limit is not None, f'{name} is missing <limit>'
        for attr in ('lower', 'upper', 'effort', 'velocity'):
            assert limit.get(attr) is not None, f'{name} is missing limit.{attr}'
        lower = float(limit.get('lower'))
        upper = float(limit.get('upper'))
        effort = float(limit.get('effort'))
        velocity = float(limit.get('velocity'))
        assert lower < upper, f'{name} has lower >= upper'
        assert effort > 0.0, f'{name} effort must be positive'
        assert velocity > 0.0, f'{name} velocity must be positive'


def test_link_inertials_are_positive(links):
    assert len(links) == 41
    for link in links:
        name = link.get('name')
        inertial = link.find('inertial')
        assert inertial is not None, f'{name} is missing <inertial>'
        mass = float(_child_text_or_attrib(inertial, 'mass', 'value'))
        assert mass > 0.0, f'{name} mass is not positive'
        inertia = inertial.find('inertia')
        assert inertia is not None, f'{name} is missing <inertia>'
        for attr in ('ixx', 'iyy', 'izz'):
            value = inertia.get(attr)
            assert value is not None, f'{name} is missing inertia.{attr}'
            assert float(value) > 0.0, f'{name} {attr} is not positive'


def test_standing_pose_zeros_inside_limits(joints_by_name):
    assert _STANDING_POSE_FILE.is_file(), f'missing {_STANDING_POSE_FILE}'
    parsed = yaml.safe_load(_STANDING_POSE_FILE.read_text(encoding='utf-8'))
    params = parsed['/**']['ros__parameters']
    expected_keys = {f'zeros.{name}' for name in _EXPECTED_REVOLUTE}
    assert set(params.keys()) == expected_keys
    assert len(params) == 18

    for key, raw_value in params.items():
        joint_name = key[len('zeros.'):]
        value = float(raw_value)
        joint = joints_by_name[joint_name]
        assert joint.get('type') == 'revolute', f'{joint_name} is not revolute'
        limit = joint.find('limit')
        lower = float(limit.get('lower'))
        upper = float(limit.get('upper'))
        assert lower < value < upper, (
            f'{joint_name} standing value {value} is not strictly inside '
            f'({lower}, {upper})'
        )


def test_payload_joints_are_fixed(joints_by_name):
    for name in _PAYLOAD_FIXED_JOINTS:
        assert name in joints_by_name, f'missing {name}'
        assert joints_by_name[name].get('type') == 'fixed', f'{name} is not fixed'
