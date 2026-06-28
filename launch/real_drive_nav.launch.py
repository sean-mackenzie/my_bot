import os

from ament_index_python.packages import (
    PackageNotFoundError,
    get_package_share_directory,
)
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    required_nav2_packages = [
        'nav2_map_server',
        'nav2_amcl',
        'nav2_lifecycle_manager',
        'nav2_controller',
        'nav2_planner',
        'nav2_behaviors',
        'nav2_bt_navigator',
        'nav2_waypoint_follower',
        'slam_toolbox',
    ]
    missing_packages = []
    for package_name in required_nav2_packages:
        try:
            get_package_share_directory(package_name)
        except PackageNotFoundError:
            missing_packages.append(package_name)

    if missing_packages:
        missing_list = ', '.join(missing_packages)
        raise RuntimeError(
            'Missing required ROS packages for real_drive_nav.launch.py: '
            f'{missing_list}. Install the Nav2 stack in this ROS 2 '
            'environment, then rebuild and re-source the workspace.'
        )

    map_file = LaunchConfiguration('map')
    nav2_params = LaunchConfiguration('params_file')
    slam_params = LaunchConfiguration('slam_params_file')
    load_map = LaunchConfiguration('load_map')
    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    frame_id = LaunchConfiguration('frame_id')
    use_rviz = LaunchConfiguration('use_rviz')

    drive_lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'real_drive_lidar.launch.py')
        ),
        launch_arguments={
            'serial_port': serial_port,
            'serial_baudrate': serial_baudrate,
            'frame_id': frame_id,
        }.items(),
    )

    wait_for_real_ready = Node(
        package='my_bot',
        executable='wait_for_real_ready.py',
        name='wait_for_real_ready',
        output='screen',
        condition=IfCondition(load_map),
    )

    wait_for_slam_ready = Node(
        package='my_bot',
        executable='wait_for_slam_ready.py',
        name='wait_for_slam_ready',
        output='screen',
        condition=UnlessCondition(load_map),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py',
            )
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_params_file': slam_params,
        }.items(),
        condition=UnlessCondition(load_map),
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            nav2_params,
            {
                'use_sim_time': False,
                'yaml_filename': map_file,
                'topic_name': 'map',
                'frame_id': 'map',
            },
        ],
        condition=IfCondition(load_map),
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': False},
        ],
        condition=IfCondition(load_map),
    )

    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'bond_timeout': 60.0,
            'node_names': ['map_server', 'amcl'],
        }],
        condition=IfCondition(load_map),
    )

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

    lifecycle_manager_navigation = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': False,
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

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(pkg_path, 'rviz', 'nav2_view.rviz')],
        parameters=[{'use_sim_time': False}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=os.path.join(pkg_path, 'maps', 'my_real_apartment_v1.yaml'),
            description='Full path to the map yaml file to load',
        ),
        DeclareLaunchArgument(
            'load_map',
            default_value='true',
            description='Load a saved map with AMCL. If false, run SLAM instead.',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(pkg_path, 'config', 'nav2_params_real.yaml'),
            description='Full path to the real-robot Nav2 parameter file',
        ),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg_path, 'config', 'slam_toolbox.yaml'),
            description='Full path to the real-robot SLAM Toolbox parameter file',
        ),
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
            description='Serial port for the RPLidar A1',
        ),
        DeclareLaunchArgument(
            'serial_baudrate',
            default_value='115200',
            description='Baud rate for the RPLidar A1',
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='laser_frame',
            description='TF frame ID for the lidar',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz with the Nav2 display config',
        ),
        drive_lidar,
        slam,
        wait_for_slam_ready,
        wait_for_real_ready,
        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_for_real_ready,
                on_exit=[
                    map_server,
                    amcl,
                    lifecycle_manager_localization,
                    controller_server,
                    planner_server,
                    behavior_server,
                    bt_navigator,
                    waypoint_follower,
                    lifecycle_manager_navigation,
                    rviz_node,
                ],
            ),
            condition=IfCondition(load_map),
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=wait_for_slam_ready,
                on_exit=[
                    controller_server,
                    planner_server,
                    behavior_server,
                    bt_navigator,
                    waypoint_follower,
                    lifecycle_manager_navigation,
                    rviz_node,
                ],
            ),
            condition=UnlessCondition(load_map),
        ),
    ])
