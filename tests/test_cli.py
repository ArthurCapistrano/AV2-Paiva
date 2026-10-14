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

    summary_path = tmp_path / "summary.json"
    result = run_cli(
        "analyze",
        "--results",
        str(results),
        "--output",
        str(summary_path),
    )

    assert result.returncode == 0, result.stderr
    assert "30 pares experimentais" in result.stdout
    assert "F1 macro" in result.stdout
    assert "Acurácia" in result.stdout
    assert "Diferenças pareadas" in result.stdout
    assert "valor-p" in result.stdout
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["pair_count"] == 30
    principal_mean = summary["metrics"]["macro_f1"]["solucao_principal"]["mean"]
    assert abs(principal_mean - 0.8) < 1e-12


def test_campaign_rejects_a_seed_list_outside_the_protocol(tmp_path: Path) -> None:
    configuration = tmp_path / "protocol.json"
    configuration.write_text(
        json.dumps({"dataset": {"version": "beans:0.1.0"}, "seeds": [1, 2, 3]}),
        encoding="utf-8",
    )

    result = run_cli(
        "campaign",
        "--config",
        str(configuration),
        "--segmented-inputs",
        str(tmp_path / "segmented"),
        "--output",
        str(tmp_path / "results"),
    )

    assert result.returncode == 2
    assert "30 fixed seeds" in result.stderr
