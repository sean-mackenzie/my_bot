import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# import xacro

def generate_launch_description():

    # Check if we're told to use sim time, sim, lidar, or camera
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_sim = LaunchConfiguration('use_sim')
    use_lidar = LaunchConfiguration('use_lidar')
    use_camera = LaunchConfiguration('use_camera')

    ## Process the URDF file
    #pkg_path = os.path.join(get_package_share_directory('my_bot'))
    #xacro_file = os.path.join(pkg_path,'description','robot.urdf.xacro')
    #robot_description_config = xacro.process_file(xacro_file).toxml()
    pkg_path = get_package_share_directory('my_bot')
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')

    robot_description = ParameterValue(
        Command([
            'xacro ',
            xacro_file,
            ' use_sim:=', use_sim,
            ' use_lidar:=', use_lidar,
            ' use_camera:=', use_camera,
        ]),
        value_type=str,
    )
    
    # Create a robot_state_publisher node to publish the robot's state to TF
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )

    # Removed the below because it conflicts with Gazebo's own joint state publisher
    # Optional (useful once you have joints; not required for a fixed box)
    #joint_state_publisher_gui = Node(
    #    package='joint_state_publisher_gui',
    #    executable='joint_state_publisher_gui',
    #    output='screen'
    #)

    # Launch!
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use sim time if true',
        ),
        DeclareLaunchArgument(
            'use_sim',
            default_value='false',
            description='Enable Gazebo-specific plugins in the xacro',
        ),
        DeclareLaunchArgument(
            'use_lidar',
            default_value='false',
            description='Include the lidar link/joint in robot_description',
        ),
        DeclareLaunchArgument(
            'use_camera',
            default_value='false',
            description='Include the camera link/joint in robot_description',
        ),
        node_robot_state_publisher,
    ])

    #return LaunchDescription([
    #    DeclareLaunchArgument(
    #        'use_sim_time',
    #        default_value='false',
    #        description='Use sim time if true'),

    #    node_robot_state_publisher,
    #    # joint_state_publisher_gui
    #])
