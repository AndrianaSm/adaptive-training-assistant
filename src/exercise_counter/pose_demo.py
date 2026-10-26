#!/usr/bin/env python3
"""TurtleBot ROS 2 camera -> MediaPipe arm-raise counter -> TCP JSON bridge."""

import json
import socket
import time
from pathlib import Path

import cv2
import mediapipe as mp
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Configuration
MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_lite.task"
IMAGE_TOPIC = "/image_raw"
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765
THRESHOLD = 0.08

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_WRIST = 15
RIGHT_WRIST = 16


class TurtleBotCamera(Node):
    def __init__(self):
        super().__init__("turtlebot_pose_demo")
        self.bridge = CvBridge()
        self.latest_frame = None
        self.subscription = self.create_subscription(
            Image, IMAGE_TOPIC, self.image_callback, 10
        )
        self.get_logger().info(f"Waiting for camera images on {IMAGE_TOPIC}...")

    def image_callback(self, msg):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(
                msg, desired_encoding="bgr8"
            )
        except Exception as error:
            self.get_logger().error(f"Could not convert camera image: {error}")


def connect_bridge():
    bridge = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bridge.settimeout(5)
    try:
        bridge.connect((BRIDGE_HOST, BRIDGE_PORT))
        bridge.settimeout(None)
        print("Connected to ROS 2 exercise publisher.")
        return bridge
    except OSError as error:
        bridge.close()
        raise RuntimeError(
            "Cannot connect to the ROS 2 publisher. Start exercise_publisher.py first."
        ) from error


def main(args=None):
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"MediaPipe model not found: {MODEL_PATH}\n"
            "Put pose_landmarker_lite.task in the same folder as pose_demo.py."
        )

    rclpy.init(args=args)
    node = TurtleBotCamera()
    bridge = None

    repetitions = 0
    arms_raised = False
    rep_start_time = None
    exercise_start_time = None
    last_rep_duration = None
    total_rep_duration = 0.0

    try:
        bridge = connect_bridge()
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            start_time = time.monotonic()
            previous_timestamp_ms = -1

            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.01)
                if node.latest_frame is None:
                    cv2.waitKey(1)
                    continue

                frame = node.latest_frame.copy()
                now = time.monotonic()
                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB, data=rgb_frame
                )
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                timestamp_ms = max(elapsed_ms, previous_timestamp_ms + 1)
                previous_timestamp_ms = timestamp_ms
                results = landmarker.detect_for_video(mp_image, timestamp_ms)

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks[0]
                    for landmark in landmarks:
                        x, y = int(landmark.x * width), int(landmark.y * height)
                        if 0 <= x < width and 0 <= y < height:
                            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

                    shoulders_y = (
                        landmarks[LEFT_SHOULDER].y + landmarks[RIGHT_SHOULDER].y
                    ) / 2
                    wrists_y = (
                        landmarks[LEFT_WRIST].y + landmarks[RIGHT_WRIST].y
                    ) / 2
                    raised = wrists_y < shoulders_y - THRESHOLD
                    lowered = wrists_y > shoulders_y + THRESHOLD

                    # Start when arms rise; complete when arms lower again.
                    if raised and not arms_raised:
                        arms_raised = True
                        rep_start_time = now
                        if exercise_start_time is None:
                            exercise_start_time = now
                    elif lowered and arms_raised:
                        arms_raised = False
                        if rep_start_time is not None:
                            last_rep_duration = now - rep_start_time
                            total_rep_duration += last_rep_duration
                            repetitions += 1
                            rep_start_time = None
                            exercise_duration = now - exercise_start_time

                            data = {
                                "exercise": "arm_raise",
                                "repetitions": repetitions,
                                "last_rep_duration": round(last_rep_duration, 2),
                                "exercise_duration": round(exercise_duration, 2),
                                "total_rep_duration": round(total_rep_duration, 2),
                            }
                            try:
                                bridge.sendall(
                                    (json.dumps(data) + "\n").encode("utf-8")
                                )
                                print("Published exercise data:", data)
                            except OSError as error:
                                node.get_logger().error(
                                    f"Bridge connection lost: {error}. "
                                    "Restart exercise_publisher.py and rerun pose_demo.py."
                                )
                                return

                    status = "ARMS RAISED" if arms_raised else "ARMS DOWN"
                    cv2.putText(frame, f"Repetitions: {repetitions}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.putText(frame, status, (20, 75),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

                    if last_rep_duration is not None:
                        cv2.putText(
                            frame, f"Last repetition: {last_rep_duration:.2f} s",
                            (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                            (0, 255, 255), 2,
                        )
                    if exercise_start_time is not None:
                        cv2.putText(
                            frame, f"Exercise duration: {now - exercise_start_time:.1f} s",
                            (20, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                            (255, 255, 255), 2,
                        )
                    cv2.putText(
                        frame, f"Total movement time: {total_rep_duration:.1f} s",
                        (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                        (255, 255, 255), 2,
                    )
                else:
                    cv2.putText(frame, "No person detected", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                cv2.imshow("TurtleBot Arm Raise Counter", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        if bridge is not None:
            bridge.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        cv2.destroyAllWindows()
        print("Exercise detector stopped.")


if __name__ == "__main__":
    main()
