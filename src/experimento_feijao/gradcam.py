from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import keras  # type: ignore[import-untyped]
import numpy as np
import tensorflow as tf  # type: ignore[import-untyped]
from numpy.typing import NDArray

from experimento_feijao.experiment import (
    BRANCHES,
    COMPONENTS,
    SegmentedRecord,
    _build_model,
    _derive_seed,
    _images,
    _load_segmented_inputs,
    _read_configuration,
)
from experimento_feijao.preparation import (
    BEANS_CLASSES,
    ImageRecord,
    SEEDS,
    _download_mirror_archive,
    _read_archive_records,
)

FIXED_IDENTITIES = {
    "angular_leaf_spot": "test-0042",
    "bean_rust": "test-0085",
    "healthy": "test-0000",
}


def _write_json(path: Path, document: object) -> None:
    """Grava um diagnóstico JSON no diretório de saída."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _gradcam_map(
    model: keras.Model,
    image: NDArray[np.uint8],
    class_index: int,
) -> NDArray[np.float32]:
    """Calcula o mapa Grad-CAM para uma classe predita."""
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
        convolutional_output, predictions = grad_model(input_tensor)
        score = predictions[:, class_index]
    gradients = tape.gradient(score, convolutional_output)
    weights = tf.reduce_mean(gradients, axis=(1, 2))
    activation = convolutional_output[0]
    cam = tf.reduce_sum(activation * weights[0][None, None, :], axis=-1)
    cam = tf.maximum(cam, 0)
    maximum = tf.reduce_max(cam)
    cam = tf.where(maximum > 0, cam / maximum, cam)
    return np.asarray(cam, dtype=np.float32)


def _panel(
    original: NDArray[np.uint8],
    segmented: NDArray[np.uint8],
    cam: NDArray[np.float32],
) -> NDArray[np.uint8]:
    """Monta o painel com imagem original, entrada e sobreposição."""
    size = (segmented.shape[1], segmented.shape[0])
    heatmap_input = np.asarray(np.clip(cam * 255, 0, 255), dtype=np.uint8)
    heatmap = cv2.applyColorMap(heatmap_input, cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    heatmap = cv2.resize(heatmap, size, interpolation=cv2.INTER_LINEAR)
    overlay = cv2.addWeighted(segmented, 0.6, heatmap, 0.4, 0)
    original_resized = cv2.resize(original, size, interpolation=cv2.INTER_AREA)
    return np.concatenate((original_resized, segmented, overlay), axis=1)


def _fixed_examples(
    segmented_root: Path,
) -> dict[str, tuple[SegmentedRecord, ImageRecord]]:
    """Carrega os três exemplos fixos e suas imagens originais."""
    records = _load_segmented_inputs(segmented_root)
    segmented_by_identity = {
        record.identity: record for record in records["test"]
    }
    original_records = _read_archive_records(
        _download_mirror_archive("test"), "test"
    )
    original_by_identity = {record.identity: record for record in original_records}
    return {
        class_name: (
            segmented_by_identity[identity],
            original_by_identity[identity],
        )
        for class_name, identity in FIXED_IDENTITIES.items()
    }


def run_gradcam(
    configuration_path: Path,
    segmented_root: Path,
    output: Path,
) -> None:
    """Gera Grad-CAM para os três exemplos fixos dos 30 pares."""
    examples = _fixed_examples(segmented_root)

    for pair_seed in SEEDS:
        training = _read_configuration(configuration_path)
        component_seeds = {
            component: _derive_seed(pair_seed, component)
            for component in COMPONENTS
        }
        for branch in BRANCHES:
            checkpoint = (
                output
                / "checkpoints"
                / f"pair-{pair_seed}"
                / f"{branch}.weights.h5"
            )
            if not checkpoint.is_file():
                raise ValueError(f"checkpoint V2 não encontrado: {checkpoint}")

            model = _build_model(branch, component_seeds, training)
            try:
                model.load_weights(checkpoint)
                metadata: dict[str, Any] = {
                    "schema_version": 1,
                    "seed": pair_seed,
                    "branch": branch,
                    "target": "predicted_class",
                    "examples": {},
                }
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
                        "path": str(image_path),
                        "predicted_class": BEANS_CLASSES[predicted_index],
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
