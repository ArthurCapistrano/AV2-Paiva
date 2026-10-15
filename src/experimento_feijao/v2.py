from __future__ import annotations

import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import cv2
import keras  # type: ignore[import-untyped]
import numpy as np
import tensorflow as tf  # type: ignore[import-untyped]
from scipy.stats import t as student_t  # type: ignore[import-untyped]
from scipy.stats import ttest_rel
from sklearn.metrics import (  # type: ignore[import-untyped]
    classification_report,
    confusion_matrix,
)

from experimento_feijao.experiment import (
    BRANCHES,
    COMPONENTS,
    Branch,
    SegmentedRecord,
    _build_model,
    _derive_seed,
    _epoch_training_data,
    _images,
    _load_segmented_inputs,
    _read_configuration,
)
from experimento_feijao.preparation import (
    BEANS_CLASSES,
    SEEDS,
    _download_mirror_archive,
    _read_archive_records,
)

V2_SCHEMA_VERSION = 1
FIXED_GRADCAM_IDENTITIES = {
    "angular_leaf_spot": "test-0042",
    "bean_rust": "test-0085",
    "healthy": "test-0000",
}


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _selected_seeds(values: Iterable[int] | None) -> tuple[int, ...]:
    if values is None:
        return tuple(SEEDS)
    selected = tuple(values)
    if not selected or any(seed not in SEEDS for seed in selected):
        raise ValueError("seeds must be selected from the fixed V1 seeds")
    if len(set(selected)) != len(selected):
        raise ValueError("seeds must not repeat")
    return tuple(seed for seed in SEEDS if seed in selected)


def _branch_result_path(output: Path, seed: int, branch: Branch) -> Path:
    return output / "results" / f"pair-{seed}" / branch / "result.json"


def _checkpoint_path(output: Path, seed: int, branch: Branch) -> Path:
    return output / "checkpoints" / f"pair-{seed}" / f"{branch}.weights.h5"


def _history_row(history: dict[str, list[float]], epoch: int) -> dict[str, float]:
    row: dict[str, float] = {"epoch": float(epoch)}
    for name, values in history.items():
        if values:
            row[name] = float(values[0])
    return row


