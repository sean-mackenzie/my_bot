import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    frame_id = LaunchConfiguration('frame_id')

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

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py'
            )
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_params_file': os.path.join(pkg_path, 'config', 'slam_toolbox.yaml'),
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
        ),
        DeclareLaunchArgument(
            'serial_baudrate',
            default_value='115200'
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='laser_frame'
        ),
        drive_lidar,
        slam,
    ])