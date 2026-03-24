from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
    Lidar launch file that is intended to only run on the Pi to test/verify the lidar is working.
    
    Launch file for the RPLIDAR A1. This will start the ROS2 node that interfaces with the lidar, 
    and also publish static transforms for the laser frame and base link (required to view in RViz).
    """

    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
        description='Serial port for the RPLIDAR A1'
    )

    serial_baudrate_arg = DeclareLaunchArgument(
        'serial_baudrate',
        default_value='115200',
        description='Baud rate for the RPLIDAR A1'
    )

    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='laser_frame',
        description='TF frame ID for the lidar'
    )

    """ 
    The below is if you want to use the sllidar_ros2 package instead of rplidar_ros. 
    You will need to change the package and executable names, and adjust the parameters accordingly.
    
    sllidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        output='screen',
        parameters=[{
            'serial_port':      LaunchConfiguration('serial_port'),
            'serial_baudrate':  LaunchConfiguration('serial_baudrate'),
            'frame_id':         LaunchConfiguration('frame_id'),
            'angle_compensate': True,
            'scan_mode':        'Standard',
            'inverted':         False,
        }]
    )
    """

    rplidar_node = Node(
        package='rplidar_ros',
        executable='rplidar_node',
        name='rplidar_node',
        output='screen',
        parameters=[{
            'serial_port':      LaunchConfiguration('serial_port'),
            'serial_baudrate':  LaunchConfiguration('serial_baudrate'),
            'frame_id':         LaunchConfiguration('frame_id'),
            'angle_compensate': True,
            'scan_mode':        'Standard',
            'inverted':         False,
        }]
    )

    # Static transforms — remove these once robot_state_publisher
    # is loading your full URDF in a combined launch file
    base_to_laser_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_to_laser_tf',
        arguments=['0', '0', '0',
                   '0', '0', '0',
                   'base_link', 'laser_frame']
    )

    odom_to_base_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='odom_to_base_tf',
        arguments=['0', '0', '0',
                   '0', '0', '0',
                   'odom', 'base_link']
    )

    return LaunchDescription([
        serial_port_arg,
        serial_baudrate_arg,
        frame_id_arg,
        # sllidar_node,
        rplidar_node,
        base_to_laser_tf,
        odom_to_base_tf,
    ])