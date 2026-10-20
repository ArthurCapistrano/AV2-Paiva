from __future__ import annotations

from pathlib import Path

import keras
import numpy as np

from experimento_feijao.experiment import (
    BATCH_NORMALIZATION_MOMENTUM,
    _build_model,
    _calibrate_batch_normalization,
    _read_configuration,
)


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
    base = next(layer for layer in model.layers if isinstance(layer, keras.Model))
    assert {
        layer.momentum
        for layer in base.layers
        if isinstance(layer, keras.layers.BatchNormalization)
    } == {BATCH_NORMALIZATION_MOMENTUM}


def test_batch_normalization_calibration_uses_training_inputs():
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
    base = next(layer for layer in model.layers if isinstance(layer, keras.Model))
    batchnorm = [
        layer
        for layer in base.layers
        if isinstance(layer, keras.layers.BatchNormalization)
    ]
    before = [layer.moving_mean.numpy().copy() for layer in batchnorm]
    images = np.full((4, 160, 160, 3), 255, dtype=np.uint8)

    _calibrate_batch_normalization(model, images, batch_size=2)

    assert any(
        not np.array_equal(previous, layer.moving_mean.numpy())
        for previous, layer in zip(before, batchnorm, strict=True)
    )
