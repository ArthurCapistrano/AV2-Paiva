from __future__ import annotations

import hashlib
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

SPLITS = ("train", "validation", "test")
BEANS_CLASSES = ("angular_leaf_spot", "bean_rust", "healthy")
SEEDS = tuple(range(1001, 1031))
BACKGROUND = (127, 127, 127)
MIRROR_BASE_URL = (
    "https://huggingface.co/datasets/AI-Lab-Makerere/beans/resolve/"
    "27aa014ce09b193e1a6f58112d4a66e0eddb69c5/data"
)
MIRROR_ARCHIVES = {
    "train": "284fe8456ce20687f4367ae7ad94a64577e7f9fde2c2c6b1c74340ab5dc82715",
    "validation": "90b7aa1c26d91d9afff07a30bbc67a5ea34f1f1397f068d8675be09d7d0c602d",
    "test": "ca67b15d960d1e2fd9d23fd8498ce86818ead90755c630a43baf19ec4af09312",
}


@dataclass(frozen=True)
class ImageRecord:
    """Representa uma imagem Beans carregada, sua identidade e sua classe."""

    identity: str
    label: str
    image: NDArray[np.uint8]


def _sha256(path: Path) -> str:
    """Calcula o SHA-256 de um arquivo em blocos."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_mirror_archive(split: str) -> Path:
    """Obtém um arquivo Beans do cache ou do espelho fixado.

    Args:
        split: Divisão do dataset a ser baixada.

    Returns:
        Caminho do arquivo ZIP validado.

    Raises:
        ValueError: Se o download falhar ou o checksum não conferir.
    """
    cache_root = Path(
        os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    )
    destination = (
        cache_root / "experimento-feijao" / "beans" / "0.1.0" / f"{split}.zip"
    )
    expected_sha256 = MIRROR_ARCHIVES[split]
    # O cache só é reutilizado depois de confirmar seu checksum.
    if destination.exists() and _sha256(destination) == expected_sha256:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".zip.partial")
    url = f"{MIRROR_BASE_URL}/{split}.zip?download=true"
    # O download parcial evita deixar um ZIP incompleto no cache final.
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open(
            "wb"
        ) as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
    except (OSError, urllib.error.URLError) as error:
        partial.unlink(missing_ok=True)
        raise ValueError(
            f"não foi possível baixar o arquivo Beans de {split}"
        ) from error

    # Só publica o arquivo depois da validação do conteúdo baixado.
    if _sha256(partial) != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ValueError(f"o checksum do arquivo Beans de {split} não confere")
    partial.replace(destination)
    return destination


def _read_archive_records(path: Path, split: str) -> list[ImageRecord]:
    """Lê e decodifica as imagens JPG de um arquivo ZIP do Beans."""
    records: list[ImageRecord] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"não foi possível ler o arquivo Beans de {split}") from error

    with archive:
        # O espelho contém imagens JPG organizadas por classe.
        image_members = [
            member
            for member in archive.infolist()
            if not member.is_dir() and member.filename.lower().endswith(".jpg")
        ]
        for index, member in enumerate(image_members):
            # Cada imagem é convertida para RGB antes da segmentação.
            label = Path(member.filename).parent.name
            if label not in BEANS_CLASSES:
                raise ValueError(f"classe Beans inválida no arquivo de {split}")
            encoded = np.frombuffer(archive.read(member), dtype=np.uint8)
            image_bgr = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            if image_bgr is None:
                raise ValueError(
                    f"não foi possível decodificar a imagem Beans: {member.filename}"
                )
            records.append(
                ImageRecord(
                    f"{split}-{index:04d}",
                    label,
                    cast(NDArray[np.uint8], cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)),
                )
            )
    if not records:
        raise ValueError(f"o arquivo Beans de {split} não contém imagens")
    return records


def _load_beans_mirror() -> dict[str, list[ImageRecord]]:
    """Carrega os arquivos oficiais do Beans pelo espelho do Hugging Face."""
    return {
        split: _read_archive_records(_download_mirror_archive(split), split)
        for split in SPLITS
    }


def _validate_segmentation_configuration(
    configuration: dict[str, Any],
) -> dict[str, Any]:
    """Confirma que a configuração contém a seção de segmentação."""
    segmentation = configuration.get("segmentation")
    if not isinstance(segmentation, dict):
        raise ValueError("a configuração de segmentação é obrigatória")
    return segmentation


def _validate_segmentation_parameters(
    segmentation: dict[str, Any],
) -> tuple[NDArray[np.uint8], NDArray[np.uint8], int, int, int]:
    """Valida e converte os parâmetros fixos usados pela segmentação."""
    try:
        hsv = segmentation["hsv"]
        morphology = segmentation["morphology"]
        lower_values = hsv["lower"]
        upper_values = hsv["upper"]
        kernel_size = morphology["kernel_size"]
        open_iterations = morphology["open_iterations"]
        close_iterations = morphology["close_iterations"]
        if not all(
            isinstance(values, list)
            and len(values) == 3
            and all(
                isinstance(channel, int)
                and not isinstance(channel, bool)
                and 0 <= channel <= 255
                for channel in values
            )
            for values in (lower_values, upper_values)
        ):
            raise ValueError("os limites HSV são inválidos")
        if not (
            isinstance(kernel_size, int)
            and kernel_size > 0
            and kernel_size % 2 == 1
            and isinstance(open_iterations, int)
            and open_iterations >= 0
            and isinstance(close_iterations, int)
            and close_iterations >= 0
        ):
            raise ValueError("os parâmetros morfológicos são inválidos")
        lower = np.asarray(lower_values, dtype=np.uint8)
        upper = np.asarray(upper_values, dtype=np.uint8)
    except ValueError:
        raise
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError("a configuração de segmentação está incompleta") from error
    return (
        lower,
        upper,
        cast(int, kernel_size),
        cast(int, open_iterations),
        cast(int, close_iterations),
    )


def _write_segmented_image(image: NDArray[np.uint8], destination: Path) -> None:
    """Grava uma imagem segmentada convertendo-a de RGB para BGR."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(
        str(destination), cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ):
        raise ValueError(f"não foi possível gravar a imagem segmentada: {destination}")


