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


def _run(args: argparse.Namespace) -> int:
    """Executa um par experimental para uma seed pela CLI."""
    from experimento_feijao.experiment import run_pair

    try:
        run_pair(args.config, args.segmented_inputs, args.seed, args.output)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not run experimental pair: {error}", file=sys.stderr)
        return 2

    print(f"Experimental pair {args.seed} written to {args.output}")
    return 0


def _campaign(args: argparse.Namespace) -> int:
    """Executa um par experimental para cada seed configurada pela CLI."""
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
        print(f"Could not run experimental campaign: {error}", file=sys.stderr)
        return 2

    print(f"Experimental campaign with {len(seeds)} pairs written to {args.output}")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    """Analisa os resultados pareados da campanha pela CLI."""
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

    run_parser = subparsers.add_parser("run", help="run one paired experiment")
    run_parser.add_argument("--config", required=True, type=Path)
    run_parser.add_argument("--segmented-inputs", required=True, type=Path)
    run_parser.add_argument("--seed", required=True, type=int)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.set_defaults(handler=_run)

    campaign_parser = subparsers.add_parser(
        "campaign", help="run all configured paired experiments"
    )
    campaign_parser.add_argument("--config", required=True, type=Path)
    campaign_parser.add_argument("--segmented-inputs", required=True, type=Path)
    campaign_parser.add_argument("--output", required=True, type=Path)
    campaign_parser.set_defaults(handler=_campaign)

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
