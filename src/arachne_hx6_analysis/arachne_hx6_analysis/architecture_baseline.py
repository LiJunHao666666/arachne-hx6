"""G1 Xacro/URDF baseline extraction and YAML-vs-Xacro consistency checks.

Does not modify G1 description files. Fail-closed on missing properties,
unsupported Xacro syntax, or numeric drift.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

import ast
from pathlib import Path
import math
import re
from typing import Any, Mapping

import yaml

from arachne_hx6_analysis.architecture_types import (
    G1_BASELINE_XACRO_KEYS,
    G1Baseline,
    LEG_PREFIXES,
    ArchitectureConfig,
    BaselineCheck,
    _BASELINE_ABS_TOL,
)
from arachne_hx6_analysis.geometry import LegMount
from arachne_hx6_analysis.inputs import (
    as_float,
    as_mapping,
    as_str,
    require_key,
)
from arachne_hx6_analysis.model import InvalidInputError

_XACRO_PROPERTY = re.compile(
    r'<xacro:property\s+name="([^"]+)"\s+value="([^"]+)"\s*/>'
)
_ALLOWED_AST = {
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
    ast.Load,
    ast.Name,
    ast.Constant,
}



def parse_xacro_numeric_properties(path: Path) -> dict[str, float]:
    """Read ``<xacro:property>`` numeric values, including simple ${expr}.

    Fail-closed: missing file, zero matches, duplicate names, non-numeric
    values, unsupported property syntax, or unresolved expressions raise.
    The regex only matches a single-line self-closing tag with double-quoted
    ``name`` then ``value`` attributes. Included files are not followed.
    """
    if not path.is_file():
        raise InvalidInputError(f'xacro file not found: {path}')
    text = path.read_text(encoding='utf-8')
    matches = list(_XACRO_PROPERTY.finditer(text))
    loose_count = len(re.findall(r'<xacro:property\b', text))
    if loose_count != len(matches):
        raise InvalidInputError(
            f'{path} has xacro:property tags that do not match the strict '
            'single-line name= then value= self-closing pattern'
        )
    raw: dict[str, str] = {}
    for match in matches:
        name = match.group(1)
        value = match.group(2)
        if name in raw:
            raise InvalidInputError(
                f'duplicate xacro property {name!r} in {path}'
            )
        raw[name] = value
    if not raw:
        raise InvalidInputError(f'no xacro properties in {path}')
    numeric: dict[str, float] = {}
    pending: dict[str, str] = {}
    for name, value in raw.items():
        try:
            numeric[name] = float(value)
        except ValueError:
            if value.startswith('${') and value.endswith('}') and len(value) > 3:
                pending[name] = value
            else:
                raise InvalidInputError(
                    f'xacro property {name!r} is not numeric and not a '
                    f'${{expr}}: {value!r}'
                ) from None
    for _iteration in range(len(pending) + 2):
        if not pending:
            break
        resolved: list[str] = []
        for name, value in pending.items():
            expr = value[2:-1]
            try:
                numeric[name] = _eval_xacro_expr(expr, numeric)
                resolved.append(name)
            except InvalidInputError:
                continue
        for name in resolved:
            del pending[name]
        if not resolved:
            break
    if pending:
        raise InvalidInputError(
            'unresolved or unparseable xacro expressions: '
            + ', '.join(f'{name}={pending[name]!r}' for name in sorted(pending))
        )
    return numeric


def load_standing_joints(path: Path) -> dict[str, float]:
    """Read G1 standing_pose.yaml zeros.<joint> map."""
    if not path.is_file():
        raise InvalidInputError(f'standing pose file not found: {path}')
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {path}: {exc}') from exc
    root = as_mapping(raw, 'standing_pose')
    ns = as_mapping(require_key(root, '/**', 'standing_pose'), 'standing_pose./**')
    params = as_mapping(
        require_key(ns, 'ros__parameters', 'standing_pose./**'),
        'standing_pose./**.ros__parameters',
    )
    joints: dict[str, float] = {}
    for key, value in params.items():
        name = as_str(key, 'standing_pose parameter name')
        if not name.startswith('zeros.'):
            raise InvalidInputError(
                f'standing_pose unexpected key {name!r}; expected zeros.<joint>'
            )
        joint = name[len('zeros.'):]
        joints[joint] = as_float(value, name)
    return joints



def _eval_xacro_expr(expr: str, names: Mapping[str, float]) -> float:
    tree = ast.parse(expr, mode='eval')
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_AST:
            raise InvalidInputError(f'unsupported xacro expression: {expr}')
        if isinstance(node, ast.Name) and node.id not in names and node.id != 'pi':
            raise InvalidInputError(f'unknown xacro symbol {node.id} in {expr}')
    env = dict(names)
    env['pi'] = math.pi
    result = eval(compile(tree, '<xacro>', 'eval'), {'__builtins__': {}}, env)
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise InvalidInputError(f'xacro expression did not yield a number: {expr}')
    number = float(result)
    if not math.isfinite(number):
        raise InvalidInputError(f'xacro expression is not finite: {expr}')
    return number


def _g1_baseline_from_xacro(values: Mapping[str, float]) -> G1Baseline:
    required = (
        'hex_arm_span',
        'coxa_length',
        'femur_length',
        'tibia_length',
        'body_length',
        'body_width',
        'body_height',
        'sensor_pod_size_x',
        'sensor_pod_size_y',
        'sensor_pod_size_z',
        'sensor_pod_z',
        'hex_deck_offset',
        'hex_rotor_z_offset',
        'coxa_radius',
        'femur_width',
        'femur_height',
        'tibia_width',
        'tibia_height',
        'foot_radius',
        'camera_size_x',
        'camera_size_y',
        'camera_size_z',
        'camera_x',
        'camera_z',
        'leg_mount_x_front',
        'leg_mount_x_mid',
        'leg_mount_x_rear',
        'leg_mount_y',
        'leg_mount_z',
        'leg_yaw_front',
        'leg_yaw_mid',
        'leg_yaw_rear',
        'coxa_lower',
        'coxa_upper',
        'femur_lower',
        'femur_upper',
        'tibia_lower',
        'tibia_upper',
        'hex_yaw_1',
    )
    missing = [name for name in required if name not in values]
    if missing:
        raise InvalidInputError(f'xacro missing properties: {missing}')
    rotor_plane = (
        0.5 * values['body_height']
        + values['hex_deck_offset']
        + values['hex_rotor_z_offset']
    )
    sensor_pod_y = 0.5 * values['body_width'] + 0.5 * values['sensor_pod_size_y']
    limits: dict[str, tuple[float, float]] = {}
    for prefix in LEG_PREFIXES:
        limits[f'{prefix}_coxa_joint'] = (
            values['coxa_lower'], values['coxa_upper']
        )
        limits[f'{prefix}_femur_joint'] = (
            values['femur_lower'], values['femur_upper']
        )
        limits[f'{prefix}_tibia_joint'] = (
            values['tibia_lower'], values['tibia_upper']
        )
    mounts = (
        LegMount('lf', values['leg_mount_x_front'], values['leg_mount_y'],
                 values['leg_mount_z'], values['leg_yaw_front']),
        LegMount('lm', values['leg_mount_x_mid'], values['leg_mount_y'],
                 values['leg_mount_z'], values['leg_yaw_mid']),
        LegMount('lr', values['leg_mount_x_rear'], values['leg_mount_y'],
                 values['leg_mount_z'], values['leg_yaw_rear']),
        LegMount('rf', values['leg_mount_x_front'], -values['leg_mount_y'],
                 values['leg_mount_z'], -values['leg_yaw_front']),
        LegMount('rm', values['leg_mount_x_mid'], -values['leg_mount_y'],
                 values['leg_mount_z'], -values['leg_yaw_mid']),
        LegMount('rr', values['leg_mount_x_rear'], -values['leg_mount_y'],
                 values['leg_mount_z'], -values['leg_yaw_rear']),
    )
    return G1Baseline(
        hex_arm_span_m=values['hex_arm_span'],
        coxa_length_m=values['coxa_length'],
        femur_length_m=values['femur_length'],
        tibia_length_m=values['tibia_length'],
        body_length_m=values['body_length'],
        body_width_m=values['body_width'],
        body_height_m=values['body_height'],
        sensor_pod_size_x_m=values['sensor_pod_size_x'],
        sensor_pod_size_y_m=values['sensor_pod_size_y'],
        sensor_pod_size_z_m=values['sensor_pod_size_z'],
        sensor_pod_z_m=values['sensor_pod_z'],
        hex_deck_offset_m=values['hex_deck_offset'],
        hex_rotor_z_offset_m=values['hex_rotor_z_offset'],
        rotor_plane_z_m=rotor_plane,
        sensor_pod_y_m=sensor_pod_y,
        first_motor_yaw_rad=values['hex_yaw_1'],
        coxa_radius_m=values['coxa_radius'],
        femur_width_m=values['femur_width'],
        femur_height_m=values['femur_height'],
        tibia_width_m=values['tibia_width'],
        tibia_height_m=values['tibia_height'],
        foot_radius_m=values['foot_radius'],
        camera_size_x_m=values['camera_size_x'],
        camera_size_y_m=values['camera_size_y'],
        camera_size_z_m=values['camera_size_z'],
        camera_x_m=values['camera_x'],
        camera_z_m=values['camera_z'],
        joint_limits=limits,
        mounts=mounts,
        xacro_values=dict(values),
    )


def _compare_g1_baseline(
    config: ArchitectureConfig,
    baseline: G1Baseline,
    xacro_values: Mapping[str, float],
) -> BaselineCheck:
    comparisons: list[dict[str, Any]] = []
    consistent = True
    for yaml_key, xacro_key in G1_BASELINE_XACRO_KEYS:
        yaml_value = config.g1_baseline_yaml[yaml_key]
        xacro_value = xacro_values[xacro_key]
        match = abs(yaml_value - xacro_value) <= _BASELINE_ABS_TOL
        comparisons.append({
            'field': yaml_key,
            'yaml_m': yaml_value,
            'xacro_m': xacro_value,
            'xacro_property': xacro_key,
            'match': match,
        })
        consistent = consistent and match
    derived = (
        ('rotor_plane_z_m', baseline.rotor_plane_z_m),
        ('sensor_pod_y_m', baseline.sensor_pod_y_m),
        ('hex_arm_span_m', baseline.hex_arm_span_m),
    )
    for field_name, xacro_value in derived:
        yaml_value = config.g1_baseline_yaml[field_name]
        match = abs(yaml_value - xacro_value) <= _BASELINE_ABS_TOL
        comparisons.append({
            'field': field_name + '_derived',
            'yaml_m': yaml_value,
            'xacro_m': xacro_value,
            'xacro_property': 'derived',
            'match': match,
        })
        consistent = consistent and match
    expected_span = 0.30
    span_ok = abs(baseline.hex_arm_span_m - expected_span) <= _BASELINE_ABS_TOL
    comparisons.append({
        'field': 'hex_arm_span_current_g1',
        'yaml_m': expected_span,
        'xacro_m': baseline.hex_arm_span_m,
        'xacro_property': 'hex_arm_span',
        'match': span_ok,
    })
    consistent = consistent and span_ok
    return BaselineCheck(
        consistent=consistent,
        comparisons=tuple(comparisons),
        xacro_path=str(config.xacro_path),
        standing_pose_path=str(config.standing_pose_path),
    )
