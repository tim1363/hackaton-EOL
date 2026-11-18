#!/usr/bin/env bash
# Stage the verified actor outside Git, then build the T2+T3 participant image.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  printf 'Usage: %s /path/to/actor-104857600.npz image:tag\n' "$0" >&2
  exit 64
fi
actor=$1
image=$2
engine=${CONTAINER_ENGINE:-docker}
expected=7a0e0d2f83017c881e2590079c01b7b6dd7ccd27d66d7e522a81d61c1ce9e0cd
actual=$(sha256sum "$actor" | cut -d' ' -f1)
if [[ "$actual" != "$expected" ]]; then
  printf 'Actor SHA-256 mismatch; expected the documented ppo-v3 export.\n' >&2
  exit 1
fi
root=$(cd "$(dirname "$0")/../.." && pwd)
staging=$(mktemp -d)
trap 'rm -rf -- "$staging"' EXIT
mkdir -p "$staging/stages/T2" "$staging/stages/T3"
cp "$root/stages/T2/"{safety_node.py,safety_core.py} "$staging/stages/T2/"
cp -R "$root/stages/T2/model" "$staging/stages/T2/"
cp "$root/stages/T3/"{Dockerfile,entrypoint.sh,policy_node.py,policy_observation.py,numpy_policy.py} "$staging/stages/T3/"
cp "$actor" "$staging/actor.npz"
args=(build --platform linux/amd64 -f "$staging/stages/T3/Dockerfile" -t "$image")
if [[ -n "${BASE_IMAGE:-}" ]]; then
  args+=(--build-arg "BASE_IMAGE=$BASE_IMAGE")
fi
"$engine" "${args[@]}" "$staging"
