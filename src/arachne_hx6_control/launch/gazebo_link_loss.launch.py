"""Launch the flight hex with the planning-only command guard."""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():
    """Create the guarded headless Gazebo launch description."""
    simulation_share = get_package_share_directory(
        'arachne_hx6_simulation',
    )
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                simulation_share,
                'launch',
                'flight_hex.launch.py',
            ),
        ),
        launch_arguments={
            'gz_args': LaunchConfiguration('gz_args'),
        }.items(),
    )
    guard = Node(
        package='arachne_hx6_control',
        executable='flight_command_guard',
        output='screen',
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_args',
            default_value='-s -r',
            description='Gazebo arguments; default is headless and running',
        ),
        simulation,
        guard,
    ])
