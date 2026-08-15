import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def _setup(context, *args, **kwargs):
    pkg_share = FindPackageShare('arachne_hx6_description').perform(context)
    xacro_file = os.path.join(pkg_share, 'urdf', 'arachne_hx6.urdf.xacro')
    rviz_config = os.path.join(pkg_share, 'rviz', 'arachne_hx6.rviz')
    standing_pose = os.path.join(pkg_share, 'config', 'standing_pose.yaml')

    initial_pose = LaunchConfiguration('initial_pose').perform(context)
    if initial_pose not in ('standing', 'zero'):
        raise RuntimeError(
            f"initial_pose must be 'standing' or 'zero', got '{initial_pose}'"
        )

    robot_description = ParameterValue(
        Command([
            FindExecutable(name='xacro'),
            ' ',
            xacro_file,
        ]),
        value_type=str,
    )

    jsp_parameters = []
    if initial_pose == 'standing':
        # Jazzy joint_state_publisher_gui reads zeros.<joint_name> from this file.
        jsp_parameters.append(standing_pose)

    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            parameters=jsp_parameters,
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'initial_pose',
            default_value='standing',
            description='Initial kinematic pose: standing (default) or zero.',
        ),
        OpaqueFunction(function=_setup),
    ])
