#!/usr/bin/env python3

import time

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


class WaitForSlamReady(Node):
    def __init__(self):
        super().__init__('wait_for_slam_ready')

        self.declare_parameter('warn_after_sec', 5.0)
        self.declare_parameter('stable_for_sec', 1.0)

        self.warn_after_sec = float(self.get_parameter('warn_after_sec').value)
        self.stable_for_sec = float(self.get_parameter('stable_for_sec').value)

        self.map_seen = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(OccupancyGrid, '/map', self.map_cb, 10)

        self.start_wall = time.monotonic()
        self.last_status_wall = 0.0
        self.ready_since_wall = None

        self.get_logger().info('Waiting for SLAM readiness: /map and TF map -> odom')

    def map_cb(self, msg):
        self.map_seen = True

    def map_to_odom_ready(self) -> bool:
        try:
            return self.tf_buffer.can_transform('map', 'odom', Time())
        except Exception:
            return False

    def base_ready(self) -> bool:
        return self.map_seen and self.map_to_odom_ready()

    def spin_until_ready(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)

            now = time.monotonic()
            ready = self.base_ready()

            if ready:
                if self.ready_since_wall is None:
                    self.ready_since_wall = now
                    self.get_logger().info(
                        'SLAM readiness checks passed. Waiting for stability window...'
                    )

                stable_elapsed = now - self.ready_since_wall
                if stable_elapsed >= self.stable_for_sec:
                    self.get_logger().info(
                        'SLAM is ready: /map active, TF map -> odom exists, '
                        'and readiness remained stable '
                        f'for {stable_elapsed:.2f} s'
                    )
                    return
            else:
                if self.ready_since_wall is not None:
                    self.get_logger().warn(
                        'SLAM readiness became false again during stability window; '
                        'resetting timer.'
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
                    'Still waiting for SLAM... '
                    f'map_seen={self.map_seen}, '
                    f'map_to_odom_ready={self.map_to_odom_ready()}, '
                    f'stable_window={stable_msg}'
                )


def main():
    rclpy.init()
    node = WaitForSlamReady()
    try:
        node.spin_until_ready()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
