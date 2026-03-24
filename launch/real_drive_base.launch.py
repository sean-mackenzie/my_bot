import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'use_sim': 'false',
            'use_lidar': 'false',
            'use_camera': 'false',
        }.items(),
    )

    base_driver = Node(
        package='my_bot',
        executable='diff_drive_base.py',
        name='diff_drive_base',
        output='screen',
        parameters=[os.path.join(pkg_path, 'config', 'base_driver.yaml')],
    )

    return LaunchDescription([
        rsp,
        base_driver,
    ])