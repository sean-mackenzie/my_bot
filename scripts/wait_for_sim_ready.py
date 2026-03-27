#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan


class WaitForSimReady(Node):
    def __init__(self):
        super().__init__('wait_for_sim_ready')

        self.declare_parameter('warn_after_sec', 5.0)
        self.declare_parameter('stable_for_sec', 1.0)

        self.warn_after_sec = float(self.get_parameter('warn_after_sec').value)
        self.stable_for_sec = float(self.get_parameter('stable_for_sec').value)

        self.clock_seen = False
        self.scan_seen = False
        self.odom_seen = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 10)

        self.start_wall = time.monotonic()
        self.last_status_wall = 0.0

        self.ready_since_wall = None

        self.get_logger().info(
            'Waiting for sim readiness: /clock, /scan, /odom, and TF odom -> base_link'
        )

    def clock_cb(self, msg):
        self.clock_seen = True

    def scan_cb(self, msg):
        self.scan_seen = True

    def odom_cb(self, msg):
        self.odom_seen = True

    def tf_ready(self) -> bool:
        try:
            return self.tf_buffer.can_transform(
                'odom',
                'base_link',
                Time(),
            )
        except Exception:
            return False

    def base_ready(self) -> bool:
        return (
            self.clock_seen and
            self.scan_seen and
            self.odom_seen and
            self.tf_ready()
        )

    def spin_until_ready(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

            now = time.monotonic()
            base_ready = self.base_ready()

            if base_ready:
                if self.ready_since_wall is None:
                    self.ready_since_wall = now
                    self.get_logger().info(
                        'All readiness checks passed. Waiting for stability window...'
                    )

                stable_elapsed = now - self.ready_since_wall
                if stable_elapsed >= self.stable_for_sec:
                    self.get_logger().info(
                        'Sim is ready: /clock active, /scan active, /odom active, '
                        'TF odom -> base_link exists, and readiness remained stable '
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
                    f'clock_seen={self.clock_seen}, '
                    f'scan_seen={self.scan_seen}, '
                    f'odom_seen={self.odom_seen}, '
                    f'tf_ready={self.tf_ready()}, '
                    f'stable_window={stable_msg}'
                )


def main():
    rclpy.init()
    node = WaitForSimReady()
    try:
        node.spin_until_ready()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()