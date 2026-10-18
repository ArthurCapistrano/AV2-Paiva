from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import cv2
import keras  # type: ignore[import-untyped]
import numpy as np
import tensorflow as tf  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sklearn.metrics import (  # type: ignore[import-untyped]
    classification_report,
    confusion_matrix,
)

from experimento_feijao.preparation import (
    BEANS_CLASSES,
    SEEDS,
    SPLITS,
)

BRANCHES: tuple[str, str] = (
    "solucao_principal",
    "solucao_contrafactual",
)

# Cada componente recebe uma seed própria para manter os ramos comparáveis.
COMPONENTS: tuple[str, ...] = (
    "base",  # Inicialização da base MobileNetV2.
    "head",  # Inicialização da cabeça classificadora.
    "data",  # Ordem dos dados em cada época.
    "augmentation",  # Espelhamento e variação de brilho.
    "dropout",  # Sorteio do dropout.
)
V2_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SegmentedRecord:
    """Representa uma entrada segmentada e seu rótulo numérico."""

    identity: str
    label: int
    path: Path


def _derive_seed(pair_seed: int, component: str) -> int:
    """Deriva uma seed estável para um componente do par experimental."""
    digest = hashlib.sha256(f"{pair_seed}:{component}".encode()).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _read_configuration(path: Path) -> dict[str, Any]:
    """Lê a configuração e devolve os parâmetros de treinamento.

    Args:
        path: Arquivo JSON da configuração fixa.
    Returns:
        Parâmetros de treinamento usados por todos os pares.

    Raises:
        ValueError: Se o arquivo não puder ser lido ou não for um objeto JSON.
    """
    try:
        configuration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(str(error)) from error
    if not isinstance(configuration, dict):
        raise ValueError("a configuração deve ser um objeto")

    return _validate_training_configuration(configuration)


def _validate_training_configuration(
    configuration: dict[str, Any],
) -> dict[str, Any]:
    """Confirma as seções mínimas usadas pelo treinamento.

    A validação verifica somente a estrutura necessária para executar o fluxo.
    Valores e tipos detalhados continuam sendo definidos pelo protocolo fixo.
    """
    training = configuration.get("training")
    if not isinstance(training, dict):
        raise ValueError("a configuração de treinamento é obrigatória")

    augmentation = training.get("augmentation")
    if not isinstance(augmentation, dict):
        raise ValueError("a configuração de aumento é obrigatória")
    try:
        training["epochs"]
        training["batch_size"]
        training["learning_rate"]
        training["l2"]
        training["dropout"]
        augmentation["horizontal_flip"]
        augmentation["brightness_delta"]
    except KeyError as error:
        raise ValueError("a configuração de treinamento está incompleta") from error

    if configuration.get("seeds") != list(SEEDS):
        raise ValueError("a configuração deve conter as 30 seeds fixas")
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
            raise ValueError(f"não foram encontradas entradas segmentadas para {split}")
    return records


