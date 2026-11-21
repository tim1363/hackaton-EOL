#!/usr/bin/env bash
set -eo pipefail
case "${1:-}" in
  ping)
    printf '%s\n' '{"protocol_version":"1.0","supported_tasks":["T4"],"self_trained_rl":false,"preferred_speed_mps":null}'
    ;;
  T4)
    source /opt/ros/humble/setup.bash
    export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
    exec python3 /opt/rh/T4/odom_prototype.py
    ;;
  *)
    printf '%s\n' 'Supported commands: ping, T4' >&2
    exit 64
    ;;
esac
