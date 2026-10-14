from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")
ARMS = ("solucao_principal", "solucao_contrafactual")


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["experimento-feijao", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def write_protocol(tmp_path: Path) -> Path:
    protocol: dict[str, Any] = {
        "dataset": {"version": "beans:0.1.0"},
        "segmentation": {
            "state": "frozen",
            "hsv": {"lower": [35, 50, 20], "upper": [90, 255, 255]},
            "pilot_evidence": "reports/segmentation-pilot.md",
        },
        "training": {
            "epochs": 1,
            "pilot_evidence": "reports/epochs-pilot.md",
            "batch_size": 6,
            "learning_rate": 0.0001,
            "l2": 0.0001,
            "dropout": 0.2,
            "augmentation": {
                "horizontal_flip": True,
                "brightness_delta": 0.05,
            },
        },
        "seeds": list(range(1001, 1031)),
        "checkpoint": {"rule": "lowest_validation_loss"},
        "failure": {"policy": "retry_full_pair", "max_retries": 1},
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path


def write_segmented_inputs(tmp_path: Path, *, epoch_pilot: bool = False) -> Path:
    root = tmp_path / "segmented"
    artifacts: list[dict[str, str]] = []
    splits = [("train", 2), ("validation", 1)]
    if not epoch_pilot:
        splits.append(("test", 1))
    for split, count in splits:
        for class_index, class_name in enumerate(CLASSES):
            for index in range(count):
                image = np.full((160, 160, 3), 127, dtype=np.uint8)
                image[20:140, 25:135] = (35 + class_index * 25, 145, 45)
                image[50 + index : 75 + index, 60:90] = (
                    170,
                    65 + class_index * 20,
                    30,
                )
                identity = f"{split}-{class_name}-{index:02d}"
                relative_path = Path("images", split, class_name, f"{identity}.png")
                destination = root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                assert cv2.imwrite(
                    str(destination), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                )
                artifacts.append(
                    {
                        "identity": identity,
                        "split": split,
                        "class": class_name,
                        "path": relative_path.as_posix(),
                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    }
                )
    manifest = {
        "dataset": {
            "version": "beans:0.1.0",
            "class_names": list(CLASSES),
        },
        "segmentation": {
            "state": "frozen",
            "output_size": [160, 160],
            "rubric": {"confirmed": True},
        },
        "shared_inputs": {
            "solucao_principal": "images",
            "solucao_contrafactual": "images",
        },
        "artifacts": artifacts,
    }
    if epoch_pilot:
        manifest["scope"] = {
            "purpose": "epoch_pilot",
            "loaded_splits": ["train", "validation"],
            "test_data_accessed": False,
        }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return root


def test_run_executes_a_reduced_paired_experiment_through_the_cli(
    tmp_path: Path,
) -> None:
    protocol = write_protocol(tmp_path)
    segmented = write_segmented_inputs(tmp_path)
    output = tmp_path / "pair"

    result = run_cli(
        "run",
        "--config",
        str(protocol),
        "--segmented-inputs",
        str(segmented),
        "--seed",
        "1001",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    pair_manifest = json.loads((output / "manifest.json").read_text())
    assert pair_manifest["seed"] == 1001
    assert set(pair_manifest["execution_order"]) == set(ARMS)
    assert pair_manifest["deterministic_operations"] is True

    arm_manifests = {
        arm: json.loads((output / arm / "manifest.json").read_text()) for arm in ARMS
    }
    principal = arm_manifests["solucao_principal"]
    counterfactual = arm_manifests["solucao_contrafactual"]
    assert principal["model"] == counterfactual["model"] == {
        "architecture": "MobileNetV2",
        "input_shape": [160, 160, 3],
        "alpha": 1.0,
        "include_top": False,
        "classes": 3,
        "all_layers_trainable": True,
        "preprocessing": "keras.applications.mobilenet_v2.preprocess_input",
        "preprocessing_applications": 1,
    }
    assert principal["base_initialization"] == "imagenet"
    assert counterfactual["base_initialization"] == "random"
    assert principal["seeds"]["base"] is None
    assert isinstance(counterfactual["seeds"]["base"], int)
    for component in ("head", "data", "augmentation", "dropout"):
        assert principal["seeds"][component] == counterfactual["seeds"][component]
    assert principal["initial_head_sha256"] == counterfactual["initial_head_sha256"]
    assert principal["training"] == counterfactual["training"]
    assert principal["segmented_inputs"] == counterfactual["segmented_inputs"]
    assert principal["configuration_sha256"] == counterfactual["configuration_sha256"]

    for arm in ARMS:
        arm_dir = output / arm
        assert {
            path.name
            for path in arm_dir.iterdir()
            if path.name != "manifest.json"
        } == {
            "checkpoint.weights.h5",
            "history.json",
            "duration.json",
            "predictions.json",
            "metrics.json",
        }
        duration = json.loads((arm_dir / "duration.json").read_text())
        assert duration["scope"] == "model.fit only"
        assert duration["seconds"] >= 0
        predictions = json.loads((arm_dir / "predictions.json").read_text())
        assert len(predictions) == 3
        assert {prediction["label"] for prediction in predictions} == set(CLASSES)
        assert all(len(prediction["probabilities"]) == 3 for prediction in predictions)
        metrics = json.loads((arm_dir / "metrics.json").read_text())
        assert set(metrics) == {
            "accuracy",
            "macro_f1",
            "confusion_matrix",
            "per_class",
        }
        assert arm_manifests[arm]["selected_checkpoint"]["epoch"] == 1
        for name, checksum in arm_manifests[arm]["artifacts"].items():
            assert checksum == hashlib.sha256((arm_dir / name).read_bytes()).hexdigest()


def test_pilot_trains_and_validates_both_arms_without_test_data(tmp_path: Path) -> None:
    protocol = write_protocol(tmp_path)
    segmented = write_segmented_inputs(tmp_path, epoch_pilot=True)
    output = tmp_path / "pilot-pair"

    result = run_cli(
        "pilot",
        "--config",
        str(protocol),
        "--segmented-inputs",
        str(segmented),
        "--seed",
        "1001",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    pair_manifest = json.loads((output / "manifest.json").read_text())
    assert pair_manifest["mode"] == "epoch_pilot"
    assert pair_manifest["loaded_splits"] == ["train", "validation"]
    assert pair_manifest["test_data_accessed"] is False
    for arm in ARMS:
        arm_dir = output / arm
        assert {path.name for path in arm_dir.iterdir()} == {
            "duration.json",
            "history.json",
            "manifest.json",
        }
        history = json.loads((arm_dir / "history.json").read_text())
        assert len(history["loss"]) == 1
        assert len(history["val_loss"]) == 1
        manifest = json.loads((arm_dir / "manifest.json").read_text())
        assert manifest["test_data_accessed"] is False
