"""Fail early unless Python is running in this project's uv environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentCheckError(RuntimeError):
    """The project command is running outside the uv-managed environment."""


def expected_environment() -> Path:
    configured = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if configured:
        path = Path(configured)
        return (path if path.is_absolute() else ROOT / path).resolve()
    return (ROOT / ".venv").resolve()


def check_environment() -> Path:
    """Require the interpreter selected by ``uv run`` for this checkout."""
    expected = expected_environment()
    actual = Path(sys.prefix).resolve()
    if actual != expected or actual == Path(sys.base_prefix).resolve():
        raise EnvironmentCheckError(
            "Project commands must use the uv-managed environment. "
            "Run `just setup`, then use a Just recipe or `uv run`."
        )
    return actual


def main() -> int:
    try:
        environment = check_environment()
    except EnvironmentCheckError as exc:
        print(f"Environment check failed: {exc}", file=sys.stderr)
        return 1
    print(f"uv project environment verified: {environment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
