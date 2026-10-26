#!/usr/bin/env python3
"""Receive newline-delimited JSON over localhost and publish /exercise/stats."""

import json
import socket

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

HOST = "127.0.0.1"
PORT = 8765


class ExercisePublisher(Node):
    def __init__(self):
        super().__init__("exercise_publisher")
        self.publisher = self.create_publisher(String, "/exercise/stats", 10)
        self.get_logger().info("Waiting for MediaPipe exercise data...")

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(1)
            server.settimeout(1.0)
            self.get_logger().info(f"Listening on {HOST}:{PORT}")

            while rclpy.ok():
                try:
                    connection, address = server.accept()
                except socket.timeout:
                    continue

                with connection:
                    self.get_logger().info(f"Connected to {address}")
                    with connection.makefile("r", encoding="utf-8") as stream:
                        for line in stream:
                            if not rclpy.ok():
                                break
                            try:
                                data = json.loads(line)
                                if not isinstance(data, dict):
                                    self.get_logger().warning(
                                        "Ignoring JSON message: expected an object"
                                    )
                                    continue
                                message = String()
                                message.data = json.dumps(data)
                                self.publisher.publish(message)
                                self.get_logger().info(f"Published: {message.data}")
                            except json.JSONDecodeError:
                                self.get_logger().warning("Invalid JSON received")
                    self.get_logger().info("Client disconnected; waiting for reconnect.")


def main(args=None):
    rclpy.init(args=args)
    node = ExercisePublisher()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
