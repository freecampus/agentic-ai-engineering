"""Fail early unless Python and Poetry both use the activated Conda environment."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentCheckError(ValueError):
    """The selected development environment violates the repository policy."""


def check_conda_python() -> Path:
    """Reject missing activation, base, and a nested or unrelated Python venv."""
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix:
        raise EnvironmentCheckError("Activate Conda first: conda activate fc-agentic")
    if os.environ.get("CONDA_DEFAULT_ENV") == "base":
        raise EnvironmentCheckError("Use a project Conda environment, not base.")
    conda = Path(prefix).resolve()
    virtual_env = os.environ.get("VIRTUAL_ENV")
    # Poetry sets VIRTUAL_ENV to CONDA_PREFIX even when running Conda Python.
    # Reject a distinct/nested prefix, not that label alone; verify metadata below.
    if sys.prefix != sys.base_prefix or (
        virtual_env and Path(virtual_env).resolve() != conda
    ):
        raise EnvironmentCheckError(
            "A Python venv is active. Deactivate it, then activate fc-agentic."
        )
    if not (conda / "conda-meta").is_dir():
        raise EnvironmentCheckError(
            "CONDA_PREFIX does not identify a Conda environment."
        )
    if Path(sys.prefix).resolve() != conda:
        raise EnvironmentCheckError(
            "Python is not running from the activated Conda prefix."
        )
    return conda


def poetry_output(executable: str, *args: str) -> str:
    try:
        result = subprocess.run(
            [executable, *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EnvironmentCheckError(f"Unable to check Poetry: {exc}") from exc
    return result.stdout.strip()


def check_poetry_python(conda: Path, details: dict[str, Any]) -> None:
    """Check Poetry's actual interpreter, not merely its configuration flags."""
    if (
        details.get("prefix") != str(conda)
        or details.get("base_prefix") != str(conda)
        or not details.get("conda_metadata")
    ):
        raise EnvironmentCheckError(
            "Poetry selected a different or non-Conda interpreter. "
            "Check PATH, activation, and Poetry environment overrides."
        )


def check_environment() -> Path:
    conda = check_conda_python()
    executable = shutil.which("poetry")
    if not executable or not Path(executable).resolve().is_relative_to(conda):
        raise EnvironmentCheckError(
            "Poetry must be installed in the activated Conda environment."
        )
    for setting in ("virtualenvs.create", "virtualenvs.in-project"):
        if poetry_output(executable, "config", setting) != "false":
            raise EnvironmentCheckError(
                f"Poetry {setting} must be false. "
                "Remove conflicting environment overrides."
            )
    probe = (
        "import json, sys; from pathlib import Path; "
        "print(json.dumps({'prefix': str(Path(sys.prefix).resolve()), "
        "'base_prefix': str(Path(sys.base_prefix).resolve()), "
        "'conda_metadata': (Path(sys.prefix) / 'conda-meta').is_dir()}))"
    )
    try:
        details = json.loads(poetry_output(executable, "run", "python", "-c", probe))
    except json.JSONDecodeError as exc:
        raise EnvironmentCheckError(
            "Poetry's Python probe returned invalid data."
        ) from exc
    if not isinstance(details, dict):
        raise EnvironmentCheckError("Poetry's Python probe must return a mapping.")
    check_poetry_python(conda, details)
    return conda


def main() -> int:
    try:
        conda = check_environment()
    except EnvironmentCheckError as exc:
        print(f"Environment check failed: {exc}", file=sys.stderr)
        return 1
    print(f"Conda + Poetry verified: {conda} (no Python/Poetry venv).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
