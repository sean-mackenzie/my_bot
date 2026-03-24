import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
    I commented out the RViz launch for now since I usually launch from headless SSH terminal and then separately
    launch RViz on VM for display. You can uncomment the RViz launch if you want to run everything

    Launch file for the real robot base. This will start the robot state publisher with the real robot description,
    and also start the RPLIDAR A1 driver node with static transforms. You can use
    the same launch file for the simulation, just set the use_sim argument to true in the rsp.launch.py file, 
    and it will use the simulated robot description instead.
    """
    pkg_path = get_package_share_directory('my_bot')

    use_lidar = LaunchConfiguration('use_lidar')
    use_camera = LaunchConfiguration('use_camera')
    #use_rviz = LaunchConfiguration('use_rviz')
    #rviz_config = LaunchConfiguration('rviz_config')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'use_sim': 'false',
            'use_lidar': use_lidar,
            'use_camera': use_camera,
        }.items(),
    )

    """rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
    )"""

    """DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Launch RViz2',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=os.path.join(pkg_path, 'rviz', 'config.rviz'),
            description='RViz config file',
        ),"""
    """rviz,"""

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_lidar',
            default_value='false',
            description='Include lidar frames in robot_description',
        ),
        DeclareLaunchArgument(
            'use_camera',
            default_value='false',
            description='Include camera frames in robot_description',
        ),
        rsp,
    ])