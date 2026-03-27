import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    map_file = '/home/sean-mackenzie/my_world_map.yaml'

    sim_lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'sim_lidar.launch.py')
        )
    )

    wait_for_sim_ready = Node(
        package='my_bot',
        executable='wait_for_sim_ready.py',
        name='wait_for_sim_ready',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'warn_after_sec': 5.0,
        }],
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': map_file,
            'topic_name': 'map',
            'frame_id': 'map',
        }],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            os.path.join(pkg_path, 'config', 'amcl.yaml'),
            {'use_sim_time': True},
        ],
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server', 'amcl'],
        }],
    )

    start_localization_when_ready = RegisterEventHandler(
        OnProcessExit(
            target_action=wait_for_sim_ready,
            on_exit=[
                map_server,
                amcl,
                TimerAction(
                    period=2.0,
                    actions=[lifecycle_manager],
                ),
            ],
        )
    )

    return LaunchDescription([
        sim_lidar,
        wait_for_sim_ready,
        start_localization_when_ready,
    ])