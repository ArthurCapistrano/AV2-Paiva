from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import cv2
import keras  # type: ignore[import-untyped]
import numpy as np
import tensorflow as tf  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sklearn.metrics import accuracy_score, f1_score  # type: ignore[import-untyped]

from experimento_feijao.preparation import (
    BEANS_CLASSES,
    DATASET_VERSION,
    SEEDS,
    SPLITS,
)

Arm = Literal["solucao_principal", "solucao_contrafactual"]
ARMS: tuple[Arm, Arm] = ("solucao_principal", "solucao_contrafactual")
COMPONENTS = ("base", "head", "data", "augmentation", "dropout")


class ExperimentError(ValueError):
    """Erro ao executar um par experimental."""


@dataclass(frozen=True)
class SegmentedRecord:
    identity: str
    label: int
    path: Path


def _derive_seed(pair_seed: int, component: str) -> int:
    digest = hashlib.sha256(f"{pair_seed}:{component}".encode()).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _read_configuration(
    path: Path, pair_seed: int
) -> dict[str, Any]:
    """Lê a configuração e devolve os parâmetros de treinamento."""
    try:
        configuration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExperimentError(str(error)) from error
    if not isinstance(configuration, dict):
        raise ExperimentError("configuration must be an object")

    dataset = configuration.get("dataset")
    training = configuration.get("training")
    seeds = configuration.get("seeds")
    if not isinstance(dataset, dict) or dataset.get("version") != DATASET_VERSION:
        raise ExperimentError(f"dataset version must be {DATASET_VERSION}")
    if not isinstance(training, dict):
        raise ExperimentError("training configuration is required")
    required_training = (
        "epochs",
        "batch_size",
        "learning_rate",
        "l2",
        "dropout",
        "augmentation",
    )
    missing_training = [
        name for name in required_training if name not in training
    ]
    if missing_training:
        missing = ", ".join(missing_training)
        raise ExperimentError(f"training fields are required: {missing}")
    augmentation = training["augmentation"]
    if not isinstance(augmentation, dict) or not {
        "horizontal_flip",
        "brightness_delta",
    }.issubset(augmentation):
        raise ExperimentError("training augmentation fields are required")
    if seeds != list(SEEDS) or pair_seed not in SEEDS:
        raise ExperimentError("configuration must contain the 30 fixed seeds")
    return training


def _load_segmented_inputs(root: Path) -> dict[str, list[SegmentedRecord]]:
    """Lê as entradas preparadas pela divisão e pela classe do dataset."""
    records: dict[str, list[SegmentedRecord]] = {split: [] for split in SPLITS}
    for split in SPLITS:
        for class_index, class_name in enumerate(BEANS_CLASSES):
            directory = root / "images" / split / class_name
            for path in sorted(directory.glob("*.png")):
                records[split].append(SegmentedRecord(path.stem, class_index, path))
        if not records[split]:
            raise ExperimentError(f"no segmented inputs found for {split}")
    return records


