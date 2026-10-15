from __future__ import annotations

import json
from pathlib import Path

from experimento_feijao.v2 import _selected_seeds, analyze_v2


def _write_branch_result(
    output: Path,
    seed: int,
    branch: str,
    macro_f1: float,
    accuracy: float,
) -> None:
    branch_path = output / "results" / f"pair-{seed}" / branch
    branch_path.mkdir(parents=True)
    branch_path.joinpath("result.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seed": seed,
                "branch": branch,
                "evaluation": {
                    "macro_f1": macro_f1,
                    "accuracy": accuracy,
                },
            }
        ),
        encoding="utf-8",
    )


def test_v2_selected_seeds_preserve_protocol_order() -> None:
    assert _selected_seeds([1003, 1002]) == (1002, 1003)
    assert _selected_seeds(None)[0] == 1001


def test_v2_analyze_calculates_confidence_interval_without_training(
    tmp_path: Path,
) -> None:
    output = tmp_path / "v2"
    for seed, principal, counterfactual in (
        (1002, 0.8, 0.6),
        (1003, 0.75, 0.5),
    ):
        _write_branch_result(
            output, seed, "solucao_principal", principal, principal + 0.1
        )
        _write_branch_result(
            output,
            seed,
            "solucao_contrafactual",
            counterfactual,
            counterfactual + 0.1,
        )
        pair_path = output / "results" / f"pair-{seed}"
        pair_path.joinpath("result.json").write_text(
            json.dumps({"schema_version": 1, "seed": seed}),
            encoding="utf-8",
        )

    summary_path = output / "summary.json"
    summary = analyze_v2(output, summary_path)

    assert summary["pair_count"] == 2
    interval = summary["paired_macro_f1_difference"]["confidence_interval_95"]
    assert interval["lower_95"] < interval["mean"] < interval["upper_95"]
    assert summary_path.is_file()
