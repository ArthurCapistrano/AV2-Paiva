#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root="${V2_OUTPUT:-$repo_root/artifacts/v2}"
state_root="${V2_STATE_DIR:-/tmp/av2-paiva-v2}"
pilot_pair="$output_root/results/pair-1002"

for required in \
  "$pilot_pair/result.json" \
  "$pilot_pair/solucao_principal/result.json" \
  "$pilot_pair/solucao_contrafactual/result.json" \
  "$output_root/checkpoints/pair-1002/solucao_principal.weights.h5" \
  "$output_root/checkpoints/pair-1002/solucao_contrafactual.weights.h5" \
  "$output_root/gradcam/pair-1002/solucao_principal/diagnostic.json" \
  "$output_root/gradcam/pair-1002/solucao_contrafactual/diagnostic.json"; do
  if [[ ! -f "$required" ]]; then
    printf 'missing pilot artifact: %s\n' "$required" >&2
    exit 1
  fi
done

mkdir -p "$state_root"
cd "$repo_root"
uv run experimento-feijao v2-analyze \
  --results "$output_root" \
  --output "$state_root/pilot-summary.json" >/dev/null

touch "$state_root/pilot-approved"
printf 'Full V2 campaign approved.\n'
