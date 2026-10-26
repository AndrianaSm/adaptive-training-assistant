# Adaptive Training Assistant

A Python and ROS 2 project that uses the TurtleBot camera and MediaPipe to detect exercises and count repetitions.

## Requirements

- Ubuntu 24.04 / WSL2
- ROS 2 Jazzy
- Python 3.12
- TurtleBot camera publishing images to `/image_raw`

## Setup

From the project root:

```bash
cd ~/adaptive-training-assistant
source /opt/ros/jazzy/setup.bash
```

Create the virtual environment only if it does not already exist:

```bash
python3 -m venv .venv
```

Activate it and install the Python dependencies:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

The publisher and pose detector communicate over a local TCP connection, so run them in separate terminals.

### Terminal 1 — Exercise publisher

```bash
cd ~/adaptive-training-assistant
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
python src/exercise_counter/exercise_publisher.py
```

The publisher listens on `127.0.0.1:8765` and publishes received exercise statistics to the ROS 2 topic `/exercise/stats`. Keep this terminal running.

### Terminal 2 — Pose detector

```bash
cd ~/adaptive-training-assistant
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
python src/exercise_counter/pose_demo.py
```

The detector subscribes to `/image_raw`, processes the camera images, and sends exercise statistics to the publisher. Press `Ctrl+C` to stop a process.

## Check the topics

To check that the camera topic is available:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list
ros2 topic hz /image_raw
```

To view exercise statistics published by the publisher, open another terminal and run:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /exercise/stats
```

## Troubleshooting

- **No camera images:** Make sure the camera node is running on the TurtleBot and publishing to `/image_raw`.
- **No `/image_raw` topic:** Check that the TurtleBot and computer can discover each other over ROS 2. Ensure they use compatible DDS/network settings and the same `ROS_DOMAIN_ID`.
- **No exercise statistics:** Make sure both `exercise_publisher.py` and `pose_demo.py` are running. The publisher should show that it is listening on port `8765`.
- **MediaPipe not found:** Activate `.venv` before running the Python scripts.
