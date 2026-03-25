import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    frame_id = LaunchConfiguration('frame_id')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'use_sim': 'false',
            'use_lidar': 'true',
            'use_camera': 'false',
        }.items(),
    )

    base_driver = Node(
        package='my_bot',
        executable='diff_drive_base.py',
        name='base_driver',
        output='screen',
        parameters=[os.path.join(pkg_path, 'config', 'base_driver.yaml')],
    )

    lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rplidar_a1.launch.py')
        ),
        launch_arguments={
            'serial_port': serial_port,
            'serial_baudrate': serial_baudrate,
            'frame_id': frame_id,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('serial_port', default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'),
        DeclareLaunchArgument('serial_baudrate', default_value='115200'),
        DeclareLaunchArgument('frame_id', default_value='laser_frame'),
        rsp,
        base_driver,
        lidar,
    ])