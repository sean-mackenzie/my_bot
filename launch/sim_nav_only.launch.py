"""
sim_nav_only10.launch.py  — navigation stack only (state-aware bringup)

PREREQUISITE: sim_localization4.launch.py must be running in another terminal.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')
    nav2_params = os.path.join(pkg_path, 'config', 'nav2_params10.yaml')

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

    # State-aware lifecycle bringup script
    # Key fix: awk '{print $1}' extracts the state NAME (unconfigured, inactive, active)
    # from the output of 'ros2 lifecycle get', which formats as: "unconfigured [1]"
    bringup_script = r"""#!/bin/bash

bring_up_node() {
    local node="$1"
    local state

    # ros2 lifecycle get outputs: "unconfigured [1]" — $1 is the state name
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

    lifecycle_bringup = TimerAction(
        period=2.0,
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c', bringup_script],
                output='screen',
            )
        ],
    )

    return LaunchDescription([
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        lifecycle_bringup,
    ])
