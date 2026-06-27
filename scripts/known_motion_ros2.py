#!/usr/bin/env python3
"""
How to run:
0. navigate to the directory with this script
1. if you change the script, you may need to remake it executable: chmod +x known_motion_ros2.py
2. in a separate terminal,initialize the robot as if you were launching any run (e.g., ros2 launch my_bot real_drive_slam.launch.py)
2. launch something basic that publishes /cmd_vel and /odom
    * I tested: ros2 launch my_bot real_drive_full.launch.py and it worked. 
    * make sure you verify with: 
        ros2 topic list, 
        ros2 topic echo /odom --once, 
        ros2 topic info /cmd_vel
3.  and run one of the following commands:

* Calibrate forward motion:
    python3 known_motion_ros2.py --mode forward --distance 1.0 --speed 0.15
- Example: 
    odometry target: 1.00 m
    actual distance: 0.93 m
- Correction factor:
    correction = actual distance / odometry distance
    correction = 0.93 / 1.00 = 0.93
    --> so your wheel distance scale is too large by about 7%
    --> try adjusting your parameters accordingly: wheel_radius, encoder_ticks_per_rev

* Calibrate rotation:
    python3 known_motion_ros2.py --mode rotate --angle 360 --angular-speed 0.5
- Example: 
    odometry target: 360 deg
    actual distance: 330 deg
- Correction:
    for diff-drive robot, rotation is primarily dependent on wheel_separation
    so you could try adjusting that, or inspect your wheel kinematics. 
"""

import argparse
import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def yaw_from_quaternion(q):
    """
    Convert quaternion to yaw angle in radians.
    Assumes ROS quaternion ordering: x, y, z, w.
    """
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def normalize_angle(angle):
    """
    Normalize angle to [-pi, pi].
    """
    return math.atan2(math.sin(angle), math.cos(angle))


class KnownMotionNode(Node):
    def __init__(self, args):
        super().__init__("known_motion_node")

        self.mode = args.mode
        self.target_distance = abs(args.distance)
        self.target_angle = math.radians(args.angle)
        self.linear_speed = abs(args.speed)
        self.angular_speed = abs(args.angular_speed)

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.odom_sub = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10,
        )

        self.current_x = None
        self.current_y = None
        self.current_yaw = None

        self.start_x = None
        self.start_y = None
        self.last_yaw = None
        self.accumulated_yaw = 0.0

        self.done = False

        self.timer = self.create_timer(0.02, self.control_loop)

        self.get_logger().info(f"Mode: {self.mode}")

    def odom_callback(self, msg):
        pose = msg.pose.pose

        self.current_x = pose.position.x
        self.current_y = pose.position.y
        self.current_yaw = yaw_from_quaternion(pose.orientation)

    def publish_stop(self):
        msg = Twist()
        self.cmd_pub.publish(msg)

    def control_loop(self):
        if self.done:
            return

        if self.current_x is None or self.current_y is None or self.current_yaw is None:
            self.get_logger().info("Waiting for /odom...", throttle_duration_sec=1.0)
            return

        if self.start_x is None:
            self.start_x = self.current_x
            self.start_y = self.current_y
            self.last_yaw = self.current_yaw
            self.get_logger().info("Starting motion.")
            return

        cmd = Twist()

        if self.mode == "forward":
            dx = self.current_x - self.start_x
            dy = self.current_y - self.start_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < self.target_distance:
                cmd.linear.x = self.linear_speed
                self.cmd_pub.publish(cmd)
            else:
                self.publish_stop()
                self.done = True
                self.get_logger().info(f"Done. Odometry distance: {distance:.3f} m")
                rclpy.shutdown()

        elif self.mode == "rotate":
            dyaw = normalize_angle(self.current_yaw - self.last_yaw)
            self.accumulated_yaw += dyaw
            self.last_yaw = self.current_yaw

            direction = 1.0 if self.target_angle >= 0.0 else -1.0
            target_abs = abs(self.target_angle)

            if abs(self.accumulated_yaw) < target_abs:
                cmd.angular.z = direction * self.angular_speed
                self.cmd_pub.publish(cmd)
            else:
                self.publish_stop()
                self.done = True
                self.get_logger().info(
                    f"Done. Odometry angle: {math.degrees(self.accumulated_yaw):.2f} deg"
                )
                rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=["forward", "rotate"],
        required=True,
        help="Motion mode: forward or rotate",
    )

    parser.add_argument(
        "--distance",
        type=float,
        default=1.0,
        help="Forward distance in meters",
    )

    parser.add_argument(
        "--angle",
        type=float,
        default=360.0,
        help="Rotation angle in degrees",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=0.15,
        help="Forward speed in m/s",
    )

    parser.add_argument(
        "--angular-speed",
        type=float,
        default=0.5,
        help="Angular speed in rad/s",
    )

    args = parser.parse_args()

    rclpy.init()
    node = KnownMotionNode(args)
    rclpy.spin(node)


if __name__ == "__main__":
    main()