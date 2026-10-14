from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _configuration(path: Path) -> dict[str, Any]:
    """Lê a configuração simples do experimento.

    Args:
        path: Arquivo JSON da configuração.

    Returns:
        Configuração carregada como um dicionário.

    Raises:
        OSError: Se o arquivo não puder ser lido.
        ValueError: Se o conteúdo não for um objeto JSON.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("configuration must be an object")
    return document


def _prepare(args: argparse.Namespace) -> int:
    """Prepara as entradas segmentadas do dataset pela CLI."""
    from experimento_feijao.preparation import prepare

    try:
        prepared = prepare(
            _configuration(args.config),
            args.dataset_manifest,
            args.output,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not prepare segmented inputs: {error}", file=sys.stderr)
        return 2

    print(f"Prepared {prepared['count']} segmented inputs in {args.output}")
    return 0


def _experiment(args: argparse.Namespace) -> int:
    """Executa os pares experimentais para todas as seeds configuradas.

    Args:
        args: Parâmetros da operação `experiment`.

    Returns:
        Código zero em caso de sucesso ou dois quando a campanha falha.
    """
    from experimento_feijao.experiment import run_pair
    from experimento_feijao.preparation import SEEDS

    try:
        configuration = _configuration(args.config)
        seeds = configuration.get("seeds")
        if seeds != list(SEEDS):
            raise ValueError("configuration must contain the 30 fixed seeds")
        for seed in seeds:
            run_pair(
                args.config,
                args.segmented_inputs,
                seed,
                args.output / f"pair-{seed}",
            )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not run experiment: {error}", file=sys.stderr)
        return 2

    print(f"Experiment with {len(seeds)} pairs written to {args.output}")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    """Analisa os resultados pareados da campanha pela CLI.

    Args:
        args: Parâmetros da operação `analyze`.

    Returns:
        Código zero em caso de sucesso ou dois quando a análise falha.
    """
    from experimento_feijao.analysis import analyze

    try:
        summary = analyze(args.results)
        if args.output is not None:
            args.output.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not analyze experimental results: {error}", file=sys.stderr)
        return 2

    print(f"{summary['pair_count']} pares experimentais")
    print("F1 macro")
    for arm, values in summary["metrics"]["macro_f1"].items():
        print(f"  {arm}: média={values['mean']:.4f}, desvio-padrão={values['std']:.4f}")
    print("Acurácia")
    for arm, values in summary["metrics"]["accuracy"].items():
        print(f"  {arm}: média={values['mean']:.4f}, desvio-padrão={values['std']:.4f}")
    print("Diferenças pareadas de F1 macro")
    differences = summary["differences"]["macro_f1"]
    print(
        f"  média={sum(differences) / len(differences):.4f}, "
        f"quantidade={len(differences)}"
    )
    accuracy_differences = summary["differences"]["accuracy"]
    print("Diferenças pareadas de acurácia")
    print(
        f"  média={sum(accuracy_differences) / len(accuracy_differences):.4f}, "
        f"quantidade={len(accuracy_differences)}"
    )
    test = summary["paired_t_test"]
    print(
        "Teste t pareado: "
        f"estatística={test['statistic']:.4f}, valor-p={test['p_value']:.4g}"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    """Cria a interface pública mínima da aplicação.

    Returns:
        Parser com as operações de preparação, execução e análise.
    """
    parser = argparse.ArgumentParser(
        prog="experimento-feijao",
        description="Experimento simples de classificacao de folhas de feijao",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare", help="prepare the shared segmented inputs"
    )
    prepare_parser.add_argument("--config", required=True, type=Path)
    prepare_parser.add_argument("--dataset-manifest", type=Path)
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.set_defaults(handler=_prepare)

    experiment_parser = subparsers.add_parser(
        "experiment", help="execute all configured paired experiments"
    )
    experiment_parser.add_argument("--config", required=True, type=Path)
    experiment_parser.add_argument("--segmented-inputs", required=True, type=Path)
    experiment_parser.add_argument("--output", required=True, type=Path)
    experiment_parser.set_defaults(handler=_experiment)

    analyze_parser = subparsers.add_parser(
        "analyze", help="analyze the paired experiment results"
    )
    analyze_parser.add_argument("--results", required=True, type=Path)
    analyze_parser.add_argument("--output", type=Path)
    analyze_parser.set_defaults(handler=_analyze)

    return parser


def main() -> None:
    """Executa a operação escolhida na CLI."""
    args = _parser().parse_args()
    raise SystemExit(args.handler(args))
