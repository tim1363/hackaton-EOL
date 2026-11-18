#!/usr/bin/env bash
# Experimental participant entrypoint. Respect the infrastructure's DDS/domain
# settings and never start a simulator in the participant container.
set -eo pipefail
case "${1:-}" in
  ping)
    printf '%s\n' '{"protocol_version":"1.0","supported_tasks":["T2"],"self_trained_rl":false,"preferred_speed_mps":null}'
    ;;
  T2)
    source /opt/ros/humble/setup.bash
    source /home/ros/go1_ws/install/setup.bash
    export PYTHONPATH="/opt/rh/T2${PYTHONPATH:+:$PYTHONPATH}"
    export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
    exec python3 /opt/rh/T2/safety_node.py
    ;;
  *)
    printf '%s\n' 'Supported commands: ping, T2' >&2
    exit 64
    ;;
esac
