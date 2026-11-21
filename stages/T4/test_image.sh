#!/usr/bin/env bash
set -euo pipefail
image=${1:?Participant image required}
simulator=${2:?Public simulator image required}
suffix=$$
network=t4-check-$suffix
sim=t4-sim-$suffix
participant=t4-participant-$suffix
cleanup() {
  docker logs --tail 100 "$sim" 2>/dev/null || true
  docker logs --tail 100 "$participant" 2>/dev/null || true
  docker rm -f "$sim" "$participant" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT

test "$(docker image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/amd64
test "$(docker image inspect "$image" --format '{{.Config.User}}')" = 10001:10001
ping=$(timeout 10s docker run --rm --network none "$image" ping)
python3 -c 'import json,sys; assert json.loads(sys.argv[1]) == dict(protocol_version="1.0",supported_tasks=["T4"],self_trained_rl=False,preferred_speed_mps=None)' "$ping"
docker run --rm --network none --entrypoint bash "$image" -c \
  'cd /opt/rh/T4; python3 -m unittest -v test_scan_match'

docker network create --internal "$network" >/dev/null
args=(--network "$network" -e ROS_DOMAIN_ID=154 -e ROS_LOCALHOST_ONLY=0 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e CYCLONEDDS_URI=)
docker run -d --name "$sim" "${args[@]}" --entrypoint bash --user 1000:1000 \
  "$simulator" -c '
    source /opt/ros/humble/setup.bash
    source /home/ros/go1_ws/install/setup.bash
    source /etc/go1_sim_env.sh
    exec ros2 launch go1_simulation scenario.launch.py scenario:=highlevel \
      gui:=false lockstep:=true cameras:=false
  '
docker run -d --name "$participant" "${args[@]}" "$image" T4
docker run --rm "${args[@]}" -e OPENBLAS_NUM_THREADS=1 --entrypoint bash "$image" -c '
  source /opt/ros/humble/setup.bash
  timeout 780s python3 /opt/rh/T4/test_gazebo.py
'
