#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


class WaitForRealReady(Node):
    def __init__(self):
        super().__init__('wait_for_real_ready')

        self.declare_parameter('warn_after_sec', 5.0)
        self.declare_parameter('stable_for_sec', 1.0)

        self.warn_after_sec = float(self.get_parameter('warn_after_sec').value)
        self.stable_for_sec = float(self.get_parameter('stable_for_sec').value)

        self.scan_seen = False
        self.odom_seen = False
        self.last_scan_stamp = None

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)

        self.start_wall = time.monotonic()
        self.last_status_wall = 0.0
        self.ready_since_wall = None

        self.get_logger().info(
            'Waiting for real robot readiness: /scan, /odom, '
            'TF odom -> base_link, TF base_link -> laser_frame, '
            'and TF odom -> laser_frame at the latest scan timestamp'
        )

    def scan_cb(self, msg):
        self.scan_seen = True
        self.last_scan_stamp = msg.header.stamp

    def odom_cb(self, msg):
        self.odom_seen = True

    def tf_ready(self, target_frame: str, source_frame: str) -> bool:
        try:
            return self.tf_buffer.can_transform(
                target_frame,
                source_frame,
                Time(),
            )
        except Exception:
            return False

    def base_ready(self) -> bool:
        return (
            self.scan_seen and
            self.odom_seen and
            self.tf_ready('odom', 'base_link') and
            self.tf_ready('base_link', 'laser_frame') and
            self.scan_tf_ready()
        )

    def scan_tf_ready(self) -> bool:
        if self.last_scan_stamp is None:
            return False
        try:
            return self.tf_buffer.can_transform(
                'odom',
                'laser_frame',
                Time.from_msg(self.last_scan_stamp),
            )
        except Exception:
            return False

    def spin_until_ready(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

            now = time.monotonic()
            ready = self.base_ready()

            if ready:
                if self.ready_since_wall is None:
                    self.ready_since_wall = now
                    self.get_logger().info(
                        'All readiness checks passed. Waiting for stability window...'
                    )

                stable_elapsed = now - self.ready_since_wall
                if stable_elapsed >= self.stable_for_sec:
                    self.get_logger().info(
                        'Real robot is ready: /scan active, /odom active, '
                        'TF odom -> base_link exists, TF base_link -> laser_frame exists, '
                        'TF odom -> laser_frame exists at the latest scan timestamp, '
                        'and readiness remained stable '
                        f'for {stable_elapsed:.2f} s'
                    )
                    return
            else:
                if self.ready_since_wall is not None:
                    self.get_logger().warn(
                        'Readiness became false again during stability window; resetting timer.'
                    )
                self.ready_since_wall = None

            elapsed = now - self.start_wall
            if elapsed > self.warn_after_sec and now - self.last_status_wall > 2.0:
                self.last_status_wall = now

                stable_msg = (
                    'not_started'
                    if self.ready_since_wall is None
                    else f'{now - self.ready_since_wall:.2f}s/{self.stable_for_sec:.2f}s'
                )

                self.get_logger().warn(
                    'Still waiting... '
                    f'scan_seen={self.scan_seen}, '
                    f'odom_seen={self.odom_seen}, '
                    f'odom_to_base_ready={self.tf_ready("odom", "base_link")}, '
                    f'base_to_laser_ready={self.tf_ready("base_link", "laser_frame")}, '
                    f'scan_tf_ready={self.scan_tf_ready()}, '
                    f'stable_window={stable_msg}'
                )


def main():
    rclpy.init()
    node = WaitForRealReady()
    try:
        node.spin_until_ready()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
