from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_uv_metadata_preserves_package_extras_and_build_assets() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "freecampus-agents"
    assert config["project"]["requires-python"] == ">=3.10,<4"
    assert config["project"]["dependencies"] == []
    assert "notebooks" in config["project"]["optional-dependencies"]
    assert set(config["dependency-groups"]) == {"dev", "docs"}
    assert config["build-system"]["build-backend"] == "uv_build"
    assert config["build-system"]["requires"] == ["uv_build>=0.12.23,<0.13"]
    assert config["tool"]["uv"]["required-version"] == ">=0.12.13,<0.14"
    assert config["tool"]["uv"]["build-backend"] == {
        "module-name": "freecampus_agents",
        "module-root": "src",
    }
    assert (Path("src/freecampus_agents/py.typed")).is_file()
    assert list(Path("src/freecampus_agents/fixtures").glob("*.json"))
    assert "makim" not in str(config).lower()
    assert "poetry" not in str(config).lower()
    assert "quarto-cli==1.9.38" in config["dependency-groups"]["docs"]
    assert "PyYAML>=6,<7" in config["dependency-groups"]["dev"]
    assert Path("uv.lock").is_file()
    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.12"
    assert not any(Path(name).exists() for name in ("poetry.lock", "poetry.toml"))


def test_justfile_exposes_documented_project_recipes() -> None:
    justfile = Path("Justfile").read_text(encoding="utf-8")
    for recipe in (
        "setup:",
        "environment:",
        "plan-refresh:",
        "plan-check:",
        "lint:",
        "test:",
        "package:",
        "docs:",
        "review:",
        "preview:",
        "hooks:",
        "clean:",
        "ci:",
    ):
        assert recipe in justfile
    assert "uv run --locked" in justfile
    assert "makim" not in justfile.lower()


@pytest.mark.parametrize("name", ["ci", "docs"])
def test_workflows_install_uv_just_node_and_locked_dependencies(name: str) -> None:
    workflow = yaml.safe_load(
        Path(f".github/workflows/{name}.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["checks" if name == "ci" else "build"]
    assert job["defaults"]["run"]["shell"] == "bash"
    uv = next(step for step in job["steps"] if "setup-uv" in step.get("uses", ""))
    just = next(step for step in job["steps"] if "setup-just" in step.get("uses", ""))
    node = next(
        step for step in job["steps"] if step.get("uses") == "actions/setup-node@v4"
    )
    assert uv["with"]["version"] == "0.12.23"
    assert just["with"]["just-version"] == "1.58.0"
    assert node["with"]["node-version"] == "24"
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "uv sync --locked --all-groups --all-extras" in commands
    assert "poetry" not in commands.lower()
    assert "conda" not in commands.lower()
    assert "makim" not in commands.lower()
    if name == "ci":
        assert job["strategy"]["matrix"]["python-version"] == ["3.10", "3.12", "3.14"]
        assert uv["with"]["python-version"] == "${{ matrix.python-version }}"
        assert "just --fmt --check" in commands
        assert "just ci" in commands
        for local_only in ("plan-check", "plan-refresh", "check_lesson_plan.py"):
            assert local_only not in commands
    else:
        assert uv["with"]["python-version"] == "3.12"
        assert "just docs" in commands


def test_precommit_runs_python_tools_through_uv() -> None:
    hooks = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert hooks["fail_fast"] is True
    all_hooks = [hook for repo in hooks["repos"] for hook in repo["hooks"]]
    assert all(hook["language"] == "system" for hook in all_hooks)
    environment = next(hook for hook in all_hooks if hook["id"] == "uv-environment")
    assert environment["entry"] == "uv run --locked python scripts/check_environment.py"
    formatter = next(hook for hook in all_hooks if hook["id"] == "prettier")
    assert formatter["additional_dependencies"] == []
    assert formatter["entry"] == (
        "npm exec --yes --package=prettier@3.0.2 -- prettier "
        "--write --list-different --ignore-unknown"
    )
    for hook in all_hooks:
        if hook["id"] in {"ruff-format", "ruff-check", "mypy"}:
            assert hook["entry"].startswith("uv run --locked ")


def test_full_pipeline_checks_and_builds_with_uv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location("project_tasks", "scripts/project.py")
    assert spec and spec.loader
    project = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(project)
    calls = []
    monkeypatch.setattr(project, "run", lambda *args: calls.append(args))
    monkeypatch.setattr(project, "lint", lambda: calls.append(("lint",)))
    monkeypatch.setattr(project, "docs", lambda: calls.append(("docs",)))
    monkeypatch.setattr(sys, "argv", ["project.py", "all"])
    project.main()
    assert calls == [
        (sys.executable, "scripts/check_environment.py"),
        ("lint",),
        (sys.executable, "-m", "pytest", "-q"),
        ("uv", "lock", "--check"),
        ("uv", "build"),
        ("docs",),
    ]


def test_repository_no_longer_requires_poetry_conda_or_makim() -> None:
    paths = [
        Path("README.md"),
        Path("AGENTS.md"),
        Path("Justfile"),
        Path("pyproject.toml"),
        Path(".pre-commit-config.yaml"),
        Path(".github/PULL_REQUEST_TEMPLATE.md"),
        *Path(".github/workflows").glob("*.yml"),
        *Path("scripts").glob("*.py"),
        *Path("docs/courses").rglob("*.qmd"),
        Path("docs/courses/_catalog.yml"),
        Path("docs/resources/agent-lab.qmd"),
        Path("docs/resources/contributing.qmd"),
    ]
    for path in paths:
        assert not re.search(
            r"\b(poetry|conda|makim)\b",
            path.read_text(encoding="utf-8"),
            re.IGNORECASE,
        ), path
    assert not Path("conda.yaml").exists()
    assert not Path(".makim.yaml").exists()


def test_public_guidance_does_not_link_to_ignored_local_plans() -> None:
    for path in [Path("README.md"), *Path("docs").rglob("*.qmd")]:
        assert not re.search(
            r"\]\([^)]*\bPLAN[^/)]*\.md(?:#[^)]*)?\)",
            path.read_text(encoding="utf-8"),
        ), path
