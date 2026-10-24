from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import t as student_t  # type: ignore[import-untyped]
from scipy.stats import shapiro  # type: ignore[import-untyped]
from scipy.stats import ttest_rel, wilcoxon  # type: ignore[import-untyped]

from experimento_feijao.artifacts import read_json
from experimento_feijao.preparation import SEEDS

BRANCHES = ("solucao_principal", "solucao_contrafactual")
RESULT_SCHEMA_VERSION = 2
METRICS = ("macro_f1", "accuracy")
NORMALITY_ALPHA = 0.05


def _read_results(results_root: Path) -> list[dict[str, Any]]:
    """Lê os pares na ordem das seeds do protocolo."""
    # O resumo só é válido quando todos os pares e seus dois ramos estão presentes.
    pair_paths = sorted((results_root / "results").glob("pair-*/result.json"))
    if len(pair_paths) != len(SEEDS):
        raise ValueError("são necessários exatamente 30 resultados pareados")

    results: list[dict[str, Any]] = []
    for pair_path in pair_paths:
        pair = read_json(pair_path)
        seed = pair.get("seed")
        if not isinstance(seed, int):
            raise ValueError(f"a seed está ausente no resultado: {pair_path}")

        # O arquivo do par aponta para um resultado detalhado de cada ramo.
        branches: dict[str, dict[str, Any]] = {}
        for branch in BRANCHES:
            branch_path = pair_path.parent / branch / "result.json"
            branch_result = read_json(branch_path)
            if branch_result.get("seed") != seed:
                raise ValueError(f"seed inconsistente no resultado: {branch_path}")
            if branch_result.get("branch") != branch:
                raise ValueError(f"ramo inconsistente no resultado: {branch_path}")
            for metric in METRICS:
                value = branch_result.get("evaluation", {}).get(metric)
                if not isinstance(value, (int, float)) or not np.isfinite(value):
                    raise ValueError(f"métrica inválida no resultado: {branch_path}")
            branches[branch] = branch_result
        results.append({"seed": seed, "branches": branches})

    # A ordem final segue as seeds do protocolo, não a ordem dos nomes dos arquivos.
    results.sort(key=lambda result: result["seed"])
    if [result["seed"] for result in results] != list(SEEDS):
        raise ValueError("os resultados devem conter as 30 seeds fixas uma única vez")
    return results


def _summary(values: np.ndarray) -> dict[str, float]:
    """Calcula a média e o desvio-padrão amostral."""
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
    }


def _metric_summaries(
    results: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    """Consolida as métricas de cada ramo."""
    # Calcula uma distribuição por métrica para cada ramo ao longo dos 30 pares.
    return {
        metric: {
            branch: _summary(
                np.asarray(
                    [
                        result["branches"][branch]["evaluation"][metric]
                        for result in results
                    ],
                    dtype=np.float64,
                )
            )
            for branch in BRANCHES
        }
        for metric in METRICS
    }


def _confidence_interval(values: list[float]) -> dict[str, float] | None:
    """Calcula o intervalo de confiança de 95% da média pareada."""
    if len(values) < 2:
        return None
    array = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(array))
    # Usa a distribuição t porque a média é estimada a partir das diferenças.
    standard_error = float(np.std(array, ddof=1) / np.sqrt(len(array)))
    critical = float(student_t.ppf(0.975, len(array) - 1))
    return {
        "mean": mean,
        "lower_95": mean - critical * standard_error,
        "upper_95": mean + critical * standard_error,
    }


def _prediction_counts(result: dict[str, Any]) -> dict[str, int]:
    """Conta as classes previstas em um resultado de ramo."""
    class_names = ("angular_leaf_spot", "bean_rust", "healthy")
    counts = {class_name: 0 for class_name in class_names}
    for prediction in result["predictions"]:
        class_name = prediction["predicted_class"]
        counts[class_name] += 1
    return {class_name: count for class_name, count in counts.items() if count}


def _normality(values: np.ndarray) -> dict[str, Any]:
    """Avalia a normalidade das diferenças pareadas por seed."""
    if len(values) < 3:
        return {
            "name": "shapiro_wilk",
            "statistic": None,
            "p_value": None,
            "alpha": NORMALITY_ALPHA,
            "normal": False,
            "reason": "amostra insuficiente",
        }
    if np.allclose(values, values[0]):
        return {
            "name": "shapiro_wilk",
            "statistic": None,
            "p_value": None,
            "alpha": NORMALITY_ALPHA,
            "normal": False,
            "reason": "diferenças constantes",
        }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        statistic, p_value = shapiro(values)
    return {
        "name": "shapiro_wilk",
        "statistic": float(statistic),
        "p_value": float(p_value),
        "alpha": NORMALITY_ALPHA,
        "normal": bool(p_value >= NORMALITY_ALPHA),
    }


