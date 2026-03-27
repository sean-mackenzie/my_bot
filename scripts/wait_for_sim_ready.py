#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan


class WaitForSimReady(Node):
    def __init__(self):
        super().__init__('wait_for_sim_ready')

        self.declare_parameter('warn_after_sec', 5.0)

        self.warn_after_sec = float(self.get_parameter('warn_after_sec').value)

        self.clock_seen = False
        self.scan_seen = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(Clock, '/clock', self.clock_cb, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)

        self.start_wall = time.monotonic()
        self.last_status_wall = 0.0

        self.get_logger().info(
            'Waiting for sim readiness: /clock, /scan, and TF odom -> base_link'
        )

    def clock_cb(self, msg):
        self.clock_seen = True

    def scan_cb(self, msg):
        self.scan_seen = True

    def tf_ready(self) -> bool:
        try:
            return self.tf_buffer.can_transform(
                'odom',
                'base_link',
                Time(),
            )
        except Exception:
            return False

    def ready(self) -> bool:
        return self.clock_seen and self.scan_seen and self.tf_ready()

    def spin_until_ready(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.ready():
                self.get_logger().info(
                    'Sim is ready: /clock active, /scan active, TF odom -> base_link exists'
                )
                return

            now = time.monotonic()
            elapsed = now - self.start_wall

            if elapsed > self.warn_after_sec and now - self.last_status_wall > 2.0:
                self.last_status_wall = now
                self.get_logger().warn(
                    f'Still waiting... clock_seen={self.clock_seen}, '
                    f'scan_seen={self.scan_seen}, tf_ready={self.tf_ready()}'
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