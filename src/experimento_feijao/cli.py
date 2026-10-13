from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

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
    "run": "run experimental pairs",
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


def _validation_errors(configuration: object) -> list[str]:
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
    if not isinstance(epochs, int) or isinstance(epochs, bool) or epochs <= 0:
        errors.append("number of epochs must be a positive integer")
    if not _non_empty_string(training.get("pilot_evidence")):
        errors.append("training pilot evidence is required before fixing epochs")

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

    errors = _validation_errors(configuration)
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

    for operation, help_text in FUTURE_OPERATIONS.items():
        future = subparsers.add_parser(operation, help=f"future: {help_text}")
        future.set_defaults(handler=_not_implemented)

    return parser


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(args.handler(args))
