from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import zipfile
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
MIRROR_BASE_URL = (
    "https://huggingface.co/datasets/AI-Lab-Makerere/beans/resolve/main/data"
)
MIRROR_ARCHIVES = {
    "train": "284fe8456ce20687f4367ae7ad94a64577e7f9fde2c2c6b1c74340ab5dc82715",
    "validation": "90b7aa1c26d91d9afff07a30bbc67a5ea34f1f1397f068d8675be09d7d0c602d",
    "test": "ca67b15d960d1e2fd9d23fd8498ce86818ead90755c630a43baf19ec4af09312",
}


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
    """Lê uma imagem do disco e converte seus canais para RGB.

    Args:
        path: Caminho da imagem original.

    Returns:
        Imagem RGB em uma matriz NumPy.

    Raises:
        PreparationError: Se a imagem não puder ser lida.
    """
    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise PreparationError(f"could not read image: {path}")
    return cast(NDArray[np.uint8], cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))


def _load_manifest(path: Path) -> dict[str, list[ImageRecord]]:
    """Carrega as imagens de um manifesto local do dataset.

    Args:
        path: Manifesto da fixture local usada no ambiente controlado.

    Returns:
        Registros agrupados pelos três splits oficiais.

    Raises:
        PreparationError: Se o manifesto ou uma imagem forem incompatíveis.
    """
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_mirror_archive(split: str) -> Path:
    cache_root = Path(
        os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    )
    destination = (
        cache_root / "experimento-feijao" / "beans" / "0.1.0" / f"{split}.zip"
    )
    expected_sha256 = MIRROR_ARCHIVES[split]
    if destination.exists() and _sha256(destination) == expected_sha256:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".zip.partial")
    url = f"{MIRROR_BASE_URL}/{split}.zip?download=true"
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open(
            "wb"
        ) as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
    except (OSError, urllib.error.URLError) as error:
        partial.unlink(missing_ok=True)
        raise PreparationError(f"could not download Beans {split} archive") from error

    if _sha256(partial) != expected_sha256:
        partial.unlink(missing_ok=True)
        raise PreparationError(f"Beans {split} archive checksum mismatch")
    partial.replace(destination)
    return destination


def _read_archive_records(path: Path, split: str) -> list[ImageRecord]:
    records: list[ImageRecord] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise PreparationError(f"could not read Beans {split} archive") from error

    with archive:
        image_members = [
            member
            for member in archive.infolist()
            if not member.is_dir() and member.filename.lower().endswith(".jpg")
        ]
        for index, member in enumerate(image_members):
            label = Path(member.filename).parent.name
            if label not in BEANS_CLASSES:
                raise PreparationError(f"invalid Beans class in {split} archive")
            encoded = np.frombuffer(archive.read(member), dtype=np.uint8)
            image_bgr = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            if image_bgr is None:
                raise PreparationError(
                    f"could not decode Beans image: {member.filename}"
                )
            records.append(
                ImageRecord(
                    f"{split}-{index:04d}",
                    label,
                    cast(NDArray[np.uint8], cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)),
                )
            )
    if not records:
        raise PreparationError(f"Beans {split} archive has no images")
    return records


def _load_beans_mirror() -> dict[str, list[ImageRecord]]:
    """Carrega os arquivos oficiais do Beans pelo espelho do Hugging Face."""
    return {
        split: _read_archive_records(_download_mirror_archive(split), split)
        for split in SPLITS
    }


def _segment(
    image: NDArray[np.uint8], segmentation: dict[str, Any]
) -> NDArray[np.uint8]:
    """Remove o fundo e preserva o interior da folha na entrada segmentada.

    Args:
        image: Imagem RGB original.
        segmentation: Limites HSV e operações morfológicas congeladas.

    Returns:
        Imagem RGB redimensionada com o fundo substituído.

    Raises:
        PreparationError: Se os parâmetros forem inválidos ou nenhuma folha for
            encontrada.
    """
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
    """Prepara todos os splits e devolve a quantidade de entradas produzidas.

    Args:
        configuration: Dataset e parâmetros fixos de segmentação.
        dataset_manifest: Fonte local opcional para execução controlada.
        output: Diretório que receberá as imagens segmentadas.

    Returns:
        Quantidade de entradas materializadas.

    Raises:
        PreparationError: Se a configuração, o dataset ou a segmentação forem
            incompatíveis com o experimento.
    """
    dataset = _mapping(configuration.get("dataset"), "dataset configuration")
    if dataset.get("version") != DATASET_VERSION:
        raise PreparationError(f"dataset version must be {DATASET_VERSION}")

    segmentation = _mapping(
        configuration.get("segmentation"), "segmentation configuration"
    )
    if output.exists():
        raise PreparationError(f"output already exists: {output}")

    records = (
        _load_manifest(dataset_manifest)
        if dataset_manifest
        else _load_beans_mirror()
    )
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
