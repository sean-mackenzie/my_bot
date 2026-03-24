import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """
    Launch the camera node and a republisher to convert
    raw images to compressed JPEG for efficient transmission.
    
    Documentation: https://docs.ros.org/en/jazzy/p/camera_ros/index.html
    Static Camera Stream Configuration parameters:
    - width: Image width in pixels (e.g., 320, 640, 164)
    - height: Image height in pixels (e.g., 240, 480, 1232)
    - format: Image encoding format (e.g., 'RGB888', 'YUV422')
        - 'RGB888' matches the IMX219's RAW→RGB output and is suitable for our use case.
        - 'YUV422' may be the default format from the driver but can be more complex to handle.
    - FrameDurationLimits: Desired frame duration range in microseconds 
        - (66666, 66666) for 15 FPS
        - (33333, 33333) for 30 FPS, etc.
    - role: 'raw', 'still', 'video', default: 'viewfinder'
    - sensor_mode: desired raw sensor format resolution (format: width:height) [default: auto]
    - jpeg_quality: 0-100, lower = smaller but more lossy 
    """

    camera_node = Node(
        package='camera_ros',
        executable='camera_node',
        name='camera',
        namespace='camera',
        parameters=[{
            # Width and height must match a supported mode for the IMX219.
            # 640x480 is the lightest mode; increase to 1640x1232 if bandwidth allows.
            'width': 320,  # 640,
            'height': 240,  # 480,
            # Format must match what camera_ros exposes for the IMX219.
            # Leave unset to use the driver default (usually YUV or RGB).
            'format': 'RGB888',
            # Set the desired frame rate control
            # 'FrameDurationLimits': (66666, 66666),  # 15 FPS is a good balance for real-time control.
        }],
        remappings=[
            # Remap camera_ros default topics to match our simulation topic names
            # so that the same RViz config and bridge work for both sim and real.
            ('~/image_raw', '/camera/image_raw'),
            ('~/camera_info', '/camera/camera_info'),
        ],
        output='screen'
    )

    # Republish the raw stream as compressed JPEG for network transmission.
    # This reduces bandwidth from ~27 MB/s to ~1-2 MB/s over WiFi.
    compressed_republisher = Node(
        package='image_transport',
        executable='republish',
        name='image_republisher',
        arguments=['raw', 'compressed'],
        remappings=[
            ('in', '/camera/image_raw'),
            ('out/compressed', '/camera/image_raw/compressed'),
        ],
        parameters=[{
            'compressed.jpeg_quality': 40,  # 0-100, lower = smaller but lossier
        }],
        output='screen'
    )

    return LaunchDescription([
        camera_node,
        compressed_republisher,
    ])