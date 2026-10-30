# Adaptive Training Assistant (ROS 2 Jazzy)

A small ROS 2 Python package with two independent nodes:

1. **`exercise_counter`** subscribes to the TurtleBot camera topic, runs MediaPipe Pose Landmarker, counts both-arm raises, and publishes exercise metrics.
2. **`training_logic`** subscribes to completed-repetition events and publishes training feedback and set status.

The nodes are intended to run on the laptop/WSL Ubuntu ROS 2 environment, while the TurtleBot's Raspberry Pi publishes the camera frames. They do not open a local webcam.

## What the current detector recognizes

The detector counts one repetition when the average wrist position is above the average shoulder position by a threshold, then returns below the lower threshold. It is a basic **both-arm raise detector**, not a general exercise classifier or a form/safety assessment.

`/exercise/repetition_duration` measures the time from the detected raised position until the wrists return to the lowered threshold. It is the **raised phase duration**, not the full movement cycle. The first duration also starts when the raised threshold is crossed.

## Topics

| Topic | Type | Publisher / consumer | Meaning |
|---|---|---|---|
| `/image_raw` | `sensor_msgs/msg/Image` | TurtleBot camera → Exercise Counter | Camera frames (configurable) |
| `/exercise/repetitions` | `std_msgs/msg/Int32` | Exercise Counter | Cumulative completed repetition count |
| `/exercise/repetition_duration` | `std_msgs/msg/Float32` | Exercise Counter | Last raised-phase duration, seconds |
| `/exercise/duration` | `std_msgs/msg/Float32` | Exercise Counter | Elapsed time since the first detected arm raise, seconds; published twice per second |
| `/exercise/feedback` | `std_msgs/msg/String` | Exercise Counter | Vision state: `No person detected`, `Move into view`, `Ready`, `Arms raised`, or `Rep completed` |
| `/exercise/rep_event` | `std_msgs/msg/String` | Exercise Counter → Training Logic | JSON event containing count, raised-phase duration, and elapsed time for the same completed repetition |
| `/training/feedback` | `std_msgs/msg/String` | Training Logic | Human-readable coaching/status message |
| `/training/status` | `std_msgs/msg/String` | Training Logic | `WAITING_FOR_PERSON`, `READY`, `MOVEMENT_IN_PROGRESS`, `IN_PROGRESS`, or `SET_COMPLETE` |
| `/training/set_complete` | `std_msgs/msg/Bool` | Training Logic | True once the configured repetition goal is reached |
| `/training/vision_status` | `std_msgs/msg/String` | Training Logic | Forwards the Exercise Counter's current vision state |

The `/exercise/rep_event` JSON topic gives Training Logic one consistent event with all three values. The individual typed topics remain available for easier inspection and other consumers.

## Requirements

- Ubuntu 24.04 / ROS 2 Jazzy (the laptop/WSL environment)
- TurtleBot camera publishing a `sensor_msgs/msg/Image` topic visible to that environment
- Python 3.12-compatible `mediapipe` package
- Python dependencies listed in `requirements.txt`
- Same `ROS_DOMAIN_ID` on the robot and laptop, plus working ROS 2 DDS networking

## Install ROS dependencies

Run in Ubuntu/WSL, not in the normal macOS Terminal unless ROS 2 Jazzy is installed there:

```bash
sudo apt update
sudo apt install ros-jazzy-cv-bridge python3-colcon-common-extensions python3-venv python3-pip
```

If ROS 2 Jazzy is already installed, install only any missing packages.

## Add the package to the workspace

Extract this package under `~/ros_ws/src/` so the path is:

```text
~/ros_ws/src/adaptive_training_assistant/
```

In a terminal:

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ros_ws/src
cd ~/ros_ws/src
# Extract/copy the adaptive_training_assistant package directory here.
```

## Python environment and build

Use a virtual environment that can see the ROS installation's Python packages. Run the following in the Ubuntu/WSL terminal:

```bash
cd ~/ros_ws
python3 -m venv --system-site-packages .venv
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r src/adaptive_training_assistant/requirements.txt

# Sanity check: both imports should work before building/running.
python -c "import rclpy, mediapipe; print('rclpy and MediaPipe imports OK')"

