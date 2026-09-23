"""Run the isolated motor-level Gazebo hex and ROS actuator bridge."""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('arachne_hx6_simulation')
    gz_share = get_package_share_directory('ros_gz_sim')
    world = os.path.join(share, 'worlds', 'flight_hex_motor.sdf')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gz_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': [LaunchConfiguration('gz_args'), ' ', world],
        }.items(),
    )
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/arachne_hx6/command/motor_speed@actuator_msgs/msg/Actuators@gz.msgs.Actuators',
            '/model/arachne_flight_hex/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry',
        ],
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_args', default_value='-s -r',
            description='Use a separate GUI with the motor-level world',
        ),
        gazebo,
        bridge,
    ])