def _images(records: list[SegmentedRecord]) -> NDArray[np.uint8]:
    images: list[NDArray[np.uint8]] = []
    for record in records:
        image = cv2.imread(str(record.path), cv2.IMREAD_COLOR)
        if image is None:
            raise ExperimentError(f"could not read segmented input: {record.path}")
        images.append(cast(NDArray[np.uint8], cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
    return np.asarray(images, dtype=np.uint8)


def _epoch_training_data(
    records: list[SegmentedRecord],
    images: NDArray[np.uint8],
    epoch: int,
    data_seed: int,
    augmentation_seed: int,
    horizontal_flip: bool,
    brightness_delta: float,
) -> tuple[NDArray[np.float32], NDArray[np.int64]]:
    """Cria a mesma ordem e os mesmos aumentos para os dois braços."""
    order = list(range(len(records)))
    random.Random(f"{data_seed}:{epoch}").shuffle(order)
    augmented: list[NDArray[np.float32]] = []
    labels: list[int] = []
    for index in order:
        record = records[index]
        image = images[index].astype(np.float32)
        local_seed = _derive_seed(augmentation_seed, f"{record.identity}:{epoch}")
        generator = np.random.default_rng(local_seed)
        if horizontal_flip and bool(generator.integers(0, 2)):
            image = np.flip(image, axis=1)
        delta = float(generator.uniform(-brightness_delta, brightness_delta)) * 255
        augmented.append(np.clip(image + delta, 0, 255).astype(np.float32))
        labels.append(record.label)
    return np.stack(augmented), np.asarray(labels, dtype=np.int64)


def _build_model(
    arm: Arm, seeds: dict[str, int], training: dict[str, Any]
) -> keras.Model:
    """Constrói os dois braços com a mesma topologia e cabeça."""
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
    pooled = keras.layers.GlobalAveragePooling2D()(features)
    dropped = keras.layers.Dropout(
        float(training["dropout"]), seed=seeds["dropout"]
    )(pooled)
    outputs = keras.layers.Dense(
        len(BEANS_CLASSES),
        activation="softmax",
        kernel_initializer=keras.initializers.GlorotUniform(seed=seeds["head"]),
        bias_initializer="zeros",
        kernel_regularizer=keras.regularizers.l2(float(training["l2"])),
    )(dropped)
    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(float(training["learning_rate"])),
        loss=keras.losses.SparseCategoricalCrossentropy(),
    )
    return model


def _metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    """Calcula somente as métricas necessárias para o experimento."""
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(
            f1_score(
                labels,
                predictions,
                labels=list(range(len(BEANS_CLASSES))),
                average="macro",
                zero_division=0,
            )
        ),
    }


def _run_arm(
    arm: Arm,
    seeds: dict[str, int],
    training: dict[str, Any],
    records: dict[str, list[SegmentedRecord]],
) -> dict[str, float]:
    """Treina um braço e devolve seu F1 macro e sua acurácia.

    Args:
        arm: Solução principal ou solução contrafactual.
        seeds: Seeds derivadas para os componentes comuns do par.
        training: Hiperparâmetros fixos do treinamento.
        records: Entradas segmentadas organizadas por divisão.

    Returns:
        F1 macro e acurácia calculados no conjunto de teste.
    """
    model = _build_model(arm, seeds, training)
    train_records = records["train"]
    validation_records = records["validation"]
    train_images = _images(train_records)
    validation_images = _images(validation_records).astype(np.float32)
    validation_labels = np.asarray(
        [record.label for record in validation_records], dtype=np.int64
    )
    augmentation = training["augmentation"]
    if not isinstance(augmentation, dict):
        raise ExperimentError("training augmentation is required")

    best_loss = float("inf")
    best_weights = model.get_weights()
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
        validation_loss = float(history.history["val_loss"][0])
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_weights = model.get_weights()

    model.set_weights(best_weights)
    test_records = records["test"]
    probabilities = model.predict(_images(test_records), verbose=0)
    predictions = np.argmax(probabilities, axis=1).tolist()
    return _metrics([record.label for record in test_records], predictions)


def run_pair(
    configuration_path: Path,
    segmented_root: Path,
    pair_seed: int,
    output: Path,
) -> None:
    """Executa e salva um par experimental mínimo.

    Args:
        configuration_path: Configuração fixa do experimento.
        segmented_root: Diretório compartilhado de entradas segmentadas.
        pair_seed: Seed do par experimental.
        output: Diretório do resultado mínimo do par.

    Raises:
        ExperimentError: Se a configuração, as entradas ou o treinamento falharem.
    """
    if output.exists():
        raise ExperimentError(f"output already exists: {output}")

    training = _read_configuration(configuration_path, pair_seed)
    records = _load_segmented_inputs(segmented_root)
    seeds = {component: _derive_seed(pair_seed, component) for component in COMPONENTS}
    tf.config.experimental.enable_op_determinism()

    results = {
        arm: _run_arm(arm, seeds, training, records) for arm in ARMS
    }
    output.mkdir(parents=True)
    (output / "result.json").write_text(
        json.dumps({"seed": pair_seed, **results}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
