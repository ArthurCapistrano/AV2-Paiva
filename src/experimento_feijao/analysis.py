from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import ttest_rel  # type: ignore[import-untyped]

from experimento_feijao.preparation import SEEDS

ARMS = ("solucao_principal", "solucao_contrafactual")
METRICS = ("macro_f1", "accuracy")


class AnalysisError(ValueError):
    """Erro ao consolidar os resultados dos pares experimentais."""


def _read_results(results_root: Path) -> list[dict[str, Any]]:
    """Lê os 30 resultados individuais da campanha.

    Args:
        results_root: Diretório que contém uma pasta por par experimental.

    Returns:
        Resultados ordenados pelas seeds do protocolo.

    Raises:
        AnalysisError: Se a campanha não contiver exatamente as 30 seeds.
    """
    paths = sorted(results_root.glob("pair-*/result.json"))
    if len(paths) != 30:
        raise AnalysisError("exactly 30 paired results are required")

    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AnalysisError(f"could not read result: {path}") from error
        if not isinstance(result, dict):
            raise AnalysisError(f"invalid result: {path}")
        results.append(result)
    results = sorted(results, key=lambda result: result["seed"])
    if [result.get("seed") for result in results] != list(SEEDS):
        raise AnalysisError("results must contain the 30 fixed seeds exactly once")
    return results


def _values(results: list[dict[str, Any]], arm: str, metric: str) -> np.ndarray:
    return np.asarray(
        [float(result[arm][metric]) for result in results], dtype=np.float64
    )


def _summary(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
    }


def analyze(results_root: Path) -> dict[str, Any]:
    """Consolida métricas e calcula o teste t pareado bilateral.

    Args:
        results_root: Diretório com os resultados individuais da campanha.

    Returns:
        Resumo das métricas, diferenças pareadas e teste estatístico.

    Raises:
        AnalysisError: Se os resultados não formarem a campanha esperada.
    """
    results = _read_results(results_root)
    metrics = {
        metric: {
            arm: _summary(_values(results, arm, metric))
            for arm in ARMS
        }
        for metric in METRICS
    }
    principal_f1 = _values(results, ARMS[0], "macro_f1")
    counterfactual_f1 = _values(results, ARMS[1], "macro_f1")
    differences = principal_f1 - counterfactual_f1
    test = ttest_rel(principal_f1, counterfactual_f1)

    return {
        "pair_count": len(results),
        "seeds": [int(result["seed"]) for result in results],
        "metrics": metrics,
        "macro_f1_differences": [float(value) for value in differences],
        "paired_t_test": {
            "statistic": float(test.statistic),
            "p_value": float(test.pvalue),
        },
    }
