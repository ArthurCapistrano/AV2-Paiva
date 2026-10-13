from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")


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
            "morphology": {
                "kernel_size": 1,
                "open_iterations": 0,
                "close_iterations": 0,
            },
            "adjustment_seed": 1729,
            "max_failures": 6,
            "pilot_evidence": "reports/segmentation-pilot.md",
        },
        "training": {"epochs": 1, "pilot_evidence": "reports/epochs-pilot.md"},
        "seeds": list(range(30)),
        "checkpoint": {"rule": "lowest_validation_loss"},
        "failure": {"policy": "retry_full_pair"},
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path


def write_dataset(tmp_path: Path, blank_training_class: str | None = None) -> Path:
    records: dict[str, list[dict[str, str]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    image_dir = tmp_path / "source-images"
    image_dir.mkdir()
    for split, amount in (("train", 12), ("validation", 1), ("test", 1)):
        for class_name in CLASSES:
            for index in range(amount):
                image = np.full((20, 20, 3), 255, dtype=np.uint8)
                if split != "train" or class_name != blank_training_class:
                    image[2:18, 3:17] = (30, 180, 30)
                    image[7:12, 8:13] = (150, 80, 30)
                identity = f"{split}-{class_name}-{index:02d}"
                image_path = image_dir / f"{identity}.png"
                cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
                records[split].append(
                    {"id": identity, "label": class_name, "path": str(image_path)}
                )

    manifest = {
        "version": "beans:0.1.0",
        "class_names": list(CLASSES),
        "splits": records,
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_prepare_materializes_repeatable_shared_segmented_inputs(
    tmp_path: Path,
) -> None:
    protocol = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path)
    manifests = []

    for run_number in (1, 2):
        output = tmp_path / f"artifacts-{run_number}"
        result = run_cli(
            "prepare",
            "--config",
            str(protocol),
            "--dataset-manifest",
            str(dataset),
            "--output",
            str(output),
        )

        assert result.returncode == 0, result.stderr
        manifests.append(json.loads((output / "manifest.json").read_text()))

        segmented_bgr = cv2.imread(
            str(output / "images/test/healthy/test-healthy-00.png")
        )
        assert segmented_bgr is not None
        segmented = cv2.cvtColor(segmented_bgr, cv2.COLOR_BGR2RGB)
        assert segmented.shape == (160, 160, 3)
        assert segmented[0, 0].tolist() == [127, 127, 127]
        assert segmented[76, 80].tolist() == [150, 80, 30]

    first, second = manifests
    assert first == second
    assert first["dataset"] == {
        "version": "beans:0.1.0",
        "class_names": list(CLASSES),
        "counts": {
            "train": {class_name: 12 for class_name in CLASSES},
            "validation": {class_name: 1 for class_name in CLASSES},
            "test": {class_name: 1 for class_name in CLASSES},
        },
    }
    adjustment = first["segmentation"]["adjustment_sample"]
    assert adjustment["seed"] == 1729
    assert adjustment["split"] == "train"
    assert {name: len(ids) for name, ids in adjustment["identities"].items()} == {
        class_name: 10 for class_name in CLASSES
    }
    assert first["shared_inputs"] == {
        "solucao_principal": "images",
        "solucao_contrafactual": "images",
    }
    assert len(first["artifacts"]) == 42
    for artifact in first["artifacts"]:
        contents = (tmp_path / "artifacts-1" / artifact["path"]).read_bytes()
        assert artifact["sha256"] == hashlib.sha256(contents).hexdigest()
    rubric = json.loads((tmp_path / "artifacts-1/rubric.json").read_text())
    assert rubric["success_count"] == 30
    assert rubric["failure_count"] == 0


def test_prepare_blocks_before_other_splits_when_training_rubric_fails(
    tmp_path: Path,
) -> None:
    protocol = write_protocol(tmp_path)
    dataset = write_dataset(tmp_path, blank_training_class="healthy")
    output = tmp_path / "artifacts"

    result = run_cli(
        "prepare",
        "--config",
        str(protocol),
        "--dataset-manifest",
        str(dataset),
        "--output",
        str(output),
    )

    assert result.returncode == 2
    assert "rubric failed" in result.stderr
    report = json.loads((output / "rubric.json").read_text())
    assert report["sample_split"] == "train"
    assert report["sample_size"] == 30
    assert report["failure_count"] == 10
    assert report["confirmed"] is False
    assert not (output / "images/validation").exists()
    assert not (output / "images/test").exists()
    assert not (output / "manifest.json").exists()


def test_prepare_reports_invalid_hsv_limits_without_a_traceback(tmp_path: Path) -> None:
    protocol = json.loads(write_protocol(tmp_path).read_text())
    protocol["segmentation"]["hsv"]["lower"] = None
    protocol_path = tmp_path / "invalid-protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    dataset = write_dataset(tmp_path)

    result = run_cli(
        "prepare",
        "--config",
        str(protocol_path),
        "--dataset-manifest",
        str(dataset),
        "--output",
        str(tmp_path / "artifacts"),
    )

    assert result.returncode == 2
    assert "invalid HSV limits" in result.stderr
    assert "Traceback" not in result.stderr
