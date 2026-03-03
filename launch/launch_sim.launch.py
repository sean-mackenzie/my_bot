import os
import xacro

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():

    package_name = 'my_bot'
    pkg_path = get_package_share_directory(package_name)

    # =========================================================================
    # Process xacro -> raw URDF string at launch construction time.
    # Used by both robot_state_publisher (via rsp.launch.py parameter override)
    # and ros_gz_sim create (via -string argument).
    # =========================================================================
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')
    robot_description_raw = xacro.process_file(xacro_file).toxml()

    # =========================================================================
    # robot_state_publisher + joint_state_publisher
    # We reinstate rsp.launch.py so that joint_state_publisher is also launched.
    # Without joint_state_publisher, the TF tree is incomplete (wheel/caster
    # joints have no state), and RViz cannot render the robot model.
    # We override the robot_description parameter with the pre-processed URDF
    # string to avoid the xacro subprocess race condition, while keeping the
    # joint_state_publisher that rsp.launch.py provides.
    # =========================================================================
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            pkg_path, 'launch', 'rsp.launch.py'
        )]),
        launch_arguments={
            'use_sim_time': 'true',
            'robot_description': robot_description_raw,  # override xacro subprocess
        }.items()
    )

    # =========================================================================
    # World argument
    # =========================================================================
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_path, 'worlds', 'living_room.sdf'),
        description='World to load'
    )
    world = LaunchConfiguration('world')

    # =========================================================================
    # Gazebo Sim
    # =========================================================================
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
        )]),
        launch_arguments={
            'gz_args': ['-r -v4 ', world],
            'on_exit_shutdown': 'true'
        }.items()
    )

    # =========================================================================
    # Spawn entity — passes the URDF XML string directly via -string to
    # bypass the QoS race condition on the robot_description topic.
    # TimerAction(5.0s) ensures the Gazebo world and service endpoints are
    # fully initialized before the spawn request is issued.
    # =========================================================================
    spawn_entity = TimerAction(
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
                output='screen'
            )
        ]
    )

    # =========================================================================
    # ROS-Gazebo bridge — normal topics (clock, tf, odom, scan, camera_info)
    # =========================================================================
    bridge_params = os.path.join(pkg_path, 'config', 'gz_bridge.yaml')
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '--ros-args',
            '-p', f'config_file:={bridge_params}',
        ],
        output='screen'
    )

    # =========================================================================
    # ROS-Gazebo image bridge
    # sensor_msgs/Image requires the dedicated image_bridge node from
    # ros_gz_image. If /camera/image_raw does not appear after launch, run:
    #   gz topic -l | grep -iE "camera|image"
    # to find the fully-scoped Gazebo topic path and update the argument below.
    # =========================================================================
    ros_gz_image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    return LaunchDescription([
        world_arg,
        rsp,
        gazebo,
        spawn_entity,
        ros_gz_bridge,
        ros_gz_image_bridge,
    ])