#!/usr/bin/env python3

import math
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
from builtin_interfaces.msg import Time as TimeMsg

import serial


class DiffDriveBase(Node):
    def __init__(self) -> None:
        super().__init__('diff_drive_base')

        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 57600)
        self.declare_parameter('wheel_radius', 0.05)
        self.declare_parameter('wheel_separation', 0.35)
        self.declare_parameter('encoder_ticks_per_rev', 360.0)
        self.declare_parameter('publish_rate_hz', 30.0)
        self.declare_parameter('cmd_timeout_sec', 0.5)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('left_joint_name', 'left_wheel_joint')
        self.declare_parameter('right_joint_name', 'right_wheel_joint')

        self.port = self.get_parameter('port').value
        self.baudrate = int(self.get_parameter('baudrate').value)
        self.wheel_radius = float(self.get_parameter('wheel_radius').value)
        self.wheel_separation = float(self.get_parameter('wheel_separation').value)
        self.encoder_ticks_per_rev = float(self.get_parameter('encoder_ticks_per_rev').value)
        self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self.cmd_timeout_sec = float(self.get_parameter('cmd_timeout_sec').value)
        self.odom_frame = str(self.get_parameter('odom_frame').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.left_joint_name = str(self.get_parameter('left_joint_name').value)
        self.right_joint_name = str(self.get_parameter('right_joint_name').value)

        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.serial_lock = threading.Lock()
        self.ser: Optional[serial.Serial] = None

        self.last_cmd_time = self.get_clock().now()
        self.left_cmd_rad_s = 0.0
        self.right_cmd_rad_s = 0.0

        self.left_ticks: Optional[int] = None
        self.right_ticks: Optional[int] = None
        self.prev_left_ticks: Optional[int] = None
        self.prev_right_ticks: Optional[int] = None
        self.prev_time = self.get_clock().now()

        self.left_pos = 0.0
        self.right_pos = 0.0
        self.left_vel = 0.0
        self.right_vel = 0.0

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        self.connect_serial()

        period = 1.0 / self.publish_rate_hz
        self.timer = self.create_timer(period, self.update)

        self.get_logger().info(f'Opened base driver on {self.port} @ {self.baudrate} baud')

    def connect_serial(self) -> None:
        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.02)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def cmd_callback(self, msg: Twist) -> None:
        v = float(msg.linear.x)
        w = float(msg.angular.z)

        self.left_cmd_rad_s = (v - 0.5 * self.wheel_separation * w) / self.wheel_radius
        self.right_cmd_rad_s = (v + 0.5 * self.wheel_separation * w) / self.wheel_radius
        self.last_cmd_time = self.get_clock().now()

    def send_command(self, left_rad_s: float, right_rad_s: float) -> None:
        if self.ser is None:
            return
        line = f'CMD {left_rad_s:.4f} {right_rad_s:.4f}\n'
        with self.serial_lock:
            self.ser.write(line.encode('utf-8'))

    def read_encoder_line(self) -> None:
        if self.ser is None:
            return
        with self.serial_lock:
            raw = self.ser.readline()

        if not raw:
            return

        try:
            line = raw.decode('utf-8', errors='ignore').strip()
        except Exception:
            return

        parts = line.split()
        if len(parts) != 3 or parts[0] != 'ENC':
            return

        try:
            self.left_ticks = int(parts[1])
            self.right_ticks = int(parts[2])
        except ValueError:
            return

    def update(self) -> None:
        now = self.get_clock().now()

        if (now - self.last_cmd_time).nanoseconds * 1e-9 > self.cmd_timeout_sec:
            left_cmd = 0.0
            right_cmd = 0.0
        else:
            left_cmd = self.left_cmd_rad_s
            right_cmd = self.right_cmd_rad_s

        self.send_command(left_cmd, right_cmd)
        self.read_encoder_line()

        if self.left_ticks is None or self.right_ticks is None:
            return

        if self.prev_left_ticks is None or self.prev_right_ticks is None:
            self.prev_left_ticks = self.left_ticks
            self.prev_right_ticks = self.right_ticks
            self.prev_time = now
            self.publish_joint_states(now.to_msg())
            self.publish_odom(now.to_msg(), 0.0, 0.0)
            return

        dt = (now - self.prev_time).nanoseconds * 1e-9
        if dt <= 0.0:
            return

        dleft_ticks = self.left_ticks - self.prev_left_ticks
        dright_ticks = self.right_ticks - self.prev_right_ticks

        rad_per_tick = 2.0 * math.pi / self.encoder_ticks_per_rev

        dleft = dleft_ticks * rad_per_tick
        dright = dright_ticks * rad_per_tick

        self.left_pos += dleft
        self.right_pos += dright
        self.left_vel = dleft / dt
        self.right_vel = dright / dt

        dl = dleft * self.wheel_radius
        dr = dright * self.wheel_radius
        dc = 0.5 * (dl + dr)
        dyaw = (dr - dl) / self.wheel_separation

        if abs(dyaw) < 1e-9:
            self.x += dc * math.cos(self.yaw)
            self.y += dc * math.sin(self.yaw)
        else:
            self.x += dc * math.cos(self.yaw + 0.5 * dyaw)
            self.y += dc * math.sin(self.yaw + 0.5 * dyaw)

        self.yaw += dyaw

        vx = dc / dt
        wz = dyaw / dt

        stamp = now.to_msg()
        self.publish_joint_states(stamp)
        self.publish_odom(stamp, vx, wz)
        self.publish_tf(stamp)

        self.prev_left_ticks = self.left_ticks
        self.prev_right_ticks = self.right_ticks
        self.prev_time = now

    def publish_joint_states(self, stamp: TimeMsg) -> None:
        msg = JointState()
        msg.header.stamp = stamp
        msg.name = [self.left_joint_name, self.right_joint_name]
        msg.position = [self.left_pos, self.right_pos]
        msg.velocity = [self.left_vel, self.right_vel]
        self.joint_pub.publish(msg)

    def publish_odom(self, stamp: TimeMsg, vx: float, wz: float) -> None:
        msg = Odometry()
        msg.header.stamp = stamp
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame

        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0

        qz = math.sin(self.yaw / 2.0)
        qw = math.cos(self.yaw / 2.0)
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        msg.twist.twist.linear.x = vx
        msg.twist.twist.angular.z = wz

        self.odom_pub.publish(msg)

    def publish_tf(self, stamp: TimeMsg) -> None:
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = self.odom_frame
        t.child_frame_id = self.base_frame

        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0

        t.transform.rotation.z = math.sin(self.yaw / 2.0)
        t.transform.rotation.w = math.cos(self.yaw / 2.0)

        self.tf_broadcaster.sendTransform(t)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DiffDriveBase()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.ser is not None:
            try:
                node.send_command(0.0, 0.0)
                node.ser.close()
            except Exception:
                pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()