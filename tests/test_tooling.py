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


def test_poetry_metadata_preserves_package_extras_and_build_assets() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "freecampus-agents"
    assert config["project"]["requires-python"] == ">=3.10"
    assert config["project"]["dependencies"] == []
    assert "notebooks" in config["project"]["optional-dependencies"]
    assert set(config["dependency-groups"]) == {"dev", "docs"}
    assert config["build-system"]["build-backend"] == "poetry.core.masonry.api"
    assert config["build-system"]["requires"] == ["poetry-core>=2.4,<3"]
    poetry = config["tool"]["poetry"]
    assert poetry["requires-poetry"] == ">=2.4,<3"
    assert poetry["packages"] == [{"include": "freecampus_agents", "from": "src"}]
    assert poetry["group"]["docs"]["optional"] is True
    for path in (
        "src/freecampus_agents/py.typed",
        "src/freecampus_agents/fixtures/*.json",
    ):
        entry = next(item for item in poetry["include"] if item["path"] == path)
        assert set(entry["format"]) == {"sdist", "wheel"}
    assert "setuptools" not in config["tool"]
    assert "pre-commit-hooks==4.6.0" in config["dependency-groups"]["dev"]
    assert not Path("uv.lock").exists()


def test_conda_bootstraps_poetry_without_becoming_a_second_dependency_manager() -> None:
    config = yaml.safe_load(Path("conda.yaml").read_text(encoding="utf-8"))
    assert config["name"] == "fc-agentic"
    assert config["channels"] == ["conda-forge", "nodefaults"]
    assert set(config["dependencies"]) == {
        "python=3.12",
        "poetry>=2.4,<3",
        "nodejs",
        "pip",
    }
    assert config["variables"] == {
        "POETRY_VIRTUALENVS_CREATE": "false",
        "POETRY_VIRTUALENVS_IN_PROJECT": "false",
    }
    poetry_config = tomllib.loads(Path("poetry.toml").read_text(encoding="utf-8"))
    assert poetry_config["virtualenvs"] == {"create": False, "in-project": False}


@pytest.mark.parametrize("name", ["ci", "docs"])
def test_workflows_activate_conda_and_install_poetry_dependencies_without_venvs(
    name: str,
) -> None:
    workflow = yaml.safe_load(
        Path(f".github/workflows/{name}.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["checks" if name == "ci" else "build"]
    assert job["defaults"]["run"]["shell"] == "bash -el {0}"
    assert job["env"]["POETRY_VIRTUALENVS_CREATE"] == "false"
    assert job["env"]["POETRY_VIRTUALENVS_IN_PROJECT"] == "false"
    assert "VIRTUAL_ENV" not in job["env"]
    setup = next(
        step
        for step in job["steps"]
        if step.get("uses") == "conda-incubator/setup-miniconda@v3"
    )
    assert setup["with"]["environment-file"] == "conda.yaml"
    assert setup["with"]["activate-environment"] == "fc-agentic"
    assert setup["with"]["auto-activate-base"] is False
    assert setup["with"]["miniforge-version"] == "latest"
    assert setup["with"]["python-version"] == (
        "${{ matrix.python-version }}" if name == "ci" else "3.12"
    )
    if name == "ci":
        assert job["strategy"]["matrix"]["python-version"] == ["3.10", "3.12", "3.14"]
    assert not any(
        step.get("uses", "").startswith(("actions/setup-python", "actions/setup-node"))
        for step in job["steps"]
    )
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    guard = "python scripts/check_environment.py"
    assert commands.count(guard) == 2
    assert commands.index(guard) < commands.index("poetry install")
    assert commands.rindex(guard) > commands.index("poetry install")
    assert "pip install" not in commands
    assert "poetry env use" not in commands
    assert "poetry check --strict" in commands
    assert "--with docs" in commands
    assert "poetry run makim" in commands
    assert "poetry sync" not in commands
    for local_only in ("plan.check", "plan.refresh", "check_lesson_plan.py"):
        assert local_only not in commands


def test_task_runner_and_hooks_use_the_existing_conda_environment() -> None:
    tasks = yaml.safe_load(Path(".makim.yaml").read_text(encoding="utf-8"))
    assert tasks["groups"]["package"]["tasks"]["build"]["run"] == (
        "python scripts/project.py package"
    )
    assert tasks["groups"]["environment"]["tasks"]["check"]["run"] == (
        "python scripts/check_environment.py"
    )
    hooks = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert hooks["fail_fast"] is True
    guard = hooks["repos"][0]["hooks"][0]
    assert guard["entry"] == "python scripts/check_environment.py"
    assert guard["always_run"] is True
    assert guard["pass_filenames"] is False
    all_hooks = [hook for repo in hooks["repos"] for hook in repo["hooks"]]
    assert all(hook["language"] == "system" for hook in all_hooks)
    formatter = next(hook for hook in all_hooks if hook["id"] == "prettier")
    assert formatter["additional_dependencies"] == []
    assert formatter["entry"] == (
        "npm exec --yes --package=prettier@3.0.2 -- prettier "
        "--write --list-different --ignore-unknown"
    )
    for hook in all_hooks:
        if hook["id"] in {"ruff-format", "ruff-check", "mypy"}:
            assert hook["entry"].startswith("poetry run ")


def test_full_pipeline_checks_and_builds_with_poetry(
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
        ("poetry", "check", "--strict"),
        ("poetry", "build"),
        ("docs",),
    ]


def test_operational_files_do_not_instruct_using_the_retired_manager() -> None:
    paths = [
        Path("README.md"),
        Path("AGENTS.md"),
        Path("conda.yaml"),
        Path(".makim.yaml"),
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
            r"\buv\b|UV_PYTHON|astral-sh/setup-uv",
            path.read_text(encoding="utf-8"),
        ), path


def test_public_guidance_does_not_link_to_ignored_local_plans() -> None:
    for path in [Path("README.md"), *Path("docs").rglob("*.qmd")]:
        assert not re.search(
            r"\]\([^)]*\bPLAN[^/)]*\.md(?:#[^)]*)?\)",
            path.read_text(encoding="utf-8"),
        ), path