def _evaluation(
    records: list[SegmentedRecord],
    probabilities: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    labels = [record.label for record in records]
    predictions = np.argmax(probabilities, axis=1).tolist()
    report = classification_report(
        labels,
        predictions,
        labels=list(range(len(BEANS_CLASSES))),
        target_names=list(BEANS_CLASSES),
        output_dict=True,
        zero_division=0,
    )
    per_class = {
        class_name: {
            metric: float(report[class_name][metric])
            for metric in ("precision", "recall", "f1-score", "support")
        }
        for class_name in BEANS_CLASSES
    }
    evaluation = {
        "accuracy": float(report["accuracy"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(
            labels, predictions, labels=list(range(len(BEANS_CLASSES)))
        ).tolist(),
    }
    prediction_rows = [
        {
            "identity": record.identity,
            "true_class": BEANS_CLASSES[record.label],
            "predicted_class": BEANS_CLASSES[prediction],
            "probabilities": {
                class_name: float(probability)
                for class_name, probability in zip(BEANS_CLASSES, row, strict=True)
            },
        }
        for record, prediction, row in zip(
            records, predictions, probabilities, strict=True
        )
    ]
    return evaluation, prediction_rows


def _run_branch_v2(
    branch: Branch,
    pair_seed: int,
    seeds: dict[str, int],
    training: dict[str, Any],
    records: dict[str, list[SegmentedRecord]],
    checkpoint: Path,
) -> dict[str, Any]:
    model: keras.Model | None = None
    try:
        model = _build_model(branch, seeds, training, include_metrics=True)
        train_records = records["train"]
        validation_records = records["validation"]
        train_images = _images(train_records)
        validation_images = _images(validation_records).astype(np.float32)
        validation_labels = np.asarray(
            [record.label for record in validation_records], dtype=np.int64
        )
        augmentation = training["augmentation"]
        if not isinstance(augmentation, dict):
            raise ValueError("training augmentation is required")

        best_loss = float("inf")
        best_epoch = 0
        best_weights = model.get_weights()
        history_rows: list[dict[str, float]] = []
        started = time.perf_counter()
        for epoch in range(int(training["epochs"])):
            epoch_images, epoch_labels = _epoch_training_data(
                train_records,
                train_images,
                epoch,
                seeds["data"],
                seeds["augmentation"],
                bool(augmentation["horizontal_flip"]),
                float(augmentation["brightness_delta"]),
            )
            history = model.fit(
                epoch_images,
                epoch_labels,
                batch_size=int(training["batch_size"]),
                epochs=1,
                shuffle=False,
                validation_data=(validation_images, validation_labels),
                verbose=0,
            )
            history_rows.append(_history_row(history.history, epoch + 1))
            validation_loss = float(history.history["val_loss"][0])
            if validation_loss < best_loss:
                best_loss = validation_loss
                best_epoch = epoch + 1
                best_weights = model.get_weights()
        elapsed = time.perf_counter() - started

        model.set_weights(best_weights)
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        model.save_weights(checkpoint)
        test_records = records["test"]
        probabilities = np.asarray(model.predict(_images(test_records), verbose=0))
        evaluation, prediction_rows = _evaluation(test_records, probabilities)
        return {
            "schema_version": V2_SCHEMA_VERSION,
            "seed": pair_seed,
            "branch": branch,
            "best_epoch": best_epoch,
            "best_validation_loss": best_loss,
            "training_seconds": elapsed,
            "history": history_rows,
            "evaluation": evaluation,
            "predictions": prediction_rows,
            "checkpoint": str(checkpoint),
        }
    finally:
        del model
        keras.backend.clear_session()


def run_v2_experiment(
    configuration_path: Path,
    segmented_root: Path,
    output: Path,
    seeds: Iterable[int] | None = None,
) -> None:
    """Executa a V2 com telemetria e retomada por ramo concluído."""
    selected = _selected_seeds(seeds)
    records = _load_segmented_inputs(segmented_root)
    tf.config.experimental.enable_op_determinism()
    for pair_seed in selected:
        training = _read_configuration(configuration_path, pair_seed)
        branch_results: dict[str, str] = {}
        for branch in BRANCHES:
            result_path = _branch_result_path(output, pair_seed, branch)
            checkpoint = _checkpoint_path(output, pair_seed, branch)
            if result_path.is_file() and checkpoint.is_file():
                branch_results[branch] = str(result_path)
                continue
            component_seeds = {
                component: _derive_seed(pair_seed, component)
                for component in COMPONENTS
            }
            result = _run_branch_v2(
                branch,
                pair_seed,
                component_seeds,
                training,
                records,
                checkpoint,
            )
            _write_json(result_path, result)
            branch_results[branch] = str(result_path)
        pair_result = output / "results" / f"pair-{pair_seed}" / "result.json"
        _write_json(
            pair_result,
            {
                "schema_version": V2_SCHEMA_VERSION,
                "seed": pair_seed,
                "branches": branch_results,
            },
        )


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"invalid V2 artifact: {path}")
    return document


def _confidence_interval(values: list[float]) -> dict[str, float] | None:
    if len(values) < 2:
        return None
    array = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(array))
    standard_error = float(np.std(array, ddof=1) / np.sqrt(len(array)))
    critical = float(student_t.ppf(0.975, len(array) - 1))
    return {
        "mean": mean,
        "lower_95": mean - critical * standard_error,
        "upper_95": mean + critical * standard_error,
    }


def analyze_v2(output: Path, summary_path: Path | None = None) -> dict[str, Any]:
    """Consolida os pares V2 disponíveis sem iniciar treinamentos."""
    branch_data: dict[str, list[dict[str, Any]]] = {branch: [] for branch in BRANCHES}
    seeds: list[int] = []
    for pair_path in sorted((output / "results").glob("pair-*/result.json")):
        pair = _load_json(pair_path)
        seed = int(pair["seed"])
        loaded: dict[str, dict[str, Any]] = {}
        for branch in BRANCHES:
            result_path = _branch_result_path(output, seed, branch)
            if not result_path.is_file():
                break
            loaded[branch] = _load_json(result_path)
        if len(loaded) != len(BRANCHES):
            continue
        seeds.append(seed)
        for branch in BRANCHES:
            branch_data[branch].append(loaded[branch])

    if not seeds:
        raise ValueError("no complete V2 pairs found")
    metrics: dict[str, dict[str, dict[str, float]]] = {}
    for metric in ("macro_f1", "accuracy"):
        metrics[metric] = {}
        for branch in BRANCHES:
            values = [float(item["evaluation"][metric]) for item in branch_data[branch]]
            metrics[metric][branch] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            }

    principal = np.asarray(
        [float(item["evaluation"]["macro_f1"]) for item in branch_data[BRANCHES[0]]]
    )
    counterfactual = np.asarray(
        [float(item["evaluation"]["macro_f1"]) for item in branch_data[BRANCHES[1]]]
    )
    differences = (principal - counterfactual).tolist()
    test = ttest_rel(principal, counterfactual) if len(seeds) > 1 else None
    summary = {
        "schema_version": V2_SCHEMA_VERSION,
        "pair_count": len(seeds),
        "seeds": seeds,
        "metrics": metrics,
        "paired_macro_f1_difference": {
            "values": differences,
            "confidence_interval_95": _confidence_interval(differences),
            "t_test": None
            if test is None
            else {"statistic": float(test.statistic), "p_value": float(test.pvalue)},
        },
    }
    if summary_path is not None:
        _write_json(summary_path, summary)
    return summary


