from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import ttest_rel  # type: ignore[import-untyped]

from experimento_feijao.preparation import SEEDS

BRANCHES = ("solucao_principal", "solucao_contrafactual")
METRICS = ("macro_f1", "accuracy")


def _read_results(results_root: Path) -> list[dict[str, Any]]:
    """Lê os 30 resultados individuais da campanha.

    Args:
        results_root: Diretório que contém uma pasta por par experimental.

    Returns:
        Resultados ordenados pelas seeds do protocolo.

    Raises:
        ValueError: Se a campanha não contiver exatamente as 30 seeds.
    """
    # A análise só é válida quando a campanha inteira está presente.
    paths = sorted(results_root.glob("pair-*/result.json"))
    if len(paths) != 30:
        raise ValueError("são necessários exatamente 30 resultados pareados")

    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"não foi possível ler o resultado: {path}") from error

        results.append(_validate_result(document, path))
    # A ordem final segue as seeds fixas, não a ordem dos nomes dos arquivos.
    results = sorted(results, key=lambda result: result["seed"])
    if [result.get("seed") for result in results] != list(SEEDS):
        raise ValueError("os resultados devem conter as 30 seeds fixas uma única vez")
    return results


def _validate_result(document: object, path: Path) -> dict[str, Any]:
    """Valida o formato de um resultado antes da consolidação estatística.

    Essa função é usada somente por :func:`_read_results`.
    """
    if not isinstance(document, dict):
        raise ValueError(f"resultado inválido: {path}")
    if not isinstance(document.get("seed"), int):
        raise ValueError(f"a seed está ausente no resultado: {path}")
    for branch in BRANCHES:
        metrics = document.get(branch)
        if not isinstance(metrics, dict) or any(
            not isinstance(metrics.get(metric), (int, float)) for metric in METRICS
        ):
            raise ValueError(f"as métricas do resultado estão incompletas: {path}")
    return document


def _values(results: list[dict[str, Any]], branch: str, metric: str) -> np.ndarray:
    """Extrai uma métrica de um ramo na ordem das seeds."""
    return np.asarray(
        [float(result[branch][metric]) for result in results], dtype=np.float64
    )


def _summary(values: np.ndarray) -> dict[str, float]:
    """Calcula a média e o desvio-padrão amostral de uma métrica."""
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
    }


def _paired_values(
    results: list[dict[str, Any]], metric: str
) -> tuple[np.ndarray, np.ndarray]:
    """Extrai os valores principal e contrafactual de uma métrica."""
    return (
        _values(results, BRANCHES[0], metric),
        _values(results, BRANCHES[1], metric),
    )


def _metric_summaries(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Consolida média e desvio-padrão para cada métrica e ramo."""
    return {
        metric: {
            branch: _summary(_values(results, branch, metric))
            for branch in BRANCHES
        }
        for metric in METRICS
    }


def _paired_differences(results: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Calcula as diferenças entre os ramos dentro de cada par experimental."""
    differences: dict[str, list[float]] = {}
    for metric in METRICS:
        principal, counterfactual = _paired_values(results, metric)
        differences[metric] = [
            float(value) for value in principal - counterfactual
        ]
    return differences


def _paired_f1_test(results: list[dict[str, Any]]) -> dict[str, float]:
    """Calcula o teste t pareado bilateral do F1 macro."""
    principal_f1, counterfactual_f1 = _paired_values(results, "macro_f1")
    test = ttest_rel(principal_f1, counterfactual_f1)
    return {
        "statistic": float(test.statistic),
        "p_value": float(test.pvalue),
    }


def analyze(results_root: Path) -> dict[str, Any]:
    """Consolida métricas e calcula o teste t pareado bilateral.

    Args:
        results_root: Diretório com os resultados individuais da campanha.

    Returns:
        Resumo das métricas, diferenças pareadas e teste estatístico.

    Raises:
        ValueError: Se os resultados não formarem a campanha esperada.
    """
    results = _read_results(results_root)

    return {
        "pair_count": len(results),
        "seeds": [int(result["seed"]) for result in results],
        "metrics": _metric_summaries(results),
        "differences": _paired_differences(results),
        "paired_t_test": _paired_f1_test(results),
    }
