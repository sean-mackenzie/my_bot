import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')

    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    frame_id = LaunchConfiguration('frame_id')
    use_rviz = LaunchConfiguration('use_rviz')
    rviz_config = LaunchConfiguration('rviz_config')

    real_base = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'real_base.launch.py')
        ),
        launch_arguments={
            'use_lidar': 'true',
            'use_camera': 'true',
            'use_rviz': use_rviz,
            'rviz_config': rviz_config,
        }.items(),
    )

    lidar_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rplidar_a1.launch.py')
        ),
        launch_arguments={
            'serial_port': serial_port,
            'serial_baudrate': serial_baudrate,
            'frame_id': frame_id,
        }.items(),
    )

    camera_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'pi_cam.launch.py')
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
            description='Serial port for the RPLIDAR A1',
        ),
        DeclareLaunchArgument(
            'serial_baudrate',
            default_value='115200',
            description='Baud rate for the RPLIDAR A1',
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='laser_frame',
            description='TF frame ID for the lidar',
        ),
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz2',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=os.path.join(pkg_path, 'rviz', 'config.rviz'),
            description='RViz config file',
        ),
        real_base,
        lidar_driver,
        camera_driver,
    ])