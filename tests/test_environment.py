from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def checker() -> ModuleType:
    return load_script("check_environment")


@pytest.fixture
def project_venv(
    tmp_path: Path,
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path / "project with spaces"
    environment = root / ".venv"
    environment.mkdir(parents=True)
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "python"))
    return environment


def test_accepts_project_uv_environment(
    checker: ModuleType,
    project_venv: Path,
) -> None:
    assert checker.check_environment() == project_venv.resolve()


def test_accepts_configured_uv_project_environment(
    checker: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    environment = root / "custom-env"
    environment.mkdir(parents=True)
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "custom-env")
    monkeypatch.setattr(sys, "prefix", str(environment))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "python"))
    assert checker.check_environment() == environment.resolve()


@pytest.mark.parametrize("fault", ["system_python", "other_environment"])
def test_rejects_python_outside_the_project_environment(
    checker: ModuleType,
    project_venv: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    if fault == "system_python":
        monkeypatch.setattr(sys, "prefix", str(tmp_path / "python"))
        monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "python"))
    else:
        monkeypatch.setattr(sys, "prefix", str(tmp_path / "other-venv"))
    with pytest.raises(checker.EnvironmentCheckError, match="uv-managed environment"):
        checker.check_environment()


def test_missing_environment_has_actionable_failure(
    checker: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path / "project")
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "python"))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "python"))
    assert checker.main() == 1
    error = capsys.readouterr().err
    assert "just setup" in error
    assert "uv run" in error


@pytest.mark.parametrize("task", ["lint", "test", "docs", "preview", "package", "all"])
def test_tasks_stop_before_work_when_environment_check_fails(
    monkeypatch: pytest.MonkeyPatch,
    task: str,
) -> None:
    project = load_script("project")
    calls = []

    def fail(*args: str) -> None:
        calls.append(args)
        raise RuntimeError("environment check failed")

    monkeypatch.setattr(project, "run", fail)
    monkeypatch.setattr(sys, "argv", ["project.py", task])
    with pytest.raises(RuntimeError, match="environment check failed"):
        project.main()
    assert calls == [(sys.executable, "scripts/check_environment.py")]


def test_cleanup_preserves_environments_and_unrelated_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = load_script("project")
    monkeypatch.setattr(project, "ROOT", tmp_path)
    preserved = [
        ".venv/pyvenv.cfg",
        "venv/pyvenv.cfg",
        ".cache/unrelated/file",
    ]
    generated = [
        "docs/_site/index.html",
        ".cache/quarto/temp",
        ".cache/quarto-home/temp",
        "dist/package.whl",
    ]
    for relative in [*preserved, *generated]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("keep or remove as appropriate", encoding="utf-8")
    project.clean()
    assert all((tmp_path / path).is_file() for path in preserved)
    assert not any((tmp_path / path).exists() for path in generated)
