# TurtleBot Exercise Detector

## Files
- `pose_demo.py`: subscribes to `/image_raw`, processes images with MediaPipe, displays pose landmarks and arm-raise counts, and sends a JSON line for each completed repetition.
- `exercise_publisher.py`: receives those JSON lines on `127.0.0.1:8765` and publishes `std_msgs/msg/String` on `/exercise/stats`.

## Prerequisites
- Both scripts run on the same computer (the TCP bridge uses localhost).
- ROS 2 packages `rclpy`, `sensor_msgs`, `std_msgs`, and `cv_bridge` are available in the Pixi environment.
- Python packages `opencv` and `mediapipe` are installed.
- Place `pose_landmarker_lite.task` in the same folder as `pose_demo.py`.
- The TurtleBot publishes camera messages on `/image_raw`, and the Mac and robot share the same ROS 2 domain/network.

## Run
Terminal 1:
```bash
pixi run python exercise_publisher.py
```

Terminal 2:
```bash
pixi run python pose_demo.py
```

Optional Terminal 3:
```bash
pixi run ros2 topic echo /exercise/stats
```

Press `q` in the video window to stop `pose_demo.py`; use Ctrl+C to stop the publisher.

## Notes
A repetition starts when both wrists are sufficiently above shoulder height and completes when both wrists move below shoulder height. This is a basic demo based on landmark height thresholds, not a clinical movement assessment.
