#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root="${V2_OUTPUT:-$repo_root/artifacts/v2}"
state_root="${V2_STATE_DIR:-/tmp/av2-paiva-v2}"

for phase in experiment gradcam analyze; do
  pid_path="$state_root/$phase.pid"
  if [[ -f "$pid_path" ]]; then
    pid=$(<"$pid_path")
    process_args=$(ps -p "$pid" -o args= 2>/dev/null || true)
    if [[ "$process_args" == *"v2-$phase"* ]]; then
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
    pair_dir=$(dirname "$result")
    if [[ -f "$result" \
      && -f "$pair_dir/solucao_principal/result.json" \
      && -f "$pair_dir/solucao_contrafactual/result.json" \
      && -f "$output_root/checkpoints/$(basename "$pair_dir")/solucao_principal.weights.h5" \
      && -f "$output_root/checkpoints/$(basename "$pair_dir")/solucao_contrafactual.weights.h5" ]]; then
      completed=$((completed + 1))
    fi
  done
fi
printf 'complete pairs: %s\n' "$completed"
printf 'output: %s\n' "$output_root"
