"""Geração dos diagnósticos visuais Grad-CAM da campanha."""

from __future__ import annotations

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
from experimento_feijao.artifacts import validate_checkpoint_reference, write_json
from experimento_feijao.preparation import (
    BEANS_CLASSES,
    ImageRecord,
    SEEDS,
    _download_mirror_archive,
    _read_archive_records,
)

FIXED_IDENTITIES: dict[str, str] = {
    "angular_leaf_spot": "test-0042",
    "bean_rust": "test-0085",
    "healthy": "test-0000",
}
GRADCAM_SCHEMA_VERSION = 2


def _gradcam_map(
    model: keras.Model,
    image: NDArray[np.uint8],
    class_index: int,
) -> tuple[NDArray[np.float32], float]:
    """Calcula o mapa Grad-CAM para uma classe predita.

    Args:
        model: Modelo treinado que será interpretado.
        image: Imagem segmentada em RGB e no formato usado pelo treinamento.
        class_index: Índice da classe cujo gradiente será projetado.

    Returns:
        Mapa normalizado e o logit alvo, na resolução da camada convolucional.
    """
    # Recupera as camadas que participam do caminho original do modelo para
    # preservar exatamente a normalização e a cabeça usadas no treinamento.
    feature_extractor = next(
        layer for layer in model.layers if isinstance(layer, keras.Model)
    )
    preprocessing_layer = model.get_layer("mobilenet_v2_preprocessing")
    pooling_layer = next(
        layer
        for layer in model.layers
        if isinstance(layer, keras.layers.GlobalAveragePooling2D)
    )
    dropout_layer = next(
        layer for layer in model.layers if isinstance(layer, keras.layers.Dropout)
    )
    classifier_layer = model.get_layer("classifier_logits")

    normalized_input = preprocessing_layer(model.input)
    convolutional_output = feature_extractor(normalized_input, training=False)
    pooled_output = pooling_layer(convolutional_output)
    dropped_output = dropout_layer(pooled_output, training=False)
    predictions_output = classifier_layer(dropped_output)
    grad_model = keras.Model(model.input, [convolutional_output, predictions_output])
    input_tensor = tf.convert_to_tensor(image[None], dtype=tf.float32)

    # Calcula o gradiente da classe alvo e agrega os pesos por canal espacial.
    with tf.GradientTape() as tape:
        activations, predictions = grad_model(input_tensor)
        score = predictions[:, class_index]
    gradients = tape.gradient(score, activations)
    weights = tf.reduce_mean(gradients, axis=(1, 2))
    activation = activations[0]
    cam = tf.reduce_sum(activation * weights[0][None, None, :], axis=-1)

    # Remove contribuições negativas e normaliza o mapa para a visualização.
    cam = tf.maximum(cam, 0)
    maximum = tf.reduce_max(cam)
    cam = tf.where(maximum > 0, cam / maximum, cam)
    return np.asarray(cam, dtype=np.float32), float(score.numpy()[0])


