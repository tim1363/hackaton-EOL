#!/usr/bin/env bash
# Experimental public-image episode. Run inside an isolated container after
# copying T2, T3 and actor.npz to /tmp/rh; no host network/devices required.
set -o pipefail
source /opt/ros/humble/setup.bash
source /home/ros/go1_ws/install/setup.bash
set -u
export PYTHONPATH="/tmp/rh/T2:/tmp/rh/T3${PYTHONPATH:+:$PYTHONPATH}"
export GO1_POLICY_NPZ=/tmp/rh/actor.npz
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
export ROS_DOMAIN_ID=151 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/ros/ros2_custom_config_setup/cyclonedds_local.xml
pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT
if [[ ${GO1_SAFETY_TRACE:-0} == 1 ]]; then
    safety_script=/tmp/rh/T3/inspect_safety.py
else
    safety_script=/tmp/rh/T2/safety_node.py
fi
python3 "$safety_script" > /tmp/t2.log 2>&1 & pids+=("$!")
python3 /tmp/rh/T3/policy_node.py > /tmp/policy.log 2>&1 & pids+=("$!")
timeout 130s python3 /tmp/rh/T3/evaluate_public_sim.py > /tmp/evaluation.log 2>&1 & evaluator=$!; pids+=("$evaluator")
# Same public simulator executable and default model used by the lowlevel launch.
python3 /home/ros/go1_ws/src/go1_simulation/scripts/go1_mujoco.py --ros-args -p headless:=true > /tmp/simulator.log 2>&1 & pids+=("$!")
wait "$evaluator"; result=$?
printf '\n--- evaluation ---\n'; tail -n 30 /tmp/evaluation.log
printf '\n--- T2 ---\n'; tail -n 30 /tmp/t2.log
printf '\n--- policy ---\n'; tail -n 30 /tmp/policy.log
printf '\n--- simulator ---\n'; tail -n 30 /tmp/simulator.log
exit "$result"