def _paired_test(values: np.ndarray) -> dict[str, Any]:
    """Escolhe t pareado ou Wilcoxon com base na normalidade das diferenças."""
    normality = _normality(values)
    if normality["normal"]:
        statistic, p_value = ttest_rel(values, np.zeros_like(values))
        return {
            "name": "paired_t",
            "statistic": float(statistic),
            "p_value": float(p_value),
            "normality": normality,
        }

    nonzero = values[~np.isclose(values, 0)]
    has_ties = len(np.unique(np.abs(nonzero))) != len(nonzero)
    if len(nonzero) < 2:
        return {
            "name": "wilcoxon",
            "statistic": 0.0,
            "p_value": 1.0,
            "method": "insufficient_nonzero_differences",
            "zero_method": "wilcox",
            "nonzero_count": int(len(nonzero)),
            "ties": has_ties,
            "normality": normality,
        }

    method = "approx" if has_ties or len(nonzero) > 50 else "exact"
    statistic, p_value = wilcoxon(
        values,
        zero_method="wilcox",
        alternative="two-sided",
        method=method,
    )
    return {
        "name": "wilcoxon",
        "statistic": float(statistic),
        "p_value": float(p_value),
        "method": method,
        "zero_method": "wilcox",
        "nonzero_count": int(len(nonzero)),
        "ties": has_ties,
        "normality": normality,
    }


def _paired_difference_summary(
    principal: np.ndarray,
    counterfactual: np.ndarray,
) -> dict[str, Any]:
    """Resume uma diferença pareada e o teste escolhido para ela."""
    values = principal - counterfactual
    return {
        "values": [float(value) for value in values],
        "confidence_interval_95": _confidence_interval(values.tolist()),
        "test": _paired_test(values),
    }


def _seed_comparison(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compara o seed 1001 com os outros pares da campanha."""
    seed_result = next(result for result in results if result["seed"] == 1001)
    # O seed 1001 é comparado com o conjunto formado pelos outros 29 pares.
    other_results = [result for result in results if result["seed"] != 1001]
    comparison: dict[str, Any] = {
        "available": True,
        "seed_1001": {},
        "other_seeds": {},
    }
    for branch in BRANCHES:
        seed_branch = seed_result["branches"][branch]
        other_branches = [result["branches"][branch] for result in other_results]
        comparison["seed_1001"][branch] = {
            "accuracy": seed_branch["evaluation"]["accuracy"],
            "macro_f1": seed_branch["evaluation"]["macro_f1"],
            "predicted_class_counts": _prediction_counts(seed_branch),
        }
        comparison["other_seeds"][branch] = {
            "accuracy_mean": float(
                np.mean([item["evaluation"]["accuracy"] for item in other_branches])
            ),
            "constant_prediction_pairs": sum(
                len(_prediction_counts(item)) == 1 for item in other_branches
            ),
            "macro_f1_mean": float(
                np.mean([item["evaluation"]["macro_f1"] for item in other_branches])
            ),
            "pair_count": len(other_branches),
        }
    return comparison


def analyze(results_root: Path) -> dict[str, Any]:
    """Consolida métricas da campanha e calcula os testes pareados bilaterais."""
    results = _read_results(results_root)
    metrics = _metric_summaries(results)
    paired_metrics: dict[str, dict[str, Any]] = {}
    for metric in METRICS:
        principal = np.asarray(
            [
                result["branches"][BRANCHES[0]]["evaluation"][metric]
                for result in results
            ],
            dtype=np.float64,
        )
        counterfactual = np.asarray(
            [
                result["branches"][BRANCHES[1]]["evaluation"][metric]
                for result in results
            ],
            dtype=np.float64,
        )
        paired_metrics[metric] = _paired_difference_summary(
            principal, counterfactual
        )

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "pair_count": len(results),
        "seeds": [int(result["seed"]) for result in results],
        "metrics": metrics,
        "paired_macro_f1_difference": paired_metrics["macro_f1"],
        "paired_accuracy_difference": paired_metrics["accuracy"],
        "seed_1001_comparison": _seed_comparison(results),
    }
