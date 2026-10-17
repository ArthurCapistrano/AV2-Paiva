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
        raise ValueError("a configuração deve ser um objeto")
    return document


def _prepare(args: argparse.Namespace) -> int:
    """Prepara as entradas segmentadas do dataset pela CLI."""
    from experimento_feijao.preparation import prepare

    try:
        prepared = prepare(
            _configuration(args.config),
            args.output,
        )
    except (OSError, ValueError) as error:
        print(
            f"Não foi possível preparar as entradas segmentadas: {error}",
            file=sys.stderr,
        )
        return 2

    print(f"Preparadas {prepared['count']} entradas segmentadas em {args.output}")
    return 0


def _experiment(args: argparse.Namespace) -> int:
    """Executa os pares experimentais para todas as seeds configuradas.

    Args:
        args: Parâmetros da operação `experiment`.

    Returns:
        Código zero em caso de sucesso ou dois quando o experimento falha.
    """
    from experimento_feijao.experiment import run_experiment
    from experimento_feijao.preparation import SEEDS

    try:
        run_experiment(args.config, args.segmented_inputs, args.output)
    except (OSError, ValueError) as error:
        print(f"Não foi possível executar o experimento: {error}", file=sys.stderr)
        return 2

    print(f"Experimento com {len(SEEDS)} pares gravado em {args.output}")
    return 0


def _analyze(args: argparse.Namespace) -> int:
    """Analisa os resultados pareados do experimento pela CLI.

    Args:
        args: Parâmetros da operação `analyze`.

    Returns:
        Código zero em caso de sucesso ou dois quando a análise falha.
    """
    from experimento_feijao.analysis import analyze

    try:
        summary = analyze(args.results)
        if args.output is not None and not args.output.exists():
            args.output.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except (OSError, ValueError) as error:
        print(f"Não foi possível analisar os resultados: {error}", file=sys.stderr)
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
        description="Experimento simples de classificação de folhas de feijão",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare", help="prepara as entradas segmentadas compartilhadas"
    )
    prepare_parser.add_argument("--config", required=True, type=Path)
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.set_defaults(handler=_prepare)

    experiment_parser = subparsers.add_parser(
        "experiment", help="executa os pares experimentais configurados"
    )
    experiment_parser.add_argument("--config", required=True, type=Path)
    experiment_parser.add_argument("--segmented-inputs", required=True, type=Path)
    experiment_parser.add_argument("--output", required=True, type=Path)
    experiment_parser.set_defaults(handler=_experiment)

    analyze_parser = subparsers.add_parser(
        "analyze", help="analisa os resultados dos pares experimentais"
    )
    analyze_parser.add_argument("--results", required=True, type=Path)
    analyze_parser.add_argument("--output", type=Path)
    analyze_parser.set_defaults(handler=_analyze)

    return parser


def main() -> None:
    """Executa a operação escolhida na CLI."""
    args = _parser().parse_args()
    raise SystemExit(args.handler(args))
