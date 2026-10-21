from __future__ import annotations

import json
from argparse import Namespace

import pytest

from experimento_feijao.cli import _analyze
from experimento_feijao.experiment import BRANCHES, run_experiment
from experimento_feijao import gradcam


def test_run_experiment_rejects_non_empty_output(tmp_path):
    output = tmp_path / "campaign"
    output.mkdir()
    (output / "marker.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(ValueError, match="já existe"):
        run_experiment(
            tmp_path / "protocol.json",
            tmp_path / "segmented",
            output,
        )


def test_analyze_rejects_existing_summary(tmp_path, monkeypatch):
    output = tmp_path / "summary.json"
    output.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "experimento_feijao.analysis.analyze",
        lambda _: {"unused": True},
    )

    assert _analyze(Namespace(results=tmp_path, output=output)) == 2


def test_gradcam_rejects_existing_diagnostic(tmp_path, monkeypatch):
    output = tmp_path / "campaign"
    seed = 1001
    for branch in BRANCHES:
        checkpoint = output / "checkpoints" / f"pair-{seed}" / f"{branch}.weights.h5"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(b"weights")
        result = output / "results" / f"pair-{seed}" / branch / "result.json"
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(
            json.dumps({"seed": seed, "branch": branch}),
            encoding="utf-8",
        )
        diagnostic = output / "gradcam" / f"pair-{seed}" / branch / "diagnostic.json"
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        diagnostic.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(gradcam, "_fixed_examples", lambda _: {})
    monkeypatch.setattr(gradcam, "_read_configuration", lambda _: {})
    monkeypatch.setattr(gradcam, "validate_checkpoint_reference", lambda *args: None)

    with pytest.raises(ValueError, match="Grad-CAM já existe"):
        gradcam.run_gradcam(
            tmp_path / "protocol.json",
            tmp_path / "segmented",
            output,
            seed,
        )
