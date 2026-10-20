from __future__ import annotations

import json

import pytest

from experimento_feijao.artifacts import sha256, validate_checkpoint_reference


def test_checkpoint_reference_accepts_matching_hash(tmp_path):
    checkpoint = tmp_path / "model.weights.h5"
    checkpoint.write_bytes(b"weights")
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "seed": 1001,
                "branch": "solucao_principal",
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": sha256(checkpoint),
            }
        ),
        encoding="utf-8",
    )

    validate_checkpoint_reference(
        result, checkpoint, 1001, "solucao_principal"
    )


def test_checkpoint_reference_rejects_changed_weights(tmp_path):
    checkpoint = tmp_path / "model.weights.h5"
    checkpoint.write_bytes(b"weights")
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "seed": 1001,
                "branch": "solucao_principal",
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="alterado"):
        validate_checkpoint_reference(
            result, checkpoint, 1001, "solucao_principal"
        )


def test_new_result_requires_checkpoint_hash(tmp_path):
    checkpoint = tmp_path / "model.weights.h5"
    checkpoint.write_bytes(b"weights")
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "seed": 1001,
                "branch": "solucao_principal",
                "checkpoint": str(checkpoint),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hash"):
        validate_checkpoint_reference(
            result, checkpoint, 1001, "solucao_principal"
        )
