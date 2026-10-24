from __future__ import annotations

from experimento_feijao.preparation import prepare


def test_prepare_reuses_an_existing_directory(tmp_path):
    output = tmp_path / "segmented"
    image = output / "images" / "test" / "healthy" / "test-0000.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"existing segmented input")

    result = prepare({"segmentation": {}}, output)

    assert result == {"count": 1, "reused": True}
