"""
sim_nav10.launch.py  — combined localization + navigation (state-aware bringup)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')
    nav2_params = os.path.join(pkg_path, 'config', 'nav2_params10.yaml')
    map_file = '/home/sean-mackenzie/my_world_map.yaml'

    rviz_arg = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Launch RViz with navigation displays',
    )
    use_rviz = LaunchConfiguration('use_rviz')

    # ==================================================================
    # LOCALIZATION — exact replica of sim_localization4.launch.py
    # ==================================================================

    sim_lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'sim_lidar.launch.py')
        )
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

    lifecycle_manager_localization = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                parameters=[{
                    'use_sim_time': True,
                    'autostart': True,
                    'bond_timeout': 60.0,
                    'node_names': ['map_server', 'amcl'],
                }],
            )
        ],
    )

    # ==================================================================
    # NAVIGATION
    # ==================================================================

    nav_nodes = TimerAction(
        period=10.0,
        actions=[
            Node(
                package='nav2_controller',
                executable='controller_server',
                name='controller_server',
                output='screen',
                parameters=[nav2_params],
            ),
            Node(
                package='nav2_planner',
                executable='planner_server',
                name='planner_server',
                output='screen',
                parameters=[nav2_params],
            ),
            Node(
                package='nav2_behaviors',
                executable='behavior_server',
                name='behavior_server',
                output='screen',
                parameters=[nav2_params],
            ),
            Node(
                package='nav2_bt_navigator',
                executable='bt_navigator',
                name='bt_navigator',
                output='screen',
                parameters=[nav2_params],
            ),
            Node(
                package='nav2_waypoint_follower',
                executable='waypoint_follower',
                name='waypoint_follower',
                output='screen',
                parameters=[nav2_params],
            ),
        ],
    )

    bringup_script = r"""#!/bin/bash

bring_up_node() {
    local node="$1"
    local state
    state=$(ros2 lifecycle get /"$node" 2>/dev/null | awk '{print $1}')
    echo "[nav2_bringup] $node state: $state"

    case "$state" in
        unconfigured)
            echo "[nav2_bringup] Configuring $node..."
            ros2 lifecycle set /"$node" configure
            sleep 3
            echo "[nav2_bringup] Activating $node..."
            ros2 lifecycle set /"$node" activate
            sleep 1
            ;;
        inactive)
            echo "[nav2_bringup] $node already configured. Activating..."
            ros2 lifecycle set /"$node" activate
            sleep 1
            ;;
        active)
            echo "[nav2_bringup] $node already active. Skipping."
            ;;
        *)
            echo "[nav2_bringup] ERROR: $node in unexpected state '$state'. Cannot proceed."
            return 1
            ;;
    esac
}

echo "[nav2_bringup] Waiting for nav2 nodes to register..."
sleep 5

FAILED=0
for node in controller_server planner_server behavior_server bt_navigator waypoint_follower; do
    if ! bring_up_node "$node"; then
        echo "[nav2_bringup] ERROR: Failed to bring up $node"
        FAILED=1
    fi
done

if [ "$FAILED" -eq 0 ]; then
    echo "[nav2_bringup] All navigation nodes are active!"
else
    echo "[nav2_bringup] WARNING: Some nodes failed to activate. Check errors above."
fi
"""

    nav_bringup = TimerAction(
        period=12.0,
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c', bringup_script],
                output='screen',
            )
        ],
    )

    rviz_config = os.path.join(pkg_path, 'rviz', 'nav2_view.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        rviz_arg,
        sim_lidar,
        map_server,
        amcl,
        rviz_node,
        lifecycle_manager_localization,
        nav_nodes,
        nav_bringup,
    ])
