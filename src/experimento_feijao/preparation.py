from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray

DATASET_VERSION = "beans:0.1.0"
SPLITS = ("train", "validation", "test")
BEANS_CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")
BACKGROUND = (127, 127, 127)
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class PreparationError(ValueError):
    pass


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


def _load_manifest(
    path: Path, requested_splits: tuple[str, ...]
) -> dict[str, list[ImageRecord]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreparationError(f"could not read dataset manifest: {error}") from error

    root = _mapping(document, "dataset manifest")
    if root.get("version") != DATASET_VERSION:
        raise PreparationError(f"dataset version must be exactly {DATASET_VERSION}")
    if root.get("class_names") != list(BEANS_CLASSES):
        raise PreparationError("dataset classes do not match beans:0.1.0")
    source_splits = _mapping(root.get("splits"), "dataset splits")
    if set(source_splits) != set(SPLITS):
        raise PreparationError(
            "dataset must contain exactly train, validation, and test"
        )

    result: dict[str, list[ImageRecord]] = {}
    identities: set[str] = set()
    for split in requested_splits:
        raw_records = source_splits[split]
        if not isinstance(raw_records, list):
            raise PreparationError(f"dataset split {split} must be a list")
        result[split] = []
        for raw_record in raw_records:
            record = _mapping(raw_record, f"record in {split}")
            identity = record.get("id")
            label = record.get("label")
            image_path = record.get("path")
            if not isinstance(identity, str) or not IDENTITY_PATTERN.fullmatch(
                identity
            ):
                raise PreparationError(
                    "image identities must be safe, non-empty strings"
                )
            if identity in identities:
                raise PreparationError(f"duplicate image identity: {identity}")
            if label not in BEANS_CLASSES:
                raise PreparationError(f"unknown class for {identity}: {label}")
            if not isinstance(image_path, str):
                raise PreparationError(f"image path is required for {identity}")
            source_path = Path(image_path)
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            image_bgr = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
            if image_bgr is None:
                raise PreparationError(
                    f"could not read image for {identity}: {source_path}"
                )
            image = cast(NDArray[np.uint8], cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
            identities.add(identity)
            result[split].append(ImageRecord(identity, label, image))
    return result


def _load_tfds(requested_splits: tuple[str, ...]) -> dict[str, list[ImageRecord]]:
    import tensorflow_datasets as tfds  # type: ignore[import-untyped]

    try:
        datasets, info = tfds.load(
            DATASET_VERSION,
            split=list(requested_splits),
            as_supervised=True,
            with_info=True,
        )
    except Exception as error:
        raise PreparationError(f"could not load {DATASET_VERSION}: {error}") from error
    if str(info.version) != "0.1.0":
        raise PreparationError(f"loaded unexpected beans version: {info.version}")
    class_names = tuple(info.features["label"].names)
    if class_names != BEANS_CLASSES:
        raise PreparationError("TFDS classes do not match beans:0.1.0")

    result: dict[str, list[ImageRecord]] = {}
    for split, dataset in zip(requested_splits, datasets, strict=True):
        records: list[ImageRecord] = []
        for index, (image, label) in enumerate(tfds.as_numpy(dataset)):
            class_name = class_names[int(label)]
            records.append(
                ImageRecord(f"{split}-{index:04d}", class_name, image.astype(np.uint8))
            )
        result[split] = records
    return result


def _sample_training(records: list[ImageRecord], seed: int) -> dict[str, list[str]]:
    randomizer = random.Random(seed)
    sample: dict[str, list[str]] = {}
    for class_name in BEANS_CLASSES:
        identities = sorted(
            record.identity for record in records if record.label == class_name
        )
        if len(identities) < 10:
            raise PreparationError(
                f"training split needs at least 10 images of class {class_name}"
            )
        sample[class_name] = sorted(randomizer.sample(identities, 10))
    return sample


def _symptoms_preserved(
    silhouette: NDArray[np.uint8], expected_regions: object
) -> bool:
    if not isinstance(expected_regions, list):
        raise PreparationError("expected symptom regions must be a list")
    image_height, image_width = silhouette.shape
    for region in expected_regions:
        if not (
            isinstance(region, list)
            and len(region) == 4
            and all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in region
            )
        ):
            raise PreparationError(
                "expected symptom regions must be [x, y, width, height]"
            )
        x, y, width, height = region
        if (
            x < 0
            or y < 0
            or width <= 0
            or height <= 0
            or x + width > image_width
            or y + height > image_height
        ):
            raise PreparationError(
                "expected symptom region is outside its training image"
            )
        if not bool(np.all(silhouette[y : y + height, x : x + width] == 255)):
            return False
    return True


def _segment(
    image: NDArray[np.uint8],
    segmentation: dict[str, Any],
    expected_symptom_regions: object,
) -> tuple[NDArray[np.uint8] | None, dict[str, object]]:
    hsv_config = _mapping(segmentation.get("hsv"), "segmentation.hsv")
    morphology = _mapping(segmentation.get("morphology"), "segmentation.morphology")
    lower = _hsv_triplet(hsv_config.get("lower"))
    upper = _hsv_triplet(hsv_config.get("upper"))
    kernel_size = morphology.get("kernel_size")
    open_iterations = morphology.get("open_iterations")
    close_iterations = morphology.get("close_iterations")
    if not (
        isinstance(kernel_size, int)
        and not isinstance(kernel_size, bool)
        and kernel_size > 0
        and kernel_size % 2 == 1
        and isinstance(open_iterations, int)
        and not isinstance(open_iterations, bool)
        and open_iterations >= 0
        and isinstance(close_iterations, int)
        and not isinstance(close_iterations, bool)
        and close_iterations >= 0
    ):
        raise PreparationError("invalid fixed morphology parameters")

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
        return None, {
            "continuity": False,
            "borders_preserved": False,
            "symptoms_preserved": False,
            "background_removed": False,
            "failure": "no leaf component found",
        }
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest_mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(
        largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    silhouette = np.zeros_like(largest_mask)
    cv2.drawContours(silhouette, [max(contours, key=cv2.contourArea)], -1, 255, -1)
    composed = np.full_like(image, BACKGROUND)
    composed[silhouette == 255] = image[silhouette == 255]
    resized = cv2.resize(composed, (160, 160), interpolation=cv2.INTER_NEAREST)
    touches_border = bool(
        np.any(silhouette[0])
        or np.any(silhouette[-1])
        or np.any(silhouette[:, 0])
        or np.any(silhouette[:, -1])
    )
    background_removed = bool(np.count_nonzero(silhouette == 0) > 0)
    symptoms_preserved = _symptoms_preserved(silhouette, expected_symptom_regions)
    rubric: dict[str, object] = {
        "continuity": True,
        "borders_preserved": not touches_border,
        "symptoms_preserved": symptoms_preserved,
        "background_removed": background_removed,
        "failure": None,
    }
    if not symptoms_preserved:
        rubric["failure"] = "expected symptom region was removed"
    elif touches_border:
        rubric["failure"] = "leaf silhouette touches an image border"
    elif not background_removed:
        rubric["failure"] = "no background was removed"
    return cast(NDArray[np.uint8], resized), rubric


def prepare(
    configuration: dict[str, Any],
    dataset_manifest: Path | None,
    output: Path,
    *,
    epoch_pilot: bool = False,
) -> dict[str, Any]:
    dataset = _mapping(configuration.get("dataset"), "dataset configuration")
    if dataset.get("version") != DATASET_VERSION:
        raise PreparationError(f"dataset version must be exactly {DATASET_VERSION}")
    segmentation = _mapping(
        configuration.get("segmentation"), "segmentation configuration"
    )
    state = segmentation.get("state")
    if state not in ("adjustment", "frozen"):
        raise PreparationError("segmentation state must be adjustment or frozen")
    adjustment_seed = segmentation.get("adjustment_seed")
    max_failures = segmentation.get("max_failures")
    if not isinstance(adjustment_seed, int) or isinstance(adjustment_seed, bool):
        raise PreparationError("segmentation adjustment_seed must be an integer")
    if (
        not isinstance(max_failures, int)
        or isinstance(max_failures, bool)
        or max_failures < 0
    ):
        raise PreparationError(
            "segmentation max_failures must be a non-negative integer"
        )
    if output.exists():
        raise PreparationError(
            f"output already exists; artifacts are immutable: {output}"
        )

    requested_splits = (
        ("train",)
        if state == "adjustment"
        else ("train", "validation")
        if epoch_pilot
        else SPLITS
    )
    records = (
        _load_tfds(requested_splits)
        if dataset_manifest is None
        else _load_manifest(dataset_manifest, requested_splits)
    )
    sample = _sample_training(records["train"], adjustment_seed)
    sample_ids = {identity for identities in sample.values() for identity in identities}
    expected_regions = _mapping(
        segmentation.get("expected_symptom_regions"),
        "segmentation.expected_symptom_regions",
    )
    output.mkdir(parents=True)
    rubric_entries: list[dict[str, object]] = []
    sampled_outputs: dict[str, NDArray[np.uint8] | None] = {}
    for record in sorted(records["train"], key=lambda item: item.identity):
        if record.identity not in sample_ids:
            continue
        if record.identity not in expected_regions:
            raise PreparationError(
                f"expected symptom regions are required for {record.identity}"
            )
        segmented, rubric = _segment(
            record.image, segmentation, expected_regions[record.identity]
        )
        sampled_outputs[record.identity] = segmented
        rubric_entries.append(
            {
                "identity": record.identity,
                "class": record.label,
                "expected_symptom_regions": expected_regions[record.identity],
                **rubric,
            }
        )

    failed_entries = [entry for entry in rubric_entries if entry["failure"]]
    rubric_report = {
        "sample_split": "train",
        "sample_size": len(rubric_entries),
        "criteria": [
            "continuity",
            "borders_preserved",
            "symptoms_preserved",
            "background_removed",
        ],
        "success_count": len(rubric_entries) - len(failed_entries),
        "failure_count": len(failed_entries),
        "max_failures": max_failures,
        "confirmed": len(failed_entries) <= max_failures
        and all(entry["symptoms_preserved"] for entry in rubric_entries),
        "entries": rubric_entries,
    }
    (output / "rubric.json").write_text(
        json.dumps(rubric_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not rubric_report["confirmed"] and state == "frozen":
        raise PreparationError(
            "segmentation rubric failed; protocol confirmation is blocked"
        )

    artifacts: list[dict[str, str]] = []
    materialized_splits = requested_splits
    for split in materialized_splits:
        split_records = sorted(records[split], key=lambda item: item.identity)
        if state == "adjustment":
            split_records = [
                record for record in split_records if record.identity in sample_ids
            ]
        for record in split_records:
            segmented = sampled_outputs.get(record.identity)
            if record.identity not in sampled_outputs:
                segmented, _ = _segment(record.image, segmentation, [])
            if segmented is None:
                raise PreparationError(
                    f"frozen segmentation failed for {split} image {record.identity}"
                )
            relative_path = Path(
                "images", split, record.label, f"{record.identity}.png"
            )
            destination = output / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(
                str(destination), cv2.cvtColor(segmented, cv2.COLOR_RGB2BGR)
            ):
                raise PreparationError(
                    f"could not write segmented image: {destination}"
                )
            artifacts.append(
                {
                    "identity": record.identity,
                    "split": split,
                    "class": record.label,
                    "path": relative_path.as_posix(),
                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                }
            )

    counts = {
        split: {
            class_name: sum(record.label == class_name for record in records[split])
            for class_name in BEANS_CLASSES
        }
        for split in requested_splits
    }
    manifest = {
        "dataset": {
            "version": DATASET_VERSION,
            "class_names": list(BEANS_CLASSES),
            "counts": counts,
        },
        "segmentation": {
            "state": state,
            "hsv": segmentation["hsv"],
            "morphology": segmentation["morphology"],
            "largest_component": True,
            "external_contour_filled": True,
            "background_rgb": list(BACKGROUND),
            "output_size": [160, 160],
            "interpolation": "nearest",
            "adjustment_sample": {
                "split": "train",
                "seed": adjustment_seed,
                "identities": sample,
            },
            "rubric": {
                "path": "rubric.json",
                "failure_count": len(failed_entries),
                "confirmed": rubric_report["confirmed"],
            },
        },
        "artifacts": artifacts,
    }
    if epoch_pilot:
        manifest["scope"] = {
            "purpose": "epoch_pilot",
            "loaded_splits": ["train", "validation"],
            "test_data_accessed": False,
        }
    if state == "frozen":
        manifest["shared_inputs"] = {
            "solucao_principal": "images",
            "solucao_contrafactual": "images",
        }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not rubric_report["confirmed"]:
        raise PreparationError(
            "segmentation rubric failed; protocol confirmation is blocked"
        )
    return manifest