def _panel(
    original: NDArray[np.uint8],
    segmented: NDArray[np.uint8],
    cam: NDArray[np.float32],
) -> NDArray[np.uint8]:
    """Monta o painel com imagem original, entrada e sobreposição.

    Args:
        original: Imagem original do dataset em RGB.
        segmented: Imagem segmentada usada pelo modelo.
        cam: Mapa Grad-CAM normalizado.

    Returns:
        Painel RGB com as três imagens lado a lado.
    """
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
    """Carrega os três exemplos fixos e suas imagens originais.

    Args:
        segmented_root: Diretório com as entradas segmentadas preparadas.

    Returns:
        Registros segmentados e originais indexados pelo nome da classe.
    """
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
    seed: int | None = None,
) -> None:
    """Gera Grad-CAM para os três exemplos fixos dos pares selecionados.

    Args:
        configuration_path: Arquivo JSON com a configuração fixa do treinamento.
        segmented_root: Diretório com as entradas segmentadas preparadas.
        output: Diretório raiz dos checkpoints e dos diagnósticos gerados.
        seed: Seed opcional para gerar Grad-CAM de somente um par.

    Raises:
        OSError: Se um artefato não puder ser lido ou gravado.
        ValueError: Se faltar um checkpoint ou houver uma entrada inválida.
    """
    if seed is not None and seed not in SEEDS:
        raise ValueError(f"seed inválida: {seed}")
    selected_seeds = SEEDS if seed is None else (seed,)
    # Os mesmos exemplos são usados em todos os pares para manter a comparação
    # visual controlada entre seeds e ramos.
    examples = _fixed_examples(segmented_root)
    training = _read_configuration(configuration_path)

    for pair_seed in selected_seeds:
        component_seeds = {
            component: _derive_seed(pair_seed, component)
            for component in COMPONENTS
        }

        # Valida os dois checkpoints antes de gerar qualquer painel do par.
        checkpoint_paths: dict[str, Path] = {}
        for branch in BRANCHES:
            checkpoint = (
                output
                / "checkpoints"
                / f"pair-{pair_seed}"
                / f"{branch}.weights.h5"
            )
            if not checkpoint.is_file():
                raise ValueError(f"checkpoint não encontrado: {checkpoint}")
            result_path = (
                output / "results" / f"pair-{pair_seed}" / branch / "result.json"
            )
            validate_checkpoint_reference(result_path, checkpoint, pair_seed, branch)
            checkpoint_paths[branch] = checkpoint

        for branch in BRANCHES:
            diagnostic_path = (
                output / "gradcam" / f"pair-{pair_seed}" / branch / "diagnostic.json"
            )
            image_paths = [
                diagnostic_path.with_name(f"{class_name}.png")
                for class_name in FIXED_IDENTITIES
            ]
            existing_path = next(
                (path for path in [diagnostic_path, *image_paths] if path.exists()),
                None,
            )
            if existing_path is not None:
                raise ValueError(f"o Grad-CAM já existe: {existing_path}")

        for branch in BRANCHES:
            model = _build_model(branch, component_seeds, training)
            try:
                checkpoint = checkpoint_paths[branch]
                model.load_weights(checkpoint)
                metadata: dict[str, Any] = {
                    "schema_version": GRADCAM_SCHEMA_VERSION,
                    "seed": pair_seed,
                    "branch": branch,
                    "target": "predicted_class",
                    "examples": {},
                }
                # Cada ramo gera um painel por classe fixa e um diagnóstico JSON.
                for class_name, example in examples.items():
                    segmented_record, original_record = example

                    # Prepara a imagem e obtém a classe prevista pelo modelo.
                    segmented = _images([segmented_record])[0]
                    probabilities = np.asarray(
                        model.predict(segmented[None], verbose=0)
                    )[0]
                    predicted_index = int(np.argmax(probabilities))

                    # Calcula o mapa Grad-CAM para a classe prevista.
                    cam, predicted_logit = _gradcam_map(
                        model, segmented, predicted_index
                    )

                    # Define o caminho do painel visual do exemplo atual.
                    image_path = (
                        output
                        / "gradcam"
                        / f"pair-{pair_seed}"
                        / branch
                        / f"{class_name}.png"
                    )
                    image_path.parent.mkdir(parents=True, exist_ok=True)

                    # Combina a imagem original, a segmentação e o mapa de ativação.
                    panel = _panel(original_record.image, segmented, cam)
                    written = cv2.imwrite(
                        str(image_path), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR)
                    )
                    if not written:
                        raise OSError(
                            f"não foi possível gravar o painel: {image_path}"
                        )

                    # Registra os metadados usados para auditar o diagnóstico visual.
                    metadata["examples"][class_name] = {
                        "identity": segmented_record.identity,
                        "path": str(image_path),
                        "predicted_class": BEANS_CLASSES[predicted_index],
                        "predicted_probability": float(probabilities[predicted_index]),
                        "predicted_logit": predicted_logit,
                        "score_type": "logit",
                    }
            finally:
                del model
                keras.backend.clear_session()

            write_json(
                output
                / "gradcam"
                / f"pair-{pair_seed}"
                / branch
                / "diagnostic.json",
                metadata,
            )
