import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_path = get_package_share_directory('my_bot')
    #use_rviz = LaunchConfiguration('use_rviz')
    #rviz_config = LaunchConfiguration('rviz_config')

    real_base = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'real_base.launch.py')
        ),
        launch_arguments={
            'use_lidar': 'false',
            'use_camera': 'true',
            #'use_rviz': use_rviz,
            #'rviz_config': rviz_config,
        }.items(),
    )

    camera_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'pi_cam.launch.py')
        )
    )

    """ This was for launching RViz from the same launch file, but I commented it out since I usually launch from headless SSH terminal and then separately
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
    """

    return LaunchDescription([
        real_base,
        camera_driver,
    ])