def _leaf_mask(
    image: NDArray[np.uint8], segmentation: dict[str, Any]
) -> NDArray[np.uint8]:
    """Cria a máscara da folha e limpa pequenos ruídos.

    Os parâmetros de HSV e morfologia são os valores congelados do protocolo.
    """
    lower, upper, kernel_size, open_iterations, close_iterations = (
        _validate_segmentation_parameters(segmentation)
    )

    try:
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
    except (TypeError, ValueError, cv2.error) as error:
        raise ValueError("os parâmetros de segmentação são inválidos") from error
    return cast(NDArray[np.uint8], mask)


def _largest_leaf_silhouette(mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Seleciona a maior folha e preenche o contorno da sua silhueta."""
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if component_count <= 1:
        raise ValueError("nenhum componente de folha foi encontrado")

    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest_mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(
        largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    silhouette = np.zeros_like(largest_mask)
    cv2.drawContours(silhouette, [max(contours, key=cv2.contourArea)], -1, 255, -1)
    return silhouette


def _compose_segmented_image(
    image: NDArray[np.uint8], silhouette: NDArray[np.uint8]
) -> NDArray[np.uint8]:
    """Substitui o fundo e redimensiona a entrada para a rede."""
    # Mantém todas as cores da folha e troca somente o exterior pelo fundo neutro.
    composed = np.full_like(image, BACKGROUND)
    composed[silhouette == 255] = image[silhouette == 255]

    # Padroniza o tamanho esperado pela MobileNetV2.
    return cast(
        NDArray[np.uint8],
        cv2.resize(composed, (160, 160), interpolation=cv2.INTER_NEAREST),
    )


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
        ValueError: Se os parâmetros forem inválidos ou nenhuma folha for
            encontrada.
    """
    mask = _leaf_mask(image, segmentation)
    silhouette = _largest_leaf_silhouette(mask)
    return _compose_segmented_image(image, silhouette)


def prepare(
    configuration: dict[str, Any],
    output: Path,
) -> dict[str, int]:
    """Prepara todos os splits e devolve a quantidade de entradas produzidas.

    Args:
        configuration: Dataset e parâmetros fixos de segmentação.
        output: Diretório que receberá as imagens segmentadas.

    Returns:
        Quantidade de entradas materializadas.

    Raises:
        ValueError: Se a configuração, o dataset ou a segmentação forem
            incompatíveis com o experimento.
    """
    segmentation = _validate_segmentation_configuration(configuration)
    if output.exists():
        raise ValueError(f"a saída já existe: {output}")

    # Carrega o dataset uma vez e materializa cada split na saída.
    records = _load_beans_mirror()
    output.mkdir(parents=True)
    count = 0
    for split in SPLITS:
        for record in records[split]:
            segmented = _segment(record.image, segmentation)
            destination = (
                output / "images" / split / record.label / f"{record.identity}.png"
            )
            _write_segmented_image(segmented, destination)
            count += 1
    return {"count": count}
