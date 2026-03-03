import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    camera_node = Node(
        package='camera_ros',
        executable='camera_node',
        name='camera',
        namespace='camera',
        parameters=[{
            # Width and height must match a supported mode for the IMX219.
            # 640x480 is the lightest mode; increase to 1640x1232 if bandwidth allows.
            'width': 640,
            'height': 480,
            # Format must match what camera_ros exposes for the IMX219.
            # Leave unset to use the driver default (usually YUV or RGB).
        }],
        remappings=[
            # Remap camera_ros default topics to match our simulation topic names
            # so that the same RViz config and bridge work for both sim and real.
            ('~/image_raw', '/camera/image_raw'),
            ('~/camera_info', '/camera/camera_info'),
        ],
        output='screen'
    )

    return LaunchDescription([
        camera_node,
    ])