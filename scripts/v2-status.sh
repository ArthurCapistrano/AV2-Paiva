#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root="${V2_OUTPUT:-$repo_root/artifacts/v2}"
state_root="${V2_STATE_DIR:-/tmp/av2-paiva-v2}"

for phase in experiment gradcam analyze; do
  pid_path="$state_root/$phase.pid"
  if [[ -f "$pid_path" ]]; then
    pid=$(<"$pid_path")
    if kill -0 "$pid" 2>/dev/null; then
      printf '%s: running (PID %s)\n' "$phase" "$pid"
    else
      printf '%s: stopped (last PID %s)\n' "$phase" "$pid"
    fi
  else
    printf '%s: not started\n' "$phase"
  fi
done

completed=0
if [[ -d "$output_root/results" ]]; then
  for result in "$output_root"/results/pair-*/result.json; do
    if [[ -f "$result" ]]; then
      completed=$((completed + 1))
    fi
  done
fi
printf 'complete pairs: %s\n' "$completed"
printf 'output: %s\n' "$output_root"
