import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_path, 'launch', 'launch_sim.launch.py')
            ),
            launch_arguments={
                'use_lidar': 'true',
                'use_camera': 'false',
                'use_teleop': 'true',
            }.items(),
        )
    ])