"""Primitivas para publicar artefatos de campanha com segurança."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    """Calcula o SHA-256 de um arquivo em blocos."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, document: object) -> None:
    """Publica um JSON válido de forma atômica e sem valores não finitos."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        encoded = json.dumps(
            document,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
    except ValueError as error:
        raise ValueError("o documento contém valor não finito") from error
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    """Lê um objeto JSON produzido por uma etapa da campanha."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"não foi possível ler o artefato: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"o artefato deve ser um objeto JSON: {path}")
    return document


def validate_checkpoint_reference(
    result_path: Path,
    checkpoint: Path,
    seed: int,
    branch: str,
) -> dict[str, Any]:
    """Confirma que um resultado aponta para os pesos que serão consumidos."""
    result = read_json(result_path)
    if result.get("seed") != seed or result.get("branch") != branch:
        raise ValueError(f"resultado incompatível com o checkpoint: {result_path}")

    recorded_checkpoint = result.get("checkpoint")
    if not isinstance(recorded_checkpoint, str):
        raise ValueError(f"checkpoint ausente no resultado: {result_path}")
    if Path(recorded_checkpoint).resolve() != checkpoint.resolve():
        raise ValueError(f"resultado aponta para outro checkpoint: {result_path}")

    recorded_hash = result.get("checkpoint_sha256")
    if result.get("schema_version", 1) >= 2 and not isinstance(recorded_hash, str):
        raise ValueError(f"hash do checkpoint ausente no resultado: {result_path}")
    if recorded_hash is not None and recorded_hash != sha256(checkpoint):
        raise ValueError(f"checkpoint alterado desde o resultado: {checkpoint}")
    return result
