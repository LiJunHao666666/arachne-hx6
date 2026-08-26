from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'arachne_hx6_analysis'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='LiJunHao666666',
    maintainer_email='289059546+LiJunHao666666@users.noreply.github.com',
    description='G1.5/G2/G3 ANALYSIS_ONLY propulsion, architecture, and requirements-evidence calculations.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'propulsion_report = arachne_hx6_analysis.cli:main',
            'architecture_report = arachne_hx6_analysis.architecture_cli:main',
            'requirements_report = arachne_hx6_analysis.requirements_cli:main',
            'configuration_space_report = arachne_hx6_analysis.configuration_space_cli:main',
        ],
    },
)