def _images(records: list[SegmentedRecord]) -> NDArray[np.uint8]:
    """Carrega registros segmentados como imagens RGB em memória."""
    images: list[NDArray[np.uint8]] = []
    for record in records:
        image = cv2.imread(str(record.path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(
                f"não foi possível ler a entrada segmentada: {record.path}"
            )
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
    """Cria a mesma ordem e os mesmos aumentos para os dois ramos.

    Args:
        records: Entradas de treino e seus rótulos.
        images: Imagens RGB correspondentes aos registros.
        epoch: Índice da época atual.
        data_seed: Seed da ordem dos dados.
        augmentation_seed: Seed dos aumentos por imagem.
        horizontal_flip: Indica se o espelhamento pode ser aplicado.
        brightness_delta: Amplitude da variação de brilho.

    Returns:
        Imagens aumentadas e seus rótulos na ordem do treinamento.
    """
    # A ordem é sorteada uma vez por época e compartilhada pelos dois ramos.
    order = list(range(len(records)))
    random.Random(f"{data_seed}:{epoch}").shuffle(order)
    augmented: list[NDArray[np.float32]] = []
    labels: list[int] = []
    for index in order:
        record = records[index]
        augmented.append(
            _augment_image(
                images[index],
                record,
                epoch,
                augmentation_seed,
                horizontal_flip,
                brightness_delta,
            )
        )
        labels.append(record.label)
    return np.stack(augmented), np.asarray(labels, dtype=np.int64)


def _augment_image(
    image: NDArray[np.uint8],
    record: SegmentedRecord,
    epoch: int,
    augmentation_seed: int,
    horizontal_flip: bool,
    brightness_delta: float,
) -> NDArray[np.float32]:
    """Aplica espelhamento e brilho determinísticos a uma única imagem."""
    # O gerador local evita que uma imagem desloque a aleatoriedade das outras.
    local_seed = _derive_seed(augmentation_seed, f"{record.identity}:{epoch}")
    generator = np.random.default_rng(local_seed)
    augmented = image.astype(np.float32)

    # O espelhamento só é sorteado quando o protocolo permite esse aumento.
    if horizontal_flip and bool(generator.integers(0, 2)):
        augmented = np.flip(augmented, axis=1)

    # A variação é aplicada igualmente a todos os pixels da imagem.
    delta = float(generator.uniform(-brightness_delta, brightness_delta)) * 255

    return np.clip(augmented + delta, 0, 255).astype(np.float32)


def _build_model(
    branch: str,
    seeds: dict[str, int],
    training: dict[str, Any],
) -> keras.Model:
    """Constrói os dois ramos com a mesma topologia e cabeça.

    Args:
        branch: Solução principal ou solução contrafactual.
        seeds: Seeds dos componentes compartilhados do par.
        training: Hiperparâmetros fixos do treinamento.

    Returns:
        Modelo MobileNetV2 treinável e compilado.
    """
    # A solução principal usa ImageNet; o outro ramo usa pesos aleatórios.
    use_imagenet = branch == "solucao_principal"
    if not use_imagenet:
        keras.utils.set_random_seed(seeds["base"])

    # A base é comum aos ramos; apenas sua inicialização muda.
    base = keras.applications.MobileNetV2(
        input_shape=(160, 160, 3),
        alpha=1.0,
        include_top=False,
        weights="imagenet" if use_imagenet else None,
    )
    base.trainable = True

    # Cria a entrada e aplica a normalização esperada pela MobileNetV2.
    inputs = keras.Input(shape=(160, 160, 3), name="segmented_input")
    normalized = keras.layers.Lambda(
        keras.applications.mobilenet_v2.preprocess_input,
        name="mobilenet_v2_preprocessing",
    )(inputs)

    # Extrai as características da base e reduz suas dimensões espaciais.
    features = base(normalized)
    pooled = keras.layers.GlobalAveragePooling2D()(features)

    # Adiciona a cabeça classificadora comum aos dois ramos.
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

    # Monta e compila o modelo que será treinado.
    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(float(training["learning_rate"])),
        loss=keras.losses.SparseCategoricalCrossentropy(),
    )

    return model


def _fit_with_validation(
    model: keras.Model,
    train_records: list[SegmentedRecord],
    train_images: NDArray[np.uint8],
    validation_images: NDArray[np.float32],
    validation_labels: NDArray[np.int64],
    seeds: dict[str, int],
    training: dict[str, Any],
) -> tuple[int, float, list[dict[str, float]]]:
    """Treina, registra o histórico e mantém o melhor estado em memória."""
    augmentation = cast(dict[str, Any], training["augmentation"])
    best_loss = float("inf")
    best_epoch = 0
    best_weights = model.get_weights()
    history_rows: list[dict[str, float]] = []
    for epoch in range(int(training["epochs"])):
        # Os dados são recriados por época, mas permanecem determinísticos.
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
        history_rows.append(
            {
                "epoch": float(epoch + 1),
                **{
                    name: float(values[0])
                    for name, values in history.history.items()
                    if values
                },
            }
        )
        validation_loss = float(history.history["val_loss"][0])
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_epoch = epoch + 1
            best_weights = model.get_weights()

    model.set_weights(best_weights)
    return best_epoch, best_loss, history_rows


def _evaluation(
    records: list[SegmentedRecord],
    probabilities: NDArray[np.float32],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Calcula métricas detalhadas e previsões por imagem."""
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
    evaluation = {
        "accuracy": float(report["accuracy"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "per_class": {
            class_name: {
                metric: float(report[class_name][metric])
                for metric in ("precision", "recall", "f1-score", "support")
            }
            for class_name in BEANS_CLASSES
        },
        "confusion_matrix": confusion_matrix(
            labels,
            predictions,
            labels=list(range(len(BEANS_CLASSES))),
        ).tolist(),
    }
    prediction_rows = [
        {
            "identity": record.identity,
            "true_class": BEANS_CLASSES[record.label],
            "predicted_class": BEANS_CLASSES[prediction],
            "probabilities": {
                class_name: float(probability)
                for class_name, probability in zip(
                    BEANS_CLASSES, row, strict=True
                )
            },
        }
        for record, prediction, row in zip(
            records, predictions, probabilities, strict=True
        )
    ]
    return evaluation, prediction_rows


def _run_branch(
    branch: str,
    pair_seed: int,
    seeds: dict[str, int],
    training: dict[str, Any],
    records: dict[str, list[SegmentedRecord]],
    checkpoint: Path,
) -> dict[str, Any]:
    """Treina um ramo e devolve a telemetria detalhada da V2.

    Args:
        branch: Solução principal ou solução contrafactual.
        pair_seed: Seed do par experimental.
        seeds: Seeds derivadas para os componentes comuns do par.
        training: Hiperparâmetros fixos do treinamento.
        records: Entradas segmentadas organizadas por divisão.
        checkpoint: Caminho compatível do checkpoint do ramo.

    Returns:
        Resultado detalhado calculado no conjunto de teste.
    """
    model: keras.Model | None = None
    try:
        model = _build_model(branch, seeds, training)
        train_records = records["train"]
        validation_records = records["validation"]
        train_images = _images(train_records)
        validation_images = _images(validation_records).astype(np.float32)
        validation_labels = np.asarray(
            [record.label for record in validation_records], dtype=np.int64
        )
        started = time.perf_counter()
        best_epoch, best_loss, history = _fit_with_validation(
            model,
            train_records,
            train_images,
            validation_images,
            validation_labels,
            seeds,
            training,
        )
        training_seconds = time.perf_counter() - started
        test_records = records["test"]
        # A avaliação final usa o conjunto de teste apenas após selecionar os pesos.
        probabilities = np.asarray(model.predict(_images(test_records), verbose=0))
        evaluation, prediction_rows = _evaluation(test_records, probabilities)
        return {
            "schema_version": V2_SCHEMA_VERSION,
            "seed": pair_seed,
            "branch": branch,
            "best_epoch": best_epoch,
            "best_validation_loss": best_loss,
            "training_seconds": training_seconds,
            "history": history,
            "evaluation": evaluation,
            "predictions": prediction_rows,
            "checkpoint": str(checkpoint),
        }
    finally:
        del model
        keras.backend.clear_session()


def _run_pair(
    pair_seed: int,
    training: dict[str, Any],
    records: dict[str, list[SegmentedRecord]],
    output: Path,
) -> dict[str, dict[str, Any]]:
    """Executa os dois ramos usando as seeds derivadas do par."""
    seeds = {
        component: _derive_seed(pair_seed, component) for component in COMPONENTS
    }
    return {
        branch: _run_branch(
            branch,
            pair_seed,
            seeds,
            training,
            records,
            output / "checkpoints" / f"pair-{pair_seed}" / f"{branch}.weights.h5",
        )
        for branch in BRANCHES
    }


def _write_json(path: Path, document: object) -> None:
    """Grava um artefato JSON em seu diretório de saída."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_experiment(
    configuration_path: Path,
    segmented_root: Path,
    output: Path,
) -> None:
    """Executa e salva os 30 pares detalhados definidos no protocolo.

    Args:
        configuration_path: Configuração fixa do experimento.
        segmented_root: Diretório compartilhado de entradas segmentadas.
        output: Diretório raiz que contém resultados e artefatos V2.

    Raises:
        ValueError: Se a configuração, as entradas ou o treinamento falharem.
    """
    # A configuração e as entradas são carregadas antes de iniciar qualquer par.
    training = _read_configuration(configuration_path)
    records = _load_segmented_inputs(segmented_root)
    tf.config.experimental.enable_op_determinism()

    for pair_seed in SEEDS:
        pair_output = output / "results" / f"pair-{pair_seed}"
        result_path = pair_output / "result.json"

        results = _run_pair(pair_seed, training, records, output)
        branch_paths: dict[str, str] = {}
        for branch, result in results.items():
            branch_path = pair_output / branch / "result.json"
            _write_json(branch_path, result)
            branch_paths[branch] = str(branch_path)
        _write_json(
            result_path,
            {
                "schema_version": V2_SCHEMA_VERSION,
                "seed": pair_seed,
                "branches": branch_paths,
            },
        )
