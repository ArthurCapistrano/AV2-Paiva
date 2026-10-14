from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["experimento-feijao", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def valid_configuration() -> dict[str, Any]:
    return {
        "dataset": {"version": "beans:0.1.0"},
        "segmentation": {
            "state": "frozen",
            "hsv": {"lower": [20, 25, 20], "upper": [100, 255, 255]},
            "pilot_evidence": "reports/segmentation-pilot.md",
        },
        "training": {
            "epochs": 20,
            "pilot_evidence": "epochs-pilot.json",
        },
        "seeds": list(range(1001, 1031)),
        "checkpoint": {"rule": "lowest_validation_loss"},
        "failure": {"policy": "retry_full_pair", "max_retries": 1},
    }


def valid_epoch_pilot_evidence() -> dict[str, Any]:
    curve = {
        "epochs_observed": 30,
        "stabilized_at_epoch": 20,
        "window_minimum_validation_loss": [1.0, 0.5, 0.498, 0.497, 0.496, 0.495],
        "validation_loss": {"initial": 1.2, "minimum": 0.4, "final": 0.42},
    }
    return {
        "status": "executed",
        "dataset_splits": ["train", "validation"],
        "test_data_accessed": False,
        "selected_epochs": 20,
        "pilot_seeds": [7001, 7002],
        "training_configuration": {
            "batch_size": 32,
            "learning_rate": 0.0001,
            "l2": 0.0001,
            "dropout": 0.2,
        },
        "stabilization_rule": {
            "declared_before_pilot": True,
            "metric": "validation_loss",
            "window_epochs": 5,
            "maximum_relative_improvement": 0.01,
            "required_stable_windows": 2,
        },
        "curve_summary": {
            "solucao_principal": curve,
            "solucao_contrafactual": curve,
        },
    }


def write_configuration(tmp_path: Path, configuration: dict[str, Any]) -> Path:
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(configuration), encoding="utf-8")
    (tmp_path / "epochs-pilot.json").write_text(
        json.dumps(valid_epoch_pilot_evidence()), encoding="utf-8"
    )
    return path


def test_help_exposes_the_single_cli_and_all_planned_operations() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "validate" in result.stdout
    assert "prepare" in result.stdout
    assert "run" in result.stdout
    assert "pilot" in result.stdout
    assert "consolidate" in result.stdout
    assert "analyze" in result.stdout
    assert "grad-cam" in result.stdout


@pytest.mark.parametrize(
    ("missing_key", "message"),
    [
        ("dataset", "dataset version"),
        ("segmentation", "frozen HSV parameters"),
        ("training", "number of epochs"),
        ("seeds", "30 unique seeds"),
        ("checkpoint", "checkpoint rule"),
        ("failure", "failure policy"),
    ],
)
def test_validate_rejects_each_missing_protocol_category(
    tmp_path: Path, missing_key: str, message: str
) -> None:
    configuration = valid_configuration()
    del configuration[missing_key]
    path = write_configuration(tmp_path, configuration)

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert message in result.stderr
    assert "Protocol is invalid" in result.stderr


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("dataset", "version", "beans", "beans:0.1.0"),
        ("segmentation", "state", "pending", "pending"),
        ("segmentation", "pilot_evidence", "", "pilot evidence"),
        ("training", "epochs", 0, "number of epochs"),
        ("training", "pilot_evidence", "", "pilot evidence"),
        ("checkpoint", "rule", "", "checkpoint rule"),
        ("failure", "policy", "", "failure policy"),
    ],
)
def test_validate_rejects_invalid_or_pending_protocol_values(
    tmp_path: Path, section: str, field: str, value: object, message: str
) -> None:
    configuration = valid_configuration()
    configuration[section][field] = value
    path = write_configuration(tmp_path, configuration)

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert message in result.stderr


def test_validate_writes_normalized_configuration_and_environment_manifest(
    tmp_path: Path,
) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    manifest_path = tmp_path / "artifacts" / "manifest.json"

    result = run_cli(
        "validate", "--config", str(path), "--manifest", str(manifest_path)
    )

    assert result.returncode == 0, result.stderr
    assert "Protocol is valid" in result.stdout
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["configuration"] == configuration
    assert manifest["environment"]["python"].startswith("3.11.")
    assert set(manifest["environment"]["libraries"]) == {
        "keras",
        "numpy",
        "opencv-python-headless",
        "scikit-learn",
        "scipy",
        "tensorflow",
        "tensorflow-datasets",
    }
    assert manifest["environment"]["operating_system"]
    assert manifest["environment"]["hardware"]["machine"]
    assert "cpu" in manifest["environment"]["hardware"]
    assert "gpu" in manifest["environment"]["hardware"]
    assert "cuda" in manifest["environment"]
    assert "cudnn" in manifest["environment"]


def test_validate_rejects_epoch_pilot_evidence_that_accessed_test_data(
    tmp_path: Path,
) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    evidence = valid_epoch_pilot_evidence()
    evidence["test_data_accessed"] = True
    (tmp_path / "epochs-pilot.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "must not access test data" in result.stderr


@pytest.mark.parametrize(
    "missing_field",
    [
        "pilot_seeds",
        "training_configuration",
        "stabilization_rule",
        "curve_summary",
    ],
)
def test_validate_rejects_epoch_pilot_without_minimum_evidence(
    tmp_path: Path, missing_field: str
) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    evidence = valid_epoch_pilot_evidence()
    del evidence[missing_field]
    (tmp_path / "epochs-pilot.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "training pilot evidence" in result.stderr


def test_validate_rejects_epoch_budget_that_does_not_match_pilot_evidence(
    tmp_path: Path,
) -> None:
    configuration = valid_configuration()
    configuration["training"]["epochs"] = 19
    path = write_configuration(tmp_path, configuration)

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "selected epoch budget must match" in result.stderr


def test_validate_rejects_a_different_stabilization_rule(tmp_path: Path) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    evidence = valid_epoch_pilot_evidence()
    evidence["stabilization_rule"]["window_epochs"] = 4
    (tmp_path / "epochs-pilot.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "predeclared stabilization rule" in result.stderr


def test_validate_rejects_curve_summary_that_does_not_support_stabilization(
    tmp_path: Path,
) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    evidence = valid_epoch_pilot_evidence()
    evidence["curve_summary"]["solucao_principal"][
        "window_minimum_validation_loss"
    ] = [1.0, 0.8, 0.6, 0.4, 0.3, 0.2]
    (tmp_path / "epochs-pilot.json").write_text(json.dumps(evidence), encoding="utf-8")

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "summarize a stabilized curve" in result.stderr


def test_validate_rejects_missing_epoch_pilot_evidence_file(tmp_path: Path) -> None:
    configuration = valid_configuration()
    path = write_configuration(tmp_path, configuration)
    (tmp_path / "epochs-pilot.json").unlink()

    result = run_cli("validate", "--config", str(path))

    assert result.returncode == 2
    assert "Could not read training pilot evidence" in result.stderr


def test_future_operation_is_explicitly_unavailable() -> None:
    result = run_cli("consolidate")

    assert result.returncode == 2
    assert "not implemented yet" in result.stderr
