from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, TypeGuard

from experimento_feijao.experiment import ExperimentError, run_pair
from experimento_feijao.preparation import PreparationError, prepare

LIBRARIES = (
    "keras",
    "numpy",
    "opencv-python-headless",
    "scikit-learn",
    "scipy",
    "tensorflow",
    "tensorflow-datasets",
)
FUTURE_OPERATIONS = {
    "consolidate": "consolidate run artifacts",
    "analyze": "perform statistical analysis",
    "grad-cam": "generate Grad-CAM visualizations",
}


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_hsv_triplet(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(channel, int) and 0 <= channel <= 255 for channel in value)
    )


def _positive_integer(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _stabilization_epoch(window_minima: object) -> int | None:
    if not (
        isinstance(window_minima, list)
        and len(window_minima) >= 3
        and all(_finite_number(value) and value > 0 for value in window_minima)
    ):
        return None
    stable_comparisons = 0
    for index, current in enumerate(window_minima[1:], start=1):
        previous = window_minima[index - 1]
        relative_improvement = (previous - current) / previous
        stable_comparisons = (
            stable_comparisons + 1 if relative_improvement <= 0.01 else 0
        )
        if stable_comparisons == 2:
            return (index + 1) * 5
    return None


def _epoch_pilot_errors(training: dict[str, Any], configuration_dir: Path) -> list[str]:
    reference = training.get("pilot_evidence")
    if not _non_empty_string(reference):
        return ["training pilot evidence is required before fixing epochs"]

    evidence_path = configuration_dir / str(reference)
    try:
        evidence = _mapping(json.loads(evidence_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        return [f"Could not read training pilot evidence: {error}"]

    errors: list[str] = []
    if evidence.get("status") != "executed":
        errors.append("training pilot evidence must have status executed")
    if evidence.get("dataset_splits") != ["train", "validation"]:
        errors.append("training pilot evidence must use only train and validation")
    if evidence.get("test_data_accessed") is not False:
        errors.append("training pilot must not access test data")
    if evidence.get("selected_epochs") != training.get("epochs"):
        errors.append("selected epoch budget must match training pilot evidence")

    pilot_seeds = evidence.get("pilot_seeds")
    if not (
        isinstance(pilot_seeds, list)
        and bool(pilot_seeds)
        and all(
            isinstance(seed, int) and not isinstance(seed, bool)
            for seed in pilot_seeds
        )
        and len(set(pilot_seeds)) == len(pilot_seeds)
    ):
        errors.append("training pilot evidence must preserve unique pilot seeds")
    if not _mapping(evidence.get("training_configuration")):
        errors.append("training pilot evidence must preserve its configuration")

    rule = _mapping(evidence.get("stabilization_rule"))
    if not (
        rule.get("declared_before_pilot") is True
        and rule.get("metric") == "validation_loss"
        and rule.get("window_epochs") == 5
        and rule.get("maximum_relative_improvement") == 0.01
        and rule.get("required_stable_windows") == 2
    ):
        errors.append(
            "training pilot evidence must preserve the predeclared stabilization rule"
        )

    curves = _mapping(evidence.get("curve_summary"))
    selected_epochs = evidence.get("selected_epochs")
    stabilization_epochs: list[int] = []
    for arm in ("solucao_principal", "solucao_contrafactual"):
        curve = _mapping(curves.get(arm))
        losses = _mapping(curve.get("validation_loss"))
        stabilized_at = curve.get("stabilized_at_epoch")
        epochs_observed = curve.get("epochs_observed")
        window_minima = curve.get("window_minimum_validation_loss")
        derived_stabilization = _stabilization_epoch(window_minima)
        if not (
            _positive_integer(selected_epochs)
            and _positive_integer(stabilized_at)
            and stabilized_at <= selected_epochs
            and _positive_integer(epochs_observed)
            and epochs_observed >= selected_epochs
            and isinstance(window_minima, list)
            and epochs_observed == len(window_minima) * 5
            and derived_stabilization == stabilized_at
            and all(
                _finite_number(losses.get(name))
                for name in ("initial", "minimum", "final")
            )
        ):
            errors.append(
                f"training pilot evidence must summarize a stabilized curve for {arm}"
            )
        else:
            stabilization_epochs.append(stabilized_at)
    if stabilization_epochs and selected_epochs != max(stabilization_epochs):
        errors.append(
            "selected epoch budget must be the later stabilization of both arms"
        )
    return errors


def _validation_errors(configuration: object, configuration_dir: Path) -> list[str]:
    root = _mapping(configuration)
    errors: list[str] = []

    dataset = _mapping(root.get("dataset"))
    if dataset.get("version") != "beans:0.1.0":
        errors.append("dataset version must be exactly beans:0.1.0")

    segmentation = _mapping(root.get("segmentation"))
    hsv = _mapping(segmentation.get("hsv"))
    if not (
        segmentation.get("state") == "frozen"
        and _valid_hsv_triplet(hsv.get("lower"))
        and _valid_hsv_triplet(hsv.get("upper"))
    ):
        if segmentation.get("state") == "pending":
            errors.append(
                "segmentation parameters are pending; freeze them after the pilot"
            )
        else:
            errors.append("frozen HSV parameters are required")
    if not _non_empty_string(segmentation.get("pilot_evidence")):
        errors.append(
            "segmentation pilot evidence is required before freezing HSV values"
        )

    training = _mapping(root.get("training"))
    epochs = training.get("epochs")
    if not _positive_integer(epochs):
        errors.append("number of epochs must be a positive integer")
    errors.extend(_epoch_pilot_errors(training, configuration_dir))

    seeds = root.get("seeds")
    if not (
        isinstance(seeds, list)
        and len(seeds) == 30
        and all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
        and len(set(seeds)) == 30
    ):
        errors.append("exactly 30 unique seeds are required")

    checkpoint = _mapping(root.get("checkpoint"))
    if not _non_empty_string(checkpoint.get("rule")):
        errors.append("checkpoint rule is required")

    failure = _mapping(root.get("failure"))
    if not _non_empty_string(failure.get("policy")):
        errors.append("failure policy is required")

    return errors


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _gpu_names() -> list[str]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return []
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [name.strip() for name in result.stdout.splitlines() if name.strip()]


def _optional_nvidia_version(package: str) -> str | None:
    version = _package_version(package)
    return None if version == "not-installed" else version


def _environment() -> dict[str, Any]:
    machine = platform.machine()
    return {
        "python": platform.python_version(),
        "libraries": {library: _package_version(library) for library in LIBRARIES},
        "operating_system": platform.platform(),
        "hardware": {
            "machine": machine,
            "cpu": platform.processor() or machine,
            "gpu": _gpu_names(),
        },
        "cuda": _optional_nvidia_version("nvidia-cuda-runtime-cu12"),
        "cudnn": _optional_nvidia_version("nvidia-cudnn-cu12"),
    }


def _validate(args: argparse.Namespace) -> int:
    try:
        with args.config.open(encoding="utf-8") as config_file:
            configuration = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read configuration: {error}", file=sys.stderr)
        return 2

    errors = _validation_errors(configuration, args.config.parent)
    if errors:
        print("Protocol is invalid:", file=sys.stderr)
    for validation_error in errors:
        print(f"- {validation_error}", file=sys.stderr)
        return 2

    manifest = {
        "configuration": configuration,
        "environment": _environment(),
    }
    try:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as error:
        print(f"Could not write manifest: {error}", file=sys.stderr)
        return 2

    print(f"Protocol is valid. Manifest written to {args.manifest}")
    return 0


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"Operation '{args.operation}' is not implemented yet", file=sys.stderr)
    return 2


def _prepare(args: argparse.Namespace) -> int:
    try:
        configuration = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(configuration, dict):
            raise PreparationError("configuration must be an object")
        manifest = prepare(configuration, args.dataset_manifest, args.output)
    except (OSError, json.JSONDecodeError, PreparationError) as error:
        print(f"Could not prepare segmented inputs: {error}", file=sys.stderr)
        return 2
    print(f"Prepared {len(manifest['artifacts'])} segmented inputs in {args.output}")
    return 0


def _run(args: argparse.Namespace) -> int:
    try:
        run_pair(args.config, args.segmented_inputs, args.seed, args.output)
    except ExperimentError as error:
        print(
            f"Pair failed at stage '{error.stage}' for arm '{error.arm}' "
            f"and seed {error.seed}: {error}",
            file=sys.stderr,
        )
        return 2
    print(f"Experimental pair {args.seed} written to {args.output}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experimento-feijao",
        description="Reproducible bean leaf disease classification experiment",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate the frozen protocol and record the environment"
    )
    validate.add_argument("--config", required=True, type=Path)
    validate.add_argument("--manifest", type=Path, default=Path("manifest.json"))
    validate.set_defaults(handler=_validate)

    prepare_parser = subparsers.add_parser(
        "prepare", help="materialize deterministic segmented inputs"
    )
    prepare_parser.add_argument("--config", required=True, type=Path)
    prepare_parser.add_argument(
        "--dataset-manifest",
        type=Path,
        help="use an auditable local beans:0.1.0 manifest instead of TFDS",
    )
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.set_defaults(handler=_prepare)

    run_parser = subparsers.add_parser(
        "run", help="run one complete paired experiment"
    )
    run_parser.add_argument("--config", required=True, type=Path)
    run_parser.add_argument("--segmented-inputs", required=True, type=Path)
    run_parser.add_argument("--seed", required=True, type=int)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.set_defaults(handler=_run)

    for operation, help_text in FUTURE_OPERATIONS.items():
        future = subparsers.add_parser(operation, help=f"future: {help_text}")
        future.set_defaults(handler=_not_implemented)

    return parser


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(args.handler(args))
