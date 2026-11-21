#!/usr/bin/env bash
set -euo pipefail
image=${1:?Participant image required}
simulator=${2:?Public simulator image required}
episodes=${3:-10}
prefix=t3-check-$$
workspace=$(mktemp -d)
cleanup() {
  for index in $(seq 1 "$episodes"); do
    docker rm -f "$prefix-sim-$index" "$prefix-participant-$index" "$prefix-driver-$index" >/dev/null 2>&1 || true
    docker network rm "$prefix-net-$index" >/dev/null 2>&1 || true
  done
  rm -f "$workspace"/episode-*.log
  rmdir "$workspace"
}
trap cleanup EXIT
test "$(docker image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/amd64
test "$(docker image inspect "$image" --format '{{.Config.User}}')" = 10001:10001
ping=$(timeout 10s docker run --rm --network none "$image" ping)
python3 -c 'import json,sys; assert json.loads(sys.argv[1]) == dict(protocol_version="1.0",supported_tasks=["T2","T3"],self_trained_rl=True,preferred_speed_mps=.4)' "$ping"
docker run --rm --network none --entrypoint bash "$image" -c \
  'cd /opt/rh/T3; python3 -m unittest -v test_residual_policy'

episode() {
  local index=$1 network=$prefix-net-$1 sim=$prefix-sim-$1 participant=$prefix-participant-$1
  local driver=$prefix-driver-$1
  docker network create --internal "$network" >/dev/null
  local args=(--network "$network" -e ROS_DOMAIN_ID=153 -e ROS_LOCALHOST_ONLY=0 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e CYCLONEDDS_URI=)
  docker run -d --name "$sim" "${args[@]}" --entrypoint bash --user 1000:1000 "$simulator" -c '
    source /opt/ros/humble/setup.bash
    source /home/ros/go1_ws/install/setup.bash
    source /etc/go1_sim_env.sh
    exec ros2 launch go1_simulation scenario.launch.py scenario:=lowlevel gui:=false
  '
  docker run -d --name "$participant" "${args[@]}" "$image" T3
  if ! docker run --rm --name "$driver" "${args[@]}" --entrypoint bash "$image" -c '
    source /opt/ros/humble/setup.bash
    source /opt/unitree/local_setup.bash
    timeout 190s python3 /opt/rh/T3/evaluate_public_sim.py
  '; then
    docker logs --tail 80 "$sim" >&2
    docker logs --tail 80 "$participant" >&2
    return 1
  fi
  docker rm -f "$sim" "$participant" >/dev/null
  docker network rm "$network" >/dev/null
}

for ((index=1; index<=episodes; index+=2)); do
  episode "$index" >"$workspace/episode-$index.log" 2>&1 &
  first=$!
  second=
  if (( index < episodes )); then
    episode "$((index+1))" >"$workspace/episode-$((index+1)).log" 2>&1 &
    second=$!
  fi
  status=0
  wait "$first" || status=1
  if [[ -n "$second" ]]; then wait "$second" || status=1; fi
  cat "$workspace/episode-$index.log"
  if [[ -n "$second" ]]; then cat "$workspace/episode-$((index+1)).log"; fi
  (( status == 0 ))
done

python3 - "$episodes" "$workspace" <<'PY'
import json
import sys
from pathlib import Path

count = int(sys.argv[1])
logs = Path(sys.argv[2])
prefix = "PUBLIC_T3_RESULT="
results = [json.loads(line[len(prefix):]) for path in sorted(logs.glob("episode-*.log"))
           for line in path.read_text().splitlines() if line.startswith(prefix)]
assert len(results) == count
passed = [row for row in results if row["success"] and row["bare_count"] > 0 and row["safe_count"] > 0]
print(f"PUBLIC_T3_SUMMARY={len(passed)}/{count}")
assert len(passed) >= (7 * count + 9) // 10
PY
