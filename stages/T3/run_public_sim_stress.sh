#!/usr/bin/env bash
# Run inside the isolated participant container after its T3 entrypoint starts.
# /tmp/rh/T3/evaluate_public_sim.py is the evaluator; this starts only a
# perturbed simulator and evaluator, never a second safety node or policy.
set -o pipefail
source /opt/ros/humble/setup.bash
source /home/ros/go1_ws/install/setup.bash
export PYTHONPATH="/opt/rh/T2:/tmp/rh/T3${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT
timeout 130s python3 /tmp/rh/T3/evaluate_public_sim.py > /tmp/stress-evaluation.log 2>&1 & evaluator=$!; pids+=("$evaluator")
python3 /tmp/rh/stress_public_sim.py --ros-args -p headless:=true > /tmp/stress-simulator.log 2>&1 & pids+=("$!")
wait "$evaluator"; result=$?
printf '\n--- evaluation ---\n'; tail -n 30 /tmp/stress-evaluation.log
printf '\n--- simulator ---\n'; tail -n 30 /tmp/stress-simulator.log
exit "$result"
