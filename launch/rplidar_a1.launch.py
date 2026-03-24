from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
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

        Node(
            package='rplidar_ros',
            executable='rplidar_node',
            name='rplidar_node',
            output='screen',
            parameters=[{
                'serial_port': LaunchConfiguration('serial_port'),
                'serial_baudrate': LaunchConfiguration('serial_baudrate'),
                'frame_id': LaunchConfiguration('frame_id'),
                'angle_compensate': True,
                'scan_mode': 'Standard',
                'inverted': False,
            }],
        ),
    ])