from __future__ import annotations

import json

import numpy as np

from experimento_feijao.analysis import analyze
from experimento_feijao.preparation import SEEDS


def _write_results(root, differences: list[float]) -> None:
    for seed, difference in zip(SEEDS, differences, strict=True):
        pair = root / "results" / f"pair-{seed}"
        branches = {}
        for branch, adjustment in (
            ("solucao_principal", difference / 2),
            ("solucao_contrafactual", -difference / 2),
        ):
            result = {
                "seed": seed,
                "branch": branch,
                "evaluation": {
                    "accuracy": 0.5 + adjustment,
                    "macro_f1": 0.5 + adjustment,
                },
                "predictions": [
                    {
                        "predicted_class": "healthy",
                    }
                ],
            }
            branch_path = pair / branch / "result.json"
            branch_path.parent.mkdir(parents=True, exist_ok=True)
            branch_path.write_text(json.dumps(result), encoding="utf-8")
            branches[branch] = str(branch_path)

        pair.mkdir(parents=True, exist_ok=True)
        (pair / "result.json").write_text(
            json.dumps({"seed": seed, "branches": branches}),
            encoding="utf-8",
        )


def test_analyze_uses_wilcoxon_for_non_normal_paired_differences(tmp_path):
    _write_results(tmp_path, [0.2] + [0.0] * 29)

    summary = analyze(tmp_path)

    test = summary["paired_macro_f1_difference"]["test"]
    assert test["name"] == "wilcoxon"
    assert test["zero_method"] == "wilcox"
    assert test["nonzero_count"] == 1
    assert test["ties"] is False
    assert test["normality"]["name"] == "shapiro_wilk"
    assert test["normality"]["normal"] is False


def test_analyze_uses_t_test_for_normal_paired_differences(tmp_path):
    differences = np.random.default_rng(1001).normal(0, 0.01, len(SEEDS))
    _write_results(tmp_path, differences.tolist())

    summary = analyze(tmp_path)

    assert summary["paired_macro_f1_difference"]["test"]["name"] == "paired_t"
    assert "paired_accuracy_difference" in summary
