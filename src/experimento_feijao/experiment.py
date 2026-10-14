from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import cv2
import keras  # type: ignore[import-untyped]
import numpy as np
import tensorflow as tf  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from experimento_feijao.preparation import BEANS_CLASSES, DATASET_VERSION

Arm = Literal["solucao_principal", "solucao_contrafactual"]
RunMode = Literal["confirmatory", "epoch_pilot"]
ARMS: tuple[Arm, Arm] = ("solucao_principal", "solucao_contrafactual")
COMPONENTS = ("base", "head", "data", "augmentation", "dropout")


class ExperimentError(ValueError):
    def __init__(self, stage: str, arm: str, seed: int, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.arm = arm
        self.seed = seed


@dataclass(frozen=True)
class SegmentedRecord:
    identity: str
    label: int
    class_name: str
    path: Path


def _mapping(value: object, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be an object")
    return value


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _derive_seed(pair_seed: int, component: str) -> int:
    digest = hashlib.sha256(f"{pair_seed}:{component}".encode()).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _read_configuration(
    path: Path, pair_seed: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        configuration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExperimentError("configuration", "pair", pair_seed, str(error)) from error
    try:
        root = _mapping(configuration, "configuration")
        dataset = _mapping(root.get("dataset"), "dataset")
        segmentation = _mapping(root.get("segmentation"), "segmentation")
        training = _mapping(root.get("training"), "training")
        augmentation = _mapping(training.get("augmentation"), "training.augmentation")
        checkpoint = _mapping(root.get("checkpoint"), "checkpoint")
        seeds = root.get("seeds")
        if dataset.get("version") != DATASET_VERSION:
            raise ValueError(f"dataset version must be exactly {DATASET_VERSION}")
        if segmentation.get("state") != "frozen":
            raise ValueError("segmentation configuration must be frozen")
        if not (
            isinstance(seeds, list)
            and len(seeds) == 30
            and len(set(seeds)) == 30
            and all(
                isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds
            )
        ):
            raise ValueError("exactly 30 unique integer seeds are required")
        if pair_seed not in seeds:
            raise ValueError("selected seed must be present in the frozen seed list")
        expected: tuple[tuple[str, Any, Any], ...] = (
            ("epochs", int, lambda value: not isinstance(value, bool) and value > 0),
            (
                "batch_size",
                int,
                lambda value: not isinstance(value, bool) and value > 0,
            ),
            ("learning_rate", (int, float), lambda value: value > 0),
            ("l2", (int, float), lambda value: value >= 0),
            ("dropout", (int, float), lambda value: 0 <= value < 1),
        )
        for name, value_type, predicate in expected:
            value = training.get(name)
            if (
                not isinstance(value, value_type)
                or isinstance(value, bool)
                or not predicate(value)
            ):
                raise ValueError(f"training.{name} is invalid")
        if not isinstance(augmentation.get("horizontal_flip"), bool):
            raise ValueError(
                "training.augmentation.horizontal_flip must be a boolean"
            )
        brightness = augmentation.get("brightness_delta")
        if (
            not isinstance(brightness, (int, float))
            or isinstance(brightness, bool)
            or not 0 <= brightness <= 1
        ):
            raise ValueError("training.augmentation.brightness_delta is invalid")
        if checkpoint.get("rule") != "lowest_validation_loss":
            raise ValueError("checkpoint rule must be lowest_validation_loss")
    except ValueError as error:
        raise ExperimentError(
            "configuration", "pair", pair_seed, str(error)
        ) from error
    return root, training


def _load_segmented_inputs(
    root: Path, pair_seed: int, mode: RunMode
) -> tuple[dict[str, list[SegmentedRecord]], str]:
    manifest_path = root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = _mapping(json.loads(manifest_bytes), "segmented manifest")
        dataset = _mapping(manifest.get("dataset"), "segmented dataset")
        segmentation = _mapping(manifest.get("segmentation"), "segmentation")
        shared_inputs = _mapping(manifest.get("shared_inputs"), "shared_inputs")
        artifacts = manifest.get("artifacts")
        scope = manifest.get("scope")
        if dataset.get("version") != DATASET_VERSION:
            raise ValueError(f"segmented dataset must be {DATASET_VERSION}")
        if dataset.get("class_names") != list(BEANS_CLASSES):
            raise ValueError("segmented dataset classes are invalid")
        if (
            segmentation.get("state") != "frozen"
            or segmentation.get("output_size") != [160, 160]
            or not _mapping(segmentation.get("rubric"), "segmentation rubric").get(
                "confirmed"
            )
        ):
            raise ValueError("segmented inputs must use the confirmed frozen procedure")
        if shared_inputs != {
            "solucao_principal": "images",
            "solucao_contrafactual": "images",
        }:
            raise ValueError("segmented inputs are not shared by both arms")
        if not isinstance(artifacts, list):
            raise ValueError("segmented artifacts must be a list")
        if mode == "epoch_pilot" and scope != {
            "purpose": "epoch_pilot",
            "loaded_splits": ["train", "validation"],
            "test_data_accessed": False,
        }:
            raise ValueError(
                "epoch pilot inputs must prove train/validation-only preparation"
            )

        required_splits = (
            ("train", "validation")
            if mode == "epoch_pilot"
            else ("train", "validation", "test")
        )
        records: dict[str, list[SegmentedRecord]] = {
            split: [] for split in required_splits
        }
        identities: set[str] = set()
        for raw_artifact in artifacts:
            artifact = _mapping(raw_artifact, "segmented artifact")
            identity = artifact.get("identity")
            split = artifact.get("split")
            class_name = artifact.get("class")
            relative_path = artifact.get("path")
            checksum = artifact.get("sha256")
            if (
                not isinstance(identity, str)
                or identity in identities
                or split not in records
                or class_name not in BEANS_CLASSES
                or not isinstance(relative_path, str)
                or not isinstance(checksum, str)
            ):
                raise ValueError("segmented artifact metadata is invalid")
            path = root / relative_path
            contents = path.read_bytes()
            if hashlib.sha256(contents).hexdigest() != checksum:
                raise ValueError(f"checksum mismatch for segmented input {identity}")
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None or image.shape != (160, 160, 3):
                raise ValueError(f"segmented input {identity} must be RGB 160 x 160")
            identities.add(identity)
            records[cast(str, split)].append(
                SegmentedRecord(
                    identity,
                    BEANS_CLASSES.index(cast(str, class_name)),
                    cast(str, class_name),
                    path,
                )
            )
        if any(not split_records for split_records in records.values()):
            raise ValueError("train, validation, and test must all contain inputs")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ExperimentError(
            "segmented-inputs", "pair", pair_seed, str(error)
        ) from error
    for split_records in records.values():
        split_records.sort(key=lambda record: record.identity)
    return records, hashlib.sha256(manifest_bytes).hexdigest()


def _images(records: list[SegmentedRecord]) -> NDArray[np.uint8]:
    loaded = []
    for record in records:
        image = cv2.imread(str(record.path), cv2.IMREAD_COLOR)
        if image is None:
            raise OSError(f"could not read {record.path}")
        loaded.append(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    return np.asarray(loaded, dtype=np.uint8)


def _epoch_training_data(
    records: list[SegmentedRecord],
    images: NDArray[np.uint8],
    epoch: int,
    data_seed: int,
    augmentation_seed: int,
    horizontal_flip: bool,
    brightness_delta: float,
) -> tuple[NDArray[np.float32], NDArray[np.int64]]:
    order = list(range(len(records)))
    random.Random(f"{data_seed}:{epoch}").shuffle(order)
    augmented: list[NDArray[np.float32]] = []
    labels: list[int] = []
    for index in order:
        record = records[index]
        image = images[index].astype(np.float32)
        local_seed = _derive_seed(
            augmentation_seed, f"{record.identity}:{epoch}"
        )
        generator = np.random.default_rng(local_seed)
        if horizontal_flip and bool(generator.integers(0, 2)):
            image = np.flip(image, axis=1)
        delta = float(generator.uniform(-brightness_delta, brightness_delta)) * 255
        augmented.append(np.clip(image + delta, 0, 255).astype(np.float32))
        labels.append(record.label)
    return np.stack(augmented), np.asarray(labels, dtype=np.int64)


def _build_model(
    arm: Arm, seeds: dict[str, int], training: dict[str, Any]
) -> tuple[keras.Model, str]:
    if arm == "solucao_contrafactual":
        keras.utils.set_random_seed(seeds["base"])
    base = keras.applications.MobileNetV2(
        input_shape=(160, 160, 3),
        alpha=1.0,
        include_top=False,
        weights="imagenet" if arm == "solucao_principal" else None,
    )
    base.trainable = True
    inputs = keras.Input(shape=(160, 160, 3), name="segmented_input")
    normalized = keras.layers.Lambda(
        keras.applications.mobilenet_v2.preprocess_input,
        name="mobilenet_v2_preprocessing",
    )(inputs)
    features = base(normalized)
    pooled = keras.layers.GlobalAveragePooling2D(name="global_average_pooling")(
        features
    )
    dropped = keras.layers.Dropout(
        float(training["dropout"]), seed=seeds["dropout"], name="dropout"
    )(pooled)
    classifier = keras.layers.Dense(
        len(BEANS_CLASSES),
        activation="softmax",
        kernel_initializer=keras.initializers.GlorotUniform(seed=seeds["head"]),
        bias_initializer="zeros",
        kernel_regularizer=keras.regularizers.l2(float(training["l2"])),
        name="classifier",
    )
    outputs = classifier(dropped)
    model = keras.Model(inputs, outputs)
    head_hash = hashlib.sha256()
    for weight in classifier.get_weights():
        head_hash.update(np.ascontiguousarray(weight).tobytes())
    model.compile(
        optimizer=keras.optimizers.Adam(float(training["learning_rate"])),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    return model, head_hash.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    label_indexes = list(range(len(BEANS_CLASSES)))
    precision, recall, f1, support = precision_recall_fscore_support(
        labels,
        predictions,
        labels=label_indexes,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(
            f1_score(
                labels,
                predictions,
                labels=label_indexes,
                average="macro",
                zero_division=0,
            )
        ),
        "confusion_matrix": confusion_matrix(
            labels, predictions, labels=label_indexes
        ).tolist(),
        "per_class": {
            class_name: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, class_name in enumerate(BEANS_CLASSES)
        },
    }


def _run_arm(
    arm: Arm,
    pair_seed: int,
    component_seeds: dict[str, int],
    configuration: dict[str, Any],
    training: dict[str, Any],
    records: dict[str, list[SegmentedRecord]],
    segmented_root: Path,
    segmented_manifest_sha256: str,
    output: Path,
    mode: RunMode,
) -> None:
    try:
        keras.backend.clear_session()
        model, initial_head_sha256 = _build_model(arm, component_seeds, training)
    except Exception as error:
        raise ExperimentError(
            "model-construction", arm, pair_seed, str(error)
        ) from error

    try:
        train_images = _images(records["train"])
        validation_images = _images(records["validation"]).astype(np.float32)
        validation_labels = np.asarray(
            [record.label for record in records["validation"]], dtype=np.int64
        )
        history: dict[str, list[float]] = {}
        best_loss = float("inf")
        best_epoch = 0
        best_weights: list[NDArray[Any]] = []
        elapsed = 0.0
        for epoch in range(int(training["epochs"])):
            epoch_images, epoch_labels = _epoch_training_data(
                records["train"],
                train_images,
                epoch,
                component_seeds["data"],
                component_seeds["augmentation"],
                bool(
                    _mapping(training["augmentation"], "augmentation")[
                        "horizontal_flip"
                    ]
                ),
                float(
                    _mapping(training["augmentation"], "augmentation")[
                        "brightness_delta"
                    ]
                ),
            )
            started = time.perf_counter()
            epoch_history = model.fit(
                epoch_images,
                epoch_labels,
                batch_size=int(training["batch_size"]),
                epochs=1,
                shuffle=False,
                validation_data=(validation_images, validation_labels),
                verbose=0,
            )
            elapsed += time.perf_counter() - started
            for name, values in epoch_history.history.items():
                history.setdefault(name, []).extend(float(value) for value in values)
            validation_loss = float(epoch_history.history["val_loss"][0])
            if validation_loss < best_loss:
                best_loss = validation_loss
                best_epoch = epoch + 1
                best_weights = model.get_weights()
        model.set_weights(best_weights)
        output.mkdir(parents=True)
        if mode == "confirmatory":
            model.save_weights(output / "checkpoint.weights.h5")
        _write_json(output / "history.json", history)
        _write_json(
            output / "duration.json",
            {"seconds": elapsed, "scope": "model.fit only"},
        )
    except Exception as error:
        raise ExperimentError("training", arm, pair_seed, str(error)) from error

    if mode == "confirmatory":
        try:
            test_images = _images(records["test"]).astype(np.float32)
            probabilities = cast(
                NDArray[np.float32], model.predict(test_images, verbose=0)
            )
            predicted_indexes = np.argmax(probabilities, axis=1).tolist()
            labels = [record.label for record in records["test"]]
            predictions = [
                {
                    "identity": record.identity,
                    "label": record.class_name,
                    "predicted_class": BEANS_CLASSES[predicted_indexes[index]],
                    "probabilities": {
                        class_name: float(probabilities[index, class_index])
                        for class_index, class_name in enumerate(BEANS_CLASSES)
                    },
                }
                for index, record in enumerate(records["test"])
            ]
            _write_json(output / "predictions.json", predictions)
            _write_json(output / "metrics.json", _metrics(labels, predicted_indexes))
        except Exception as error:
            raise ExperimentError("evaluation", arm, pair_seed, str(error)) from error

    arm_seeds: dict[str, int | None] = dict(component_seeds)
    if arm == "solucao_principal":
        arm_seeds["base"] = None
    artifact_names = (
        (
            "checkpoint.weights.h5",
            "history.json",
            "duration.json",
            "predictions.json",
            "metrics.json",
        )
        if mode == "confirmatory"
        else ("history.json", "duration.json")
    )
    manifest = {
        "arm": arm,
        "mode": mode,
        "test_data_accessed": mode == "confirmatory",
        "pair_seed": pair_seed,
        "base_initialization": (
            "imagenet" if arm == "solucao_principal" else "random"
        ),
        "model": {
            "architecture": "MobileNetV2",
            "input_shape": [160, 160, 3],
            "alpha": 1.0,
            "include_top": False,
            "classes": 3,
            "all_layers_trainable": True,
            "preprocessing": "keras.applications.mobilenet_v2.preprocess_input",
            "preprocessing_applications": 1,
        },
        "seeds": arm_seeds,
        "initial_head_sha256": initial_head_sha256,
        "training": {
            **training,
            "loss": "sparse_categorical_crossentropy",
            "optimizer": "adam",
            "checkpoint_rule": "lowest_validation_loss",
        },
        "selected_checkpoint": {
            "epoch": best_epoch,
            "validation_loss": best_loss,
            "path": "checkpoint.weights.h5" if mode == "confirmatory" else None,
        },
        "configuration_sha256": _canonical_sha256(configuration),
        "segmented_inputs": {
            "root": str(segmented_root.resolve()),
            "manifest_sha256": segmented_manifest_sha256,
        },
        "artifacts": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in artifact_names
        },
    }
    try:
        _write_json(output / "manifest.json", manifest)
    except OSError as error:
        raise ExperimentError("manifest", arm, pair_seed, str(error)) from error


def run_pair(
    configuration_path: Path,
    segmented_root: Path,
    pair_seed: int,
    output: Path,
    *,
    mode: RunMode = "confirmatory",
) -> None:
    if output.exists():
        raise ExperimentError(
            "output", "pair", pair_seed, f"output already exists: {output}"
        )
    configuration, training = _read_configuration(configuration_path, pair_seed)
    records, segmented_manifest_sha256 = _load_segmented_inputs(
        segmented_root, pair_seed, mode
    )
    component_seeds = {
        component: _derive_seed(pair_seed, component) for component in COMPONENTS
    }
    tf.config.experimental.enable_op_determinism()
    execution_order = list(ARMS)
    random.Random(_derive_seed(pair_seed, "arm-order")).shuffle(execution_order)
    try:
        output.mkdir(parents=True)
    except OSError as error:
        raise ExperimentError("output", "pair", pair_seed, str(error)) from error
    for arm in execution_order:
        _run_arm(
            arm,
            pair_seed,
            component_seeds,
            configuration,
            training,
            records,
            segmented_root,
            segmented_manifest_sha256,
            output / arm,
            mode,
        )
    try:
        _write_json(
            output / "manifest.json",
            {
                "seed": pair_seed,
                "mode": mode,
                "execution_order": execution_order,
                "deterministic_operations": True,
                "loaded_splits": list(records),
                "test_data_accessed": mode == "confirmatory",
                "configuration_sha256": _canonical_sha256(configuration),
                "segmented_manifest_sha256": segmented_manifest_sha256,
            },
        )
    except OSError as error:
        raise ExperimentError("manifest", "pair", pair_seed, str(error)) from error
