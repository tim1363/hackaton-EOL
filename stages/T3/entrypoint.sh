#!/usr/bin/env bash
set -eo pipefail
case "${1:-}" in
  ping)
    printf '%s\n' '{"protocol_version":"1.0","supported_tasks":["T2","T3"],"self_trained_rl":true,"preferred_speed_mps":0.4}'
    exit 0
    ;;
  T2|T3) ;;
  *)
    printf '%s\n' 'Supported commands: ping, T2, T3' >&2
    exit 64
    ;;
esac

source /opt/ros/humble/setup.bash
source /opt/unitree/local_setup.bash
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1

if [[ $1 == T2 ]]; then
  exec python3 /opt/rh/T2/safety_node.py
fi
python3 /opt/rh/T2/safety_node.py &
safety=$!
python3 /opt/rh/T3/residual_node.py &
policy=$!
cleanup() {
  kill "$safety" "$policy" 2>/dev/null || true
  wait "$safety" "$policy" 2>/dev/null || true
}
trap 'cleanup; exit 143' TERM
trap 'cleanup; exit 130' INT
set +e
wait -n "$safety" "$policy"
status=$?
cleanup
if [[ $status == 0 ]]; then
  status=1
fi
exit "$status"
