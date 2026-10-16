from __future__ import annotations

import json
from pathlib import Path

from experimento_feijao.v2 import (
    _branch_result_path,
    _checkpoint_path,
    _complete_branch,
    _selected_seeds,
    analyze_v2,
)


def _write_branch_result(
    output: Path,
    seed: int,
    branch: str,
    macro_f1: float,
    accuracy: float,
) -> None:
    branch_path = output / "results" / f"pair-{seed}" / branch
    branch_path.mkdir(parents=True)
    checkpoint = output / "checkpoints" / f"pair-{seed}" / f"{branch}.weights.h5"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(b"checkpoint")
    branch_path.joinpath("result.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seed": seed,
                "branch": branch,
                "best_epoch": 1,
                "best_validation_loss": 1.0,
                "training_seconds": 1.0,
                "history": [{"epoch": 1, "loss": 1.0, "val_loss": 1.0}],
                "evaluation": {
                    "macro_f1": macro_f1,
                    "accuracy": accuracy,
                    "per_class": {
                        "angular_leaf_spot": {},
                        "bean_rust": {},
                        "healthy": {},
                    },
                    "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                },
                "predictions": [
                    {
                        "identity": "test-0000",
                        "true_class": "healthy",
                        "predicted_class": "healthy",
                        "probabilities": {
                            "angular_leaf_spot": 0.1,
                            "bean_rust": 0.1,
                            "healthy": 0.8,
                        },
                    },
                    {
                        "identity": "test-0001",
                        "true_class": "bean_rust",
                        "predicted_class": "bean_rust",
                        "probabilities": {
                            "angular_leaf_spot": 0.1,
                            "bean_rust": 0.8,
                            "healthy": 0.1,
                        },
                    },
                ],
                "checkpoint": str(checkpoint),
            }
        ),
        encoding="utf-8",
    )


def test_v2_selected_seeds_preserve_protocol_order() -> None:
    assert _selected_seeds([1003, 1002]) == (1002, 1003)
    assert _selected_seeds(None)[0] == 1001


def test_v2_resume_rejects_invalid_branch_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "v2"
    _write_branch_result(output, 1002, "solucao_principal", 0.8, 0.9)
    result_path = _branch_result_path(output, 1002, "solucao_principal")
    checkpoint = _checkpoint_path(output, 1002, "solucao_principal")

    assert _complete_branch(result_path, checkpoint, 1002, "solucao_principal")
    result_path.write_text("{}", encoding="utf-8")
    assert not _complete_branch(result_path, checkpoint, 1002, "solucao_principal")


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
