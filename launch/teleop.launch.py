from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    cmd_vel_topic = LaunchConfiguration('cmd_vel_topic')

    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        prefix='xterm -e',
        output='screen',
        parameters=[{
            'stamped': False,
            'use_sim_time': True, # LaunchConfiguration('use_sim_time'),
            }],
        remappings=[('/cmd_vel', cmd_vel_topic)],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'cmd_vel_topic',
            default_value='/cmd_vel',
            description='Twist topic to publish keyboard teleop commands to',
        ),
        teleop,
    ])