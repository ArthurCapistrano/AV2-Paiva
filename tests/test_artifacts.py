from __future__ import annotations

import json

import pytest

from experimento_feijao.artifacts import sha256, write_json


def test_write_json_rejects_non_finite_numbers(tmp_path):
    path = tmp_path / "result.json"

    with pytest.raises(ValueError, match="não finito"):
        write_json(path, {"loss": float("nan")})

    assert not path.exists()


def test_write_json_replaces_a_complete_document(tmp_path):
    path = tmp_path / "result.json"

    write_json(path, {"value": 1})

    assert json.loads(path.read_text(encoding="utf-8")) == {"value": 1}
    assert len(sha256(path)) == 64
