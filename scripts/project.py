"""Cross-platform local tasks; failures stop the pipeline immediately."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def lint() -> None:
    for args in (("check",), ("format", "--check")):
        run(sys.executable, "-m", "ruff", *args, "src", "tests", "scripts")
    run(sys.executable, "-m", "mypy", "src")


def docs() -> None:
    for relative in (".quarto-tmp", ".cache/quarto-home", ".cache/deno"):
        (ROOT / relative).mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "HOME": str(ROOT / ".cache/quarto-home"),
        "TMPDIR": str(ROOT / ".quarto-tmp"),
        "XDG_CACHE_HOME": str(ROOT / ".cache"),
        "DENO_DIR": str(ROOT / ".cache/deno"),
    }
    subprocess.run(
        ["quarto", "render", "docs", "--no-execute-daemon"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    run(sys.executable, "scripts/build_colab_notebooks.py")
    run(sys.executable, "scripts/check_site.py")


def clean() -> None:
    """Remove only known generated locations; never walk virtual environments."""
    targets = [
        ROOT / name
        for name in (
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".quarto-tmp",
            ".cache",
            "docs/_site",
            "docs/.quarto",
            "htmlcov",
        )
    ]
    for source in (ROOT / "docs").rglob("*.qmd"):
        targets.append(source.with_name(f"{source.stem}_files"))
    for folder in ("src", "tests", "scripts"):
        targets.extend((ROOT / folder).rglob("__pycache__"))
    targets.extend((ROOT / "src").glob("*.egg-info"))
    for target in targets:
        if target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
    (ROOT / ".coverage").unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task", choices=["lint", "test", "docs", "preview", "clean", "all"]
    )
    task = parser.parse_args().task
    if task in {"lint", "all"}:
        lint()
    if task in {"test", "all"}:
        run(sys.executable, "-m", "pytest", "-q")
    if task == "all":
        run("uv", "build")
    if task in {"docs", "preview", "all"}:
        docs()
    if task == "preview":
        run("quarto", "preview", "docs")
    if task == "clean":
        clean()


if __name__ == "__main__":
    main()