colcon build --symlink-install --packages-select adaptive_training_assistant
source install/setup.bash
```

If `python3 -m venv` reports that a venv is already present, either reuse your existing ROS-compatible environment or create it under a different name. Keep the same environment active when building and launching so the node executable can import MediaPipe.

## Check the camera topic before launching

In every terminal, source ROS and the workspace, activate the same virtual environment, and set the matching domain ID:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros_ws/.venv/bin/activate
source ~/ros_ws/install/setup.bash
export ROS_DOMAIN_ID=102
ros2 topic list
ros2 topic info /image_raw
ros2 topic hz /image_raw
```

Use `ROS_DOMAIN_ID=102` only if that matches the value configured on your TurtleBot. Both devices must use the same domain ID, and DDS networking must allow them to discover each other. If your camera topic has a different name, use that name in the launch command.

## Run both nodes together

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros_ws/.venv/bin/activate
source ~/ros_ws/install/setup.bash
export ROS_DOMAIN_ID=102
ros2 launch adaptive_training_assistant training_assistant.launch.py
```

By default, this listens to `/image_raw`, hides the OpenCV preview (to reduce latency), and sets a goal of 10 repetitions. The MediaPipe model is downloaded automatically on first startup to:

```text
~/.cache/adaptive_training_assistant/pose_landmarker_lite.task
```

A later launch reuses that file. Internet access is required only for the first download unless you provide your own model file.

### Launch parameters

```bash
ros2 launch adaptive_training_assistant training_assistant.launch.py \
  image_topic:=/image_raw \
  show_preview:=false \
  target_repetitions:=10 \
  min_raised_phase_duration_seconds:=0.25 \
  max_raised_phase_duration_seconds:=4.0 \
  model_path:=""
```

Set `show_preview:=true` to display an OpenCV window with counters. Displaying the window can increase latency, especially in WSL, so leave it false for normal robot operation. Press `q` in the preview window to stop the node.

### Run nodes separately

Use two terminals (after sourcing ROS and the workspace and activating the venv in each):

```bash
ros2 run adaptive_training_assistant exercise_counter
```

```bash
ros2 run adaptive_training_assistant training_logic
```

If you run them separately, start Exercise Counter and Training Logic in the same ROS domain. Both can also be started with the launch file above.

## Inspect the output

In another sourced terminal:

```bash
ros2 topic echo /exercise/repetitions
ros2 topic echo /exercise/repetition_duration
ros2 topic echo /exercise/duration
ros2 topic echo /exercise/rep_event
ros2 topic echo /training/feedback
ros2 topic echo /training/status
ros2 topic echo /training/set_complete
```

`/exercise/repetition_duration` updates when a repetition is completed; `/exercise/duration` updates twice per second.

## Troubleshooting

- **No `/image_raw` topic:** check that the camera driver is running on the TurtleBot and that ROS 2 DDS discovery is working between the TurtleBot and laptop.
- **Topic exists but no repetitions:** make sure the full upper body and both wrists are visible. The detector needs both wrists and both shoulders to pass the landmark visibility threshold.
- **MediaPipe model download error:** check internet access, then rerun. Alternatively pass `model_path:=/absolute/path/to/pose_landmarker_lite.task` to the launch command.
- **`ModuleNotFoundError: mediapipe`:** activate the same virtual environment used during the build and install `requirements.txt` there, then rebuild the package.
- **OpenCV preview errors:** leave `show_preview:=false`; the node does not require a display to process frames.
- **Camera processing feels laggy:** keep `show_preview:=false`; this node uses sensor-data QoS and MediaPipe's video mode to help avoid stale camera-frame queues.
- **Counter doesn't reset between sets:** the current prototype starts at zero when the Exercise Counter node restarts. A reset service is not included yet.

## Current scope and limitations

- Detects both-arm raises only.
- `Training Logic` includes a configurable repetition goal and simple feedback based on the detected raised-phase duration.
- It does not recognize arbitrary exercises, verify correct technique, or provide medical advice.
- The repetition goal is completed once the count reaches `target_repetitions`; restart the nodes to begin a fresh counter in this prototype.
