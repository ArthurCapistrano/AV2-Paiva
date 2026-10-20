from __future__ import annotations

from pathlib import Path

from experimento_feijao.experiment import _build_model, _read_configuration


def test_model_exposes_logits_before_softmax_and_tracks_accuracy():
    training = _read_configuration(Path("protocol.json"))
    model = _build_model(
        "solucao_contrafactual",
        {
            "base": 1001,
            "head": 1002,
            "data": 1003,
            "augmentation": 1004,
            "dropout": 1005,
        },
        training,
    )

    logits = model.get_layer("classifier_logits")
    assert logits.activation.__name__ == "linear"
    assert model.get_layer("classifier_probabilities") is not None
    assert "accuracy" in model.get_compile_config()["metrics"]