def _gradcam_map(
    model: keras.Model, image: np.ndarray, class_index: int
) -> np.ndarray:
    base = next(layer for layer in model.layers if isinstance(layer, keras.Model))
    preprocessing = model.get_layer("mobilenet_v2_preprocessing")
    pooling = next(
        layer
        for layer in model.layers
        if isinstance(layer, keras.layers.GlobalAveragePooling2D)
    )
    dropout = next(
        layer for layer in model.layers if isinstance(layer, keras.layers.Dropout)
    )
    classifier = next(
        layer for layer in model.layers if isinstance(layer, keras.layers.Dense)
    )
    normalized = preprocessing(model.input)
    convolutional = base(normalized)
    pooled = pooling(convolutional)
    dropped = dropout(pooled, training=False)
    predictions_output = classifier(dropped)
    grad_model = keras.Model(model.input, [convolutional, predictions_output])
    input_tensor = tf.convert_to_tensor(image[None], dtype=tf.float32)
    with tf.GradientTape() as tape:
        convolutional, predictions = grad_model(input_tensor)
        score = predictions[:, class_index]
    gradients = tape.gradient(score, convolutional)
    weights = tf.reduce_mean(gradients, axis=(1, 2))
    activation = convolutional[0]
    cam = tf.reduce_sum(activation * weights[0][None, None, :], axis=-1)
    cam = tf.maximum(cam, 0)
    maximum = tf.reduce_max(cam)
    cam = tf.where(maximum > 0, cam / maximum, cam)
    return np.asarray(cam)


def _panel(original: np.ndarray, segmented: np.ndarray, cam: np.ndarray) -> np.ndarray:
    size = (segmented.shape[1], segmented.shape[0])
    heatmap_input: np.ndarray = np.asarray(
        np.clip(cam * 255, 0, 255), dtype=np.uint8
    )
    heatmap = cv2.applyColorMap(heatmap_input, cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    heatmap = cv2.resize(heatmap, size, interpolation=cv2.INTER_LINEAR)
    overlay = cv2.addWeighted(segmented, 0.6, heatmap, 0.4, 0)
    original_resized = cv2.resize(original, size, interpolation=cv2.INTER_AREA)
    return np.concatenate((original_resized, segmented, overlay), axis=1)


def run_v2_gradcam(
    configuration_path: Path,
    segmented_root: Path,
    output: Path,
    seeds: Iterable[int] | None = None,
) -> None:
    """Gera os três mapas fixos por ramo para os pares V2 disponíveis."""
    selected = _selected_seeds(seeds)
    records = _load_segmented_inputs(segmented_root)
    segmented_by_identity = {
        record.identity: record for record in records["test"]
    }
    original_records = _read_archive_records(
        _download_mirror_archive("test"), "test"
    )
    original_by_identity = {record.identity: record for record in original_records}
    examples = {
        class_name: (
            segmented_by_identity[identity],
            original_by_identity[identity],
        )
        for class_name, identity in FIXED_GRADCAM_IDENTITIES.items()
    }

    for pair_seed in selected:
        training = _read_configuration(configuration_path, pair_seed)
        component_seeds = {
            component: _derive_seed(pair_seed, component)
            for component in COMPONENTS
        }
        for branch in BRANCHES:
            checkpoint = _checkpoint_path(output, pair_seed, branch)
            if not checkpoint.is_file():
                raise ValueError(f"missing V2 checkpoint: {checkpoint}")
            model = _build_model(branch, component_seeds, training)
            model.load_weights(checkpoint)
            metadata: dict[str, Any] = {
                "schema_version": V2_SCHEMA_VERSION,
                "seed": pair_seed,
                "branch": branch,
                "target": "predicted_class",
                "examples": {},
            }
            try:
                for class_name, (segmented_record, original_record) in examples.items():
                    segmented = _images([segmented_record])[0]
                    probabilities = np.asarray(
                        model.predict(segmented[None], verbose=0)
                    )[0]
                    predicted_index = int(np.argmax(probabilities))
                    cam = _gradcam_map(model, segmented, predicted_index)
                    image_path = (
                        output
                        / "gradcam"
                        / f"pair-{pair_seed}"
                        / branch
                        / f"{class_name}.png"
                    )
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    panel = _panel(original_record.image, segmented, cam)
                    cv2.imwrite(
                        str(image_path), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR)
                    )
                    metadata["examples"][class_name] = {
                        "identity": segmented_record.identity,
                        "predicted_class": BEANS_CLASSES[predicted_index],
                        "path": str(image_path),
                    }
            finally:
                del model
                keras.backend.clear_session()
            _write_json(
                output
                / "gradcam"
                / f"pair-{pair_seed}"
                / branch
                / "diagnostic.json",
                metadata,
            )
