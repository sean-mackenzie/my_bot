"""
sim_nav10.launch.py

Navigation launch file for my_bot in Gazebo simulation.

Architecture
------------
This launch file resolves the startup race condition present in sim_nav.launch.py
by splitting the Nav2 lifecycle management into two stages:

  Stage 1 (t = 3 s after sim start):
    lifecycle_manager_localization activates map_server and amcl.
    AMCL begins publishing the map -> odom transform.

  Stage 2 (t = 8 s after sim start):
    lifecycle_manager_navigation activates controller_server, smoother_server,
    planner_server, behavior_server, bt_navigator, and waypoint_follower.
    By this point, the map -> odom TF is available, so costmaps can configure
    without transform lookup failures.

The 5-second offset between stages provides margin for:
  - Gazebo physics engine initialization
  - gz_bridge topic establishment (/clock, /odom, /scan, /tf)
  - AMCL particle filter convergence to an initial estimate

Usage
-----
  ros2 launch my_bot sim_nav10.launch.py

  # With a custom map:
  ros2 launch my_bot sim_nav10.launch.py map:=/path/to/your_map.yaml

  # With RViz disabled (e.g., headless testing):
  ros2 launch my_bot sim_nav10.launch.py use_rviz:=false

After launch, set the initial pose in RViz using "2D Pose Estimate",
then send goals via "Nav2 Goal" (i.e., "2D Goal Pose").

References
----------
  S. Macenski et al., "The Marathon 2: A Navigation System,"
  J. Robotics & Autonomous Systems, 2023.
  https://github.com/ros-navigation/navigation2
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    # ── Launch arguments ──────────────────────────────────────────────
    map_arg = DeclareLaunchArgument(
        'map',
        default_value='/home/sean-mackenzie/my_world_map.yaml',
        description='Full path to the map YAML file produced by SLAM',
    )

    rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz with a navigation display configuration',
    )

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_path, 'config', 'nav2_params10.yaml'),
        description='Full path to the Nav2 parameter file',
    )

    map_file = LaunchConfiguration('map')
    use_rviz = LaunchConfiguration('use_rviz')
    params_file = LaunchConfiguration('params_file')

    # ── Stage 0: Gazebo + robot + bridges (via sim_lidar) ─────────────
    # sim_lidar.launch.py → launch_sim.launch.py, which:
    #   1. Starts robot_state_publisher (publishes base_link -> chassis, etc.)
    #   2. Launches Gazebo with the world
    #   3. Spawns the robot (5 s TimerAction)
    #   4. Starts gz_bridge for /clock, /cmd_vel, /odom, /tf, /joint_states
    #   5. Starts gz_bridge for /scan (lidar)
    sim_lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'sim_lidar.launch.py')
        )
    )

    # ── Localization nodes (map_server + amcl) ────────────────────────
    # These are launched immediately but remain in the 'unconfigured' state
    # until the lifecycle manager transitions them.
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            params_file,
            {'yaml_filename': map_file},
        ],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[params_file],
    )

    # ── Navigation nodes ──────────────────────────────────────────────
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file],
        remappings=[('cmd_vel', 'cmd_vel')],
    )

    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        output='screen',
        parameters=[params_file],
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file],
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[params_file],
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[params_file],
    )

    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[params_file],
    )

    # ── Stage 1: Lifecycle manager for localization ───────────────────
    # Delayed 3 s to allow Gazebo + bridges to initialize.
    # Transitions map_server and amcl through:
    #   unconfigured -> inactive -> active
    lifecycle_manager_localization = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    # ── Stage 2: Lifecycle manager for navigation ─────────────────────
    # Delayed an additional 5 s (8 s total) to ensure:
    #   - map_server is active and publishing /map
    #   - amcl is active and publishing the map -> odom TF
    #   - Costmaps can look up both map -> odom and odom -> base_link
    lifecycle_manager_navigation = TimerAction(
        period=8.0,
        actions=[
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    # ── RViz (optional) ───────────────────────────────────────────────
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

    # ── Assemble launch description ───────────────────────────────────
    return LaunchDescription([
        # Launch arguments
        map_arg,
        rviz_arg,
        params_arg,

        # Stage 0: simulation environment
        sim_lidar,

        # Localization nodes (launched unconfigured)
        map_server,
        amcl,

        # Navigation nodes (launched unconfigured)
        controller_server,
        smoother_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,

        # Stage 1: activate localization (t = 3 s)
        lifecycle_manager_localization,

        # Stage 2: activate navigation (t = 8 s)
        lifecycle_manager_navigation,

        # Visualization
        rviz_node,
    ])
