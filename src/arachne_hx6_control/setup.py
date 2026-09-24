from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'arachne_hx6_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lijunhao',
    maintainer_email='lijunhao@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gazebo_flight_scenario = arachne_hx6_control.gazebo_flight_scenario:main',
            'gazebo_motor_scenario = arachne_hx6_control.gazebo_motor_scenario:main',
            'flight_command_guard = arachne_hx6_control.flight_command_guard:main',
            'gazebo_link_loss_scenario = arachne_hx6_control.gazebo_link_loss_scenario:main',
            'flight_evidence = arachne_hx6_control.flight_evidence:main',
        ],
    },
)
