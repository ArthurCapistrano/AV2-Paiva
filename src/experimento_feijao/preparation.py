from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray

DATASET_VERSION = "beans:0.1.0"
SPLITS = ("train", "validation", "test")
BEANS_CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")
SEEDS = tuple(range(1001, 1031))
BACKGROUND = (127, 127, 127)


class PreparationError(ValueError):
    """Erro ao preparar uma entrada do experimento."""


@dataclass(frozen=True)
class ImageRecord:
    identity: str
    label: str
    image: NDArray[np.uint8]


def _mapping(value: object, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreparationError(f"{description} must be an object")
    return value


def _hsv_triplet(value: object) -> NDArray[np.uint8]:
    if not (
        isinstance(value, list)
        and len(value) == 3
        and all(
            isinstance(channel, int)
            and not isinstance(channel, bool)
            and 0 <= channel <= 255
            for channel in value
        )
    ):
        raise PreparationError("invalid HSV limits")
    return np.array(value, dtype=np.uint8)


def _read_image(path: Path) -> NDArray[np.uint8]:
    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise PreparationError(f"could not read image: {path}")
    return cast(NDArray[np.uint8], cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))


def _load_manifest(path: Path) -> dict[str, list[ImageRecord]]:
    """Carrega as imagens de um manifesto local do dataset."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreparationError(f"could not read dataset manifest: {error}") from error

    root = _mapping(document, "dataset manifest")
    if root.get("version") != DATASET_VERSION:
        raise PreparationError(f"dataset version must be {DATASET_VERSION}")
    if root.get("class_names") != list(BEANS_CLASSES):
        raise PreparationError("dataset classes do not match beans:0.1.0")

    source_splits = _mapping(root.get("splits"), "dataset splits")
    records: dict[str, list[ImageRecord]] = {}
    for split in SPLITS:
        raw_records = source_splits.get(split)
        if not isinstance(raw_records, list):
            raise PreparationError(f"dataset split {split} must be a list")

        records[split] = []
        for raw_record in raw_records:
            record = _mapping(raw_record, f"record in {split}")
            identity = record.get("id")
            label = record.get("label")
            image_path = record.get("path")
            if not isinstance(identity, str) or not isinstance(label, str):
                raise PreparationError(f"invalid record in {split}")
            if label not in BEANS_CLASSES or not isinstance(image_path, str):
                raise PreparationError(f"invalid image record: {identity}")
            path_value = Path(image_path)
            if not path_value.is_absolute():
                path_value = path.parent / path_value
            records[split].append(ImageRecord(identity, label, _read_image(path_value)))
    return records


def _load_tfds() -> dict[str, list[ImageRecord]]:
    """Carrega os três splits oficiais diretamente do TFDS."""
    import tensorflow_datasets as tfds  # type: ignore[import-untyped]

    try:
        datasets, info = tfds.load(
            DATASET_VERSION,
            split=list(SPLITS),
            as_supervised=True,
            with_info=True,
        )
    except Exception as error:
        raise PreparationError(f"could not load {DATASET_VERSION}: {error}") from error

    class_names = tuple(info.features["label"].names)
    if class_names != BEANS_CLASSES:
        raise PreparationError("TFDS classes do not match beans:0.1.0")

    records: dict[str, list[ImageRecord]] = {}
    for split, dataset in zip(SPLITS, datasets, strict=True):
        records[split] = [
            ImageRecord(
                f"{split}-{index:04d}",
                class_names[int(label)],
                image.astype(np.uint8),
            )
            for index, (image, label) in enumerate(tfds.as_numpy(dataset))
        ]
    return records


def _segment(
    image: NDArray[np.uint8], segmentation: dict[str, Any]
) -> NDArray[np.uint8]:
    """Remove o fundo e preserva o interior da folha na entrada segmentada."""
    hsv = _mapping(segmentation.get("hsv"), "segmentation.hsv")
    morphology = _mapping(segmentation.get("morphology"), "segmentation.morphology")
    lower = _hsv_triplet(hsv.get("lower"))
    upper = _hsv_triplet(hsv.get("upper"))
    kernel_size = morphology.get("kernel_size")
    open_iterations = morphology.get("open_iterations")
    close_iterations = morphology.get("close_iterations")
    if not (
        isinstance(kernel_size, int)
        and kernel_size > 0
        and kernel_size % 2 == 1
        and isinstance(open_iterations, int)
        and open_iterations >= 0
        and isinstance(close_iterations, int)
        and close_iterations >= 0
    ):
        raise PreparationError("invalid morphology parameters")

    mask = cv2.inRange(cv2.cvtColor(image, cv2.COLOR_RGB2HSV), lower, upper)
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    if open_iterations:
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel, iterations=open_iterations
        )
    if close_iterations:
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, kernel, iterations=close_iterations
        )

    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if component_count <= 1:
        raise PreparationError("no leaf component found")

    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest_mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(
        largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    silhouette = np.zeros_like(largest_mask)
    cv2.drawContours(silhouette, [max(contours, key=cv2.contourArea)], -1, 255, -1)

    composed = np.full_like(image, BACKGROUND)
    composed[silhouette == 255] = image[silhouette == 255]
    return cast(
        NDArray[np.uint8],
        cv2.resize(composed, (160, 160), interpolation=cv2.INTER_NEAREST),
    )


def prepare(
    configuration: dict[str, Any],
    dataset_manifest: Path | None,
    output: Path,
) -> dict[str, int]:
    """Prepara todos os splits e devolve a quantidade de entradas produzidas."""
    dataset = _mapping(configuration.get("dataset"), "dataset configuration")
    if dataset.get("version") != DATASET_VERSION:
        raise PreparationError(f"dataset version must be {DATASET_VERSION}")

    segmentation = _mapping(
        configuration.get("segmentation"), "segmentation configuration"
    )
    if output.exists():
        raise PreparationError(f"output already exists: {output}")

    records = _load_manifest(dataset_manifest) if dataset_manifest else _load_tfds()
    output.mkdir(parents=True)
    count = 0
    for split in SPLITS:
        for record in records[split]:
            segmented = _segment(record.image, segmentation)
            destination = (
                output / "images" / split / record.label / f"{record.identity}.png"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(
                str(destination), cv2.cvtColor(segmented, cv2.COLOR_RGB2BGR)
            ):
                raise PreparationError(
                    f"could not write segmented image: {destination}"
                )
            count += 1
    return {"count": count}
