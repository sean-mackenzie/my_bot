"""
sim_nav_only10.launch.py  —  Phase 2 (navigation stack only)

PREREQUISITE: sim_localization4.launch.py must already be running in
              another terminal, with localization confirmed active:
                - /map topic publishing
                - map -> odom TF present (check with: ros2 run tf2_tools view_frames)
                - AMCL particle cloud visible in RViz

This file launches ONLY the navigation-stack nodes:
  - controller_server   (DWB local planner)
  - planner_server      (NavFn global planner)
  - behavior_server     (spin, backup, wait recoveries)
  - bt_navigator        (behavior tree orchestration)
  - waypoint_follower   (multi-goal sequencing)
  - lifecycle_manager_navigation  (activates all above, delayed 3 s)

Usage
-----
  # Terminal 1 (already running):
  ros2 launch my_bot sim_localization4.launch.py

  # Terminal 2:
  ros2 launch my_bot sim_nav_only10.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')
    nav2_params = os.path.join(pkg_path, 'config', 'nav2_params10.yaml')

    # --- Navigation nodes (launched immediately, unconfigured) ---

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[nav2_params],
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_params],
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_params],
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params],
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[nav2_params],
    )

    # --- Lifecycle manager (delayed 3 s to let nodes register services) ---

    lifecycle_manager_navigation = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                parameters=[{
                    'use_sim_time': True,
                    'autostart': True,
                    'bond_timeout': 60.0,
                    'node_names': [
                        'controller_server',
                        'planner_server',
                        'behavior_server',
                        'bt_navigator',
                        'waypoint_follower',
                    ],
                }],
            )
        ],
    )

    return LaunchDescription([
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        lifecycle_manager_navigation,
    ])
