#!/usr/bin/env bash
set -euo pipefail

phase="${1:-}"
shift || true

if [[ "$phase" != "experiment" && "$phase" != "gradcam" && "$phase" != "analyze" ]]; then
  printf 'usage: %s {experiment|gradcam|analyze} [--seeds 1002]\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root="${V2_OUTPUT:-$repo_root/artifacts/v2}"
state_root="${V2_STATE_DIR:-/tmp/av2-paiva-v2}"
mkdir -p "$state_root"

full_run=false
forwarded_args=()
has_seeds=false
for argument in "$@"; do
  if [[ "$argument" == "--full" ]]; then
    full_run=true
  else
    forwarded_args+=("$argument")
    if [[ "$argument" == "--seeds" ]]; then
      has_seeds=true
    fi
  fi
done

if [[ "$phase" == "experiment" || "$phase" == "gradcam" ]] \
  && [[ "$full_run" == true ]]; then
  if [[ ! -f "$state_root/pilot-approved" ]]; then
    printf 'full V2 run requires pilot approval: %s\n' "$state_root/pilot-approved" >&2
    exit 1
  fi
  if [[ "$has_seeds" == true ]]; then
    printf '--full cannot be combined with --seeds\n' >&2
    exit 2
  fi
  forwarded_args+=(--seeds all)
  if [[ "$phase" == "experiment" ]]; then
    export V2_PILOT_APPROVED=1
  fi
elif [[ ( "$phase" == "experiment" || "$phase" == "gradcam" ) \
  && "$has_seeds" == false ]]; then
  forwarded_args+=(--seeds 1002)
fi

pid_path="$state_root/$phase.pid"
log_path="$state_root/$phase.log"
if [[ -f "$pid_path" ]]; then
  pid=$(<"$pid_path")
  process_args=$(ps -p "$pid" -o args= 2>/dev/null || true)
  if [[ "$process_args" == *"v2-$phase"* ]]; then
    printf '%s is already running with PID %s\n' "$phase" "$pid"
    exit 1
  fi
  rm -f "$pid_path"
fi

case "$phase" in
  experiment)
    command=(
      uv run experimento-feijao v2-experiment
      --config "$repo_root/protocol.json"
      --segmented-inputs "$repo_root/artifacts/segmented"
      --output "$output_root"
    )
    ;;
  gradcam)
    command=(
      uv run experimento-feijao v2-gradcam
      --config "$repo_root/protocol.json"
      --segmented-inputs "$repo_root/artifacts/segmented"
      --output "$output_root"
    )
    ;;
  analyze)
    command=(
      uv run experimento-feijao v2-analyze
      --results "$output_root"
      --output "$output_root/summary.json"
    )
    ;;
esac

command+=("${forwarded_args[@]}")
cd "$repo_root"
nohup "${command[@]}" >>"$log_path" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$pid_path"
printf 'Started %s with PID %s\n' "$phase" "$pid"
printf 'Log: %s\n' "$log_path"
printf 'Output: %s\n' "$output_root"
