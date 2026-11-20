#!/usr/bin/env bash
# Run inside the public simulator image with T2 copied to /tmp/rh/T2.
# No simulator, network sharing, devices, extra capabilities or mounts required.
set -o pipefail
source /opt/ros/humble/setup.bash
source /home/ros/go1_ws/install/setup.bash
set -u
export PYTHONPATH="/tmp/rh/T2${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
export ROS_DOMAIN_ID=152 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/ros/ros2_custom_config_setup/cyclonedds_local.xml
python3 /tmp/rh/T2/safety_node.py > /tmp/t2-test-node.log 2>&1 &
node=$!
cleanup() { kill "$node" 2>/dev/null || true; wait "$node" 2>/dev/null || true; }
trap cleanup EXIT
timeout 120s python3 /tmp/rh/T2/test_ros_safety.py
result=$?
printf '\n--- T2 node log ---\n'
tail -n 30 /tmp/t2-test-node.log
exit "$result"
