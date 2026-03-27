import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _bool_arg(context, name: str) -> bool:
    return LaunchConfiguration(name).perform(context).lower() in ('true', '1', 'yes')


def _launch_setup(context, *args, **kwargs):
    package_name = 'my_bot'
    pkg_path = get_package_share_directory(package_name)

    world = LaunchConfiguration('world').perform(context)
    use_lidar = _bool_arg(context, 'use_lidar')
    use_camera = _bool_arg(context, 'use_camera')
    use_teleop = _bool_arg(context, 'use_teleop')

    robot_description_raw = xacro.process_file(
        os.path.join(pkg_path, 'description', 'robot.urdf.xacro'),
        mappings={
            'use_sim': 'true',
            'use_lidar': 'true' if use_lidar else 'false',
            'use_camera': 'true' if use_camera else 'false',
        },
    ).toxml()

    actions = []

    # robot_state_publisher
    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_path, 'launch', 'rsp.launch.py')
            ),
            launch_arguments={
                'use_sim_time': 'true',
                'use_sim': 'true',
                'use_lidar': 'true' if use_lidar else 'false',
                'use_camera': 'true' if use_camera else 'false',
            }.items(),
        )
    )

    # Gazebo
    actions.append(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py',
                )
            ),
            launch_arguments={
                'gz_args': f'-r -v4 {world}',
                'on_exit_shutdown': 'true',
            }.items(),
        )
    )

    # Spawn robot
    actions.append(
        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='ros_gz_sim',
                    executable='create',
                    arguments=[
                        '-string', robot_description_raw,
                        '-name', 'my_bot',
                        '-z', '0.1',
                    ],
                    output='screen',
                )
            ],
        )
    )

    # ── Gazebo ↔ ROS bridge ──────────────────────────────────────────
    # Use a SINGLE bridge instance with a combined config file.
    # Multiple parameter_bridge instances share the default DDS node
    # name, causing discovery collisions that silently drop publishers.
    # One bridge = one DDS participant = no collisions.
    if use_lidar and not use_camera:
        bridge_config = os.path.join(pkg_path, 'config', 'gz_bridge_base_lidar.yaml')
    elif use_camera and not use_lidar:
        bridge_config = os.path.join(pkg_path, 'config', 'gz_bridge.yaml')
    elif use_lidar and use_camera:
        bridge_config = os.path.join(pkg_path, 'config', 'gz_bridge.yaml')
    else:
        bridge_config = os.path.join(pkg_path, 'config', 'gz_bridge_base.yaml')

    actions.append(
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '--ros-args',
                '-p',
                f'config_file:={bridge_config}',
            ],
            output='screen',
        )
    )

    # Camera image bridge (separate node — image_bridge is a different
    # executable from parameter_bridge, so no name collision)
    if use_camera:
        actions.append(
            Node(
                package='ros_gz_image',
                executable='image_bridge',
                arguments=['/camera/image_raw'],
                output='screen',
            )
        )

    # Optional keyboard teleop
    if use_teleop:
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_path, 'launch', 'teleop.launch.py')
                )
            )
        )

    return actions


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value=os.path.join(pkg_path, 'worlds', 'living_room.sdf'),
            description='World to load',
        ),
        DeclareLaunchArgument(
            'use_lidar',
            default_value='false',
            description='Spawn robot with simulated lidar',
        ),
        DeclareLaunchArgument(
            'use_camera',
            default_value='false',
            description='Spawn robot with simulated camera',
        ),
        DeclareLaunchArgument(
            'use_teleop',
            default_value='false',
            description='Launch keyboard teleop in a separate terminal',
        ),
        OpaqueFunction(function=_launch_setup),
    ])