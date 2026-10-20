from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_SEGMENTED_OUTPUT = Path("artifacts/v1/segmented")


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
        run_experiment(args.config, args.segmented_inputs, args.output, args.seed)
    except (OSError, ValueError) as error:
        print(f"Não foi possível executar o experimento: {error}", file=sys.stderr)
        return 2

    pair_count = 1 if args.seed is not None else len(SEEDS)
    print(f"Experimento com {pair_count} pares gravado em {args.output}")
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
        if args.output is not None:
            args.output.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except (OSError, ValueError) as error:
        print(f"Não foi possível analisar os resultados: {error}", file=sys.stderr)
        return 2

    _print_metric_summaries(summary)
    _print_paired_f1_difference(summary)
    return 0


def _gradcam(args: argparse.Namespace) -> int:
    """Gera os mapas Grad-CAM dos exemplos fixos da V2.

    Args:
        args: Parâmetros da operação `gradcam`.

    Returns:
        Código zero em caso de sucesso ou dois quando a geração falha.
    """
    from experimento_feijao.gradcam import run_gradcam

    try:
        run_gradcam(args.config, args.segmented_inputs, args.output, args.seed)
    except (OSError, ValueError) as error:
        print(f"Não foi possível gerar os mapas Grad-CAM: {error}", file=sys.stderr)
        return 2

    print(f"Grad-CAM gravado em {args.output / 'gradcam'}")
    return 0


def _print_metric_summaries(summary: dict[str, Any]) -> None:
    """Apresenta média e desvio-padrão de cada métrica consolidada."""
    print(f"{summary['pair_count']} pares experimentais")
    print("F1 macro")
    for arm, values in summary["metrics"]["macro_f1"].items():
        print(f"  {arm}: média={values['mean']:.4f}, desvio-padrão={values['std']:.4f}")
    print("Acurácia")
    for arm, values in summary["metrics"]["accuracy"].items():
        print(f"  {arm}: média={values['mean']:.4f}, desvio-padrão={values['std']:.4f}")


def _print_paired_f1_difference(summary: dict[str, Any]) -> None:
    """Apresenta a diferença pareada de F1 e seu teste estatístico."""
    difference = summary["paired_macro_f1_difference"]
    differences = difference["values"]
    print("Diferenças pareadas de F1 macro")
    print(
        f"  média={sum(differences) / len(differences):.4f}, "
        f"quantidade={len(differences)}"
    )
    test = difference["t_test"]
    print(
        "Teste t pareado: "
        f"estatística={test['statistic']:.4f}, valor-p={test['p_value']:.4g}"
    )


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
    prepare_parser.add_argument(
        "--output", type=Path, default=DEFAULT_SEGMENTED_OUTPUT
    )
    prepare_parser.set_defaults(handler=_prepare)

    experiment_parser = subparsers.add_parser(
        "experiment", help="executa os pares experimentais configurados"
    )
    experiment_parser.add_argument("--config", required=True, type=Path)
    experiment_parser.add_argument("--segmented-inputs", required=True, type=Path)
    experiment_parser.add_argument("--output", required=True, type=Path)
    experiment_parser.add_argument(
        "--seed", type=int, help="executa somente o par experimental desta seed"
    )
    experiment_parser.set_defaults(handler=_experiment)

    analyze_parser = subparsers.add_parser(
        "analyze", help="analisa os resultados dos pares experimentais"
    )
    analyze_parser.add_argument("--results", required=True, type=Path)
    analyze_parser.add_argument("--output", type=Path)
    analyze_parser.set_defaults(handler=_analyze)

    gradcam_parser = subparsers.add_parser(
        "gradcam", help="gera os mapas Grad-CAM dos exemplos fixos"
    )
    gradcam_parser.add_argument("--config", required=True, type=Path)
    gradcam_parser.add_argument("--segmented-inputs", required=True, type=Path)
    gradcam_parser.add_argument("--output", required=True, type=Path)
    gradcam_parser.add_argument(
        "--seed", type=int, help="gera Grad-CAM somente para esta seed"
    )
    gradcam_parser.set_defaults(handler=_gradcam)

    return parser


def main() -> None:
    """Executa a operação escolhida na CLI."""
    args = _parser().parse_args()
    raise SystemExit(args.handler(args))
