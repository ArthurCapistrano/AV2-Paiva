from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import experimento_feijao.cli as cli
import experimento_feijao.experiment as experiment_module


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["experimento-feijao", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_help_exposes_only_the_simple_experiment_operations() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    for operation in ("prepare", "experiment", "analyze"):
        assert operation in result.stdout
    for removed_operation in (
        "run",
        "campaign",
        "validate",
        "pilot",
        "consolidate",
        "grad-cam",
    ):
        assert removed_operation not in result.stdout


def test_analyze_prints_the_minimum_paired_summary(tmp_path: Path) -> None:
    results = tmp_path / "results"
    for seed in range(1001, 1031):
        pair = results / f"pair-{seed}"
        pair.mkdir(parents=True)
        pair.joinpath("result.json").write_text(
            json.dumps(
                {
                    "seed": seed,
                    "solucao_principal": {"macro_f1": 0.8, "accuracy": 0.9},
                    "solucao_contrafactual": {
                        "macro_f1": 0.6,
                        "accuracy": 0.7,
                    },
                }
            ),
            encoding="utf-8",
        )

    summary_path = tmp_path / "summary.json"
    result = run_cli(
        "analyze",
        "--results",
        str(results),
        "--output",
        str(summary_path),
    )

    assert result.returncode == 0, result.stderr
    assert "30 pares experimentais" in result.stdout
    assert "F1 macro" in result.stdout
    assert "Acurácia" in result.stdout
    assert "Diferenças pareadas" in result.stdout
    assert "valor-p" in result.stdout
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["pair_count"] == 30
    principal_mean = summary["metrics"]["macro_f1"]["solucao_principal"]["mean"]
    assert abs(principal_mean - 0.8) < 1e-12
    accuracy_mean = summary["metrics"]["accuracy"]["solucao_principal"]["mean"]
    assert abs(accuracy_mean - 0.9) < 1e-12
    macro_f1_std = summary["metrics"]["macro_f1"]["solucao_principal"]["std"]
    assert abs(macro_f1_std) < 1e-12
    assert all(
        abs(difference - 0.2) < 1e-12
        for difference in summary["differences"]["macro_f1"]
    )
    assert all(
        abs(difference - 0.2) < 1e-12
        for difference in summary["differences"]["accuracy"]
    )
    assert set(summary["paired_t_test"]) == {"statistic", "p_value"}


def test_experiment_validates_and_delegates_fixed_seeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configuration = tmp_path / "protocol.json"
    configuration.write_text(
        json.dumps(
            {
                "dataset": {"version": "beans:0.1.0"},
                "seeds": list(range(1001, 1031)),
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[Path, Path, Path]] = []

    def fake_run_experiment(config: Path, segmented: Path, output: Path) -> None:
        calls.append((config, segmented, output))

    monkeypatch.setattr(experiment_module, "run_experiment", fake_run_experiment)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "experimento-feijao",
            "experiment",
            "--config",
            str(configuration),
            "--segmented-inputs",
            str(tmp_path / "segmented"),
            "--output",
            str(tmp_path / "results"),
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert calls == [
        (
            configuration,
            tmp_path / "segmented",
            tmp_path / "results",
        )
    ]


def test_run_experiment_writes_one_result_per_fixed_seed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executed: list[tuple[int, str]] = []
    current_seed = [0]

    monkeypatch.setattr(
        experiment_module, "_load_segmented_inputs", lambda _root: {}
    )

    def fake_run_branch(
        branch: str,
        seeds: dict[str, int],
        training: dict[str, object],
        records: dict[str, list[object]],
    ) -> dict[str, float]:
        del seeds, training, records
        executed.append((current_seed[0], branch))
        return {"macro_f1": 0.8, "accuracy": 0.9}

    def fake_configuration(_path: Path, seed: int) -> dict[str, object]:
        current_seed[0] = seed
        return {}

    monkeypatch.setattr(
        experiment_module, "_read_configuration", fake_configuration
    )
    monkeypatch.setattr(experiment_module, "_run_branch", fake_run_branch)

    output = tmp_path / "results"
    experiment_module.run_experiment(
        tmp_path / "protocol.json", tmp_path / "segmented", output
    )

    assert sorted(output.glob("pair-*/result.json")) == [
        output / f"pair-{seed}" / "result.json"
        for seed in range(1001, 1031)
    ]
    assert [seed for seed, _branch in executed[::2]] == list(range(1001, 1031))
    assert [seed for seed, _branch in executed[1::2]] == list(range(1001, 1031))


def test_experiment_rejects_a_seed_list_outside_the_protocol(tmp_path: Path) -> None:
    configuration = tmp_path / "protocol.json"
    configuration.write_text(
        json.dumps({"dataset": {"version": "beans:0.1.0"}, "seeds": [1, 2, 3]}),
        encoding="utf-8",
    )

    result = run_cli(
        "experiment",
        "--config",
        str(configuration),
        "--segmented-inputs",
        str(tmp_path / "segmented"),
        "--output",
        str(tmp_path / "results"),
    )

    assert result.returncode == 2
    assert "30 fixed seeds" in result.stderr


def test_experiment_reports_missing_seeds_without_a_traceback(tmp_path: Path) -> None:
    configuration = tmp_path / "protocol.json"
    configuration.write_text(
        json.dumps({"dataset": {"version": "beans:0.1.0"}}),
        encoding="utf-8",
    )

    result = run_cli(
        "experiment",
        "--config",
        str(configuration),
        "--segmented-inputs",
        str(tmp_path / "segmented"),
        "--output",
        str(tmp_path / "results"),
    )

    assert result.returncode == 2
    assert "30 fixed seeds" in result.stderr
    assert "Traceback" not in result.stderr


def test_analyze_reports_incomplete_results_without_a_traceback(tmp_path: Path) -> None:
    results = tmp_path / "results"
    for seed in range(1001, 1031):
        pair = results / f"pair-{seed}"
        pair.mkdir(parents=True)
        pair.joinpath("result.json").write_text(
            json.dumps({"seed": seed}),
            encoding="utf-8",
        )

    result = run_cli("analyze", "--results", str(results))

    assert result.returncode == 2
    assert "result metrics are incomplete" in result.stderr
    assert "Traceback" not in result.stderr
