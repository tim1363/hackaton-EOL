#!/usr/bin/env bash
set -eo pipefail

image=${1:?Pass the T2 image name}
test "$(docker image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/amd64
test "$(docker image inspect "$image" --format '{{.Config.User}}')" = '10001:10001'
ping=$(timeout 10s docker run --rm --network none "$image" ping)
python3 -c 'import json, sys; assert json.loads(sys.argv[1]) == dict(protocol_version="1.0", supported_tasks=["T2"], self_trained_rl=False, preferred_speed_mps=None)' "$ping"
printf '%s\n' "$ping"

docker run --rm --network none --entrypoint bash \
  -e ROS_LOCALHOST_ONLY=1 -e T2_TEST_WALL_TICK=0.01 "$image" -c '
    set -eo pipefail
    test "$(id -u)" = 10001
    source /opt/ros/humble/setup.bash
    source /opt/unitree/local_setup.bash
    export PYTHONPATH="/opt/rh/T2${PYTHONPATH:+:$PYTHONPATH}"
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    cd /opt/rh/T2
    python3 -m unittest -v test_safety_core
    /entrypoint.sh T2 >/tmp/t2-node.log 2>&1 &
    node=$!
    cleanup() {
      kill "$node" 2>/dev/null || true
      wait "$node" 2>/dev/null || true
      cat /tmp/t2-node.log
    }
    trap cleanup EXIT
    timeout 120s python3 test_ros_safety.py
    kill -0 "$node"
  '
