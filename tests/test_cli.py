from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["experimento-feijao", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_help_exposes_only_the_simple_experiment_operations() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    for operation in ("prepare", "run", "campaign", "analyze"):
        assert operation in result.stdout
    for removed_operation in ("validate", "pilot", "consolidate", "grad-cam"):
        assert removed_operation not in result.stdout


def test_analyze_prints_the_minimum_paired_summary(tmp_path: Path) -> None:
    results = tmp_path / "results"
    for seed in range(1001, 1031):
        pair = results / f"pair-{seed}"
        pair.mkdir(parents=True)
        pair.joinpath("result.json").write_text(
            json.dumps(
                {
                    "seed": seed,
                    "solucao_principal": {"macro_f1": 0.8, "accuracy": 0.9},
                    "solucao_contrafactual": {
                        "macro_f1": 0.6,
                        "accuracy": 0.7,
                    },
                }
            ),
            encoding="utf-8",
        )

    result = run_cli("analyze", "--results", str(results))

    assert result.returncode == 0, result.stderr
    assert "30 pares experimentais" in result.stdout
    assert "F1 macro" in result.stdout
    assert "valor-p" in result.stdout
