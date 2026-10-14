from __future__ import annotations

import json
import subprocess
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

import experimento_feijao.preparation as preparation

CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["experimento-feijao", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def write_dataset(tmp_path: Path) -> Path:
    records: dict[str, list[dict[str, str]]] = {
        "train": [],
        "validation": [],
        "test": [],
    }
    image_dir = tmp_path / "source-images"
    image_dir.mkdir()

    for split in records:
        for class_name in CLASSES:
            identity = f"{split}-{class_name}"
            image = np.full((20, 20, 3), 255, dtype=np.uint8)
            image[2:18, 3:17] = (30, 180, 30)
            image[7:12, 8:13] = (150, 80, 30)
            image_path = image_dir / f"{identity}.png"
            cv2.imwrite(str(image_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            records[split].append(
                {"id": identity, "label": class_name, "path": str(image_path)}
            )

    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "version": "beans:0.1.0",
                "class_names": list(CLASSES),
                "splits": records,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_prepare_materializes_one_shared_segmented_collection(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "dataset": {"version": "beans:0.1.0"},
                "segmentation": {
                    "hsv": {"lower": [35, 50, 20], "upper": [90, 255, 255]},
                    "morphology": {
                        "kernel_size": 1,
                        "open_iterations": 0,
                        "close_iterations": 0,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "segmented"

    result = run_cli(
        "prepare",
        "--config",
        str(protocol),
        "--dataset-manifest",
        str(write_dataset(tmp_path)),
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert "Prepared 9 segmented inputs" in result.stdout
    assert not (output / "manifest.json").exists()
    assert not (output / "rubric.json").exists()

    segmented_bgr = cv2.imread(
        str(output / "images/test/healthy/test-healthy.png")
    )
    assert segmented_bgr is not None
    segmented = cv2.cvtColor(segmented_bgr, cv2.COLOR_BGR2RGB)
    assert segmented.shape == (160, 160, 3)
    assert segmented[0, 0].tolist() == [127, 127, 127]
    assert segmented[76, 80].tolist() == [150, 80, 30]


def test_read_archive_records_decodes_the_official_dataset_shape(
    tmp_path: Path,
) -> None:
    image = np.full((20, 20, 3), 255, dtype=np.uint8)
    image[2:18, 3:17] = (30, 180, 30)
    encoded_ok, encoded = cv2.imencode(
        ".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    )
    assert encoded_ok

    archive_path = tmp_path / "train.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("train/healthy/example.jpg", encoded.tobytes())

    records = preparation._read_archive_records(archive_path, "train")

    assert len(records) == 1
    assert records[0].identity == "train-0000"
    assert records[0].label == "healthy"
    assert records[0].image.shape == (20, 20, 3)
