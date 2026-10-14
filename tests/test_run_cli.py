from __future__ import annotations

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
        "training": {
            "epochs": 1,
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
    }
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path


def write_segmented_inputs(tmp_path: Path) -> Path:
    root = tmp_path / "segmented"
    for split in ("train", "validation", "test"):
        for class_index, class_name in enumerate(CLASSES):
            count = 2 if split == "train" else 1
            for index in range(count):
                image = np.full((160, 160, 3), 127, dtype=np.uint8)
                image[20:140, 25:135] = (35 + class_index * 25, 145, 45)
                image[50 + index : 75 + index, 60:90] = (
                    170,
                    65 + class_index * 20,
                    30,
                )
                destination = (
                    root
                    / "images"
                    / split
                    / class_name
                    / f"{split}-{class_name}-{index:02d}.png"
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                assert cv2.imwrite(
                    str(destination), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                )
    return root


def test_run_executes_one_simple_paired_experiment(tmp_path: Path) -> None:
    output = tmp_path / "pair"
    result = run_cli(
        "run",
        "--config",
        str(write_protocol(tmp_path)),
        "--segmented-inputs",
        str(write_segmented_inputs(tmp_path)),
        "--seed",
        "1001",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    pair = json.loads((output / "result.json").read_text())
    assert pair["seed"] == 1001
    assert set(pair) == {"seed", *ARMS}
    for arm in ARMS:
        assert set(pair[arm]) == {"macro_f1", "accuracy"}
        assert 0 <= pair[arm]["macro_f1"] <= 1
        assert 0 <= pair[arm]["accuracy"] <= 1
    assert {path.name for path in output.iterdir()} == {"result.json"}
