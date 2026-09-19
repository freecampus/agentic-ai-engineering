from __future__ import annotations

import importlib.util
import json
import subprocess
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
def conda_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Model prefixes with metadata; never create or activate a real venv in tests.
    prefix = tmp_path / "conda with spaces"
    (prefix / "conda-meta").mkdir(parents=True)
    monkeypatch.setenv("CONDA_PREFIX", str(prefix))
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "fc-agentic")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", str(prefix))
    monkeypatch.setattr(sys, "base_prefix", str(prefix))
    return prefix


def test_accepts_real_conda_prefix(
    checker: ModuleType,
    conda_prefix: Path,
) -> None:
    assert checker.check_conda_python() == conda_prefix


def test_accepts_poetry_labeling_the_same_real_conda_prefix(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # poetry run sets this marker without creating or using a separate venv.
    monkeypatch.setenv("VIRTUAL_ENV", str(conda_prefix))
    assert checker.check_conda_python() == conda_prefix


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("inactive", "Activate Conda first"),
        ("base", "not base"),
        ("virtual_env", "venv is active"),
        ("nested_prefix", "venv is active"),
        ("missing_metadata", "does not identify a Conda environment"),
        ("wrong_python", "not running from the activated Conda prefix"),
    ],
)
def test_rejects_incorrect_python_environments(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    message: str,
) -> None:
    if fault == "inactive":
        monkeypatch.delenv("CONDA_PREFIX")
    elif fault == "base":
        monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")
    elif fault == "virtual_env":
        monkeypatch.setenv("VIRTUAL_ENV", str(conda_prefix / "nested"))
    elif fault == "nested_prefix":
        monkeypatch.setattr(sys, "prefix", str(conda_prefix / "nested"))
    elif fault == "missing_metadata":
        (conda_prefix / "conda-meta").rmdir()
    elif fault == "wrong_python":
        for attr in ("prefix", "base_prefix"):
            monkeypatch.setattr(sys, attr, str(conda_prefix / "outside"))
    with pytest.raises(checker.EnvironmentCheckError, match=message):
        checker.check_conda_python()


def configure_poetry(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    override: str = "",
    probe: str | None = None,
) -> list[tuple[str, ...]]:
    executable = str(conda_prefix / "bin" / "poetry")
    monkeypatch.setattr(checker.shutil, "which", lambda name: executable)
    calls: list[tuple[str, ...]] = []

    def output(command: str, *args: str) -> str:
        assert command == executable
        calls.append(args)
        if args[0] == "config":
            return "true" if args[1] == override else "false"
        assert args[:3] == ("run", "python", "-c")
        return (
            probe
            if probe is not None
            else json.dumps(
                {
                    "prefix": str(conda_prefix),
                    "base_prefix": str(conda_prefix),
                    "conda_metadata": True,
                }
            )
        )

    monkeypatch.setattr(checker, "poetry_output", output)
    return calls


def test_checks_effective_settings_and_actual_poetry_interpreter(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = configure_poetry(checker, conda_prefix, monkeypatch)
    assert checker.check_environment() == conda_prefix
    assert calls[:2] == [
        ("config", "virtualenvs.create"),
        ("config", "virtualenvs.in-project"),
    ]
    assert calls[2][:3] == ("run", "python", "-c")


@pytest.mark.parametrize("setting", ["virtualenvs.create", "virtualenvs.in-project"])
def test_rejects_overrides_before_poetry_can_select_or_create_a_venv(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    setting: str,
) -> None:
    calls = configure_poetry(checker, conda_prefix, monkeypatch, override=setting)
    with pytest.raises(checker.EnvironmentCheckError, match="must be false"):
        checker.check_environment()
    assert all(args[0] == "config" for args in calls)


@pytest.mark.parametrize("executable", [None, "/outside/poetry"])
def test_rejects_missing_or_external_poetry(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    executable: str | None,
) -> None:
    calls = configure_poetry(checker, conda_prefix, monkeypatch)
    monkeypatch.setattr(checker.shutil, "which", lambda name: executable)
    with pytest.raises(checker.EnvironmentCheckError, match="Poetry must be installed"):
        checker.check_environment()
    assert calls == []


@pytest.mark.parametrize("field", ["prefix", "base_prefix", "conda_metadata"])
def test_rejects_poetry_selecting_a_cached_or_unrelated_environment(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    details = {
        "prefix": str(conda_prefix),
        "base_prefix": str(conda_prefix),
        "conda_metadata": True,
    }
    details[field] = False if field == "conda_metadata" else "/cached/venv"
    configure_poetry(checker, conda_prefix, monkeypatch, probe=json.dumps(details))
    with pytest.raises(checker.EnvironmentCheckError, match="different or non-Conda"):
        checker.check_environment()


@pytest.mark.parametrize("probe", ["not-json", "[]", "{}"])
def test_rejects_malformed_poetry_probe(
    checker: ModuleType,
    conda_prefix: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    configure_poetry(checker, conda_prefix, monkeypatch, probe=probe)
    with pytest.raises(checker.EnvironmentCheckError):
        checker.check_environment()


def test_poetry_failure_is_reported_without_falling_back_to_another_environment(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "poetry")

    monkeypatch.setattr(checker.subprocess, "run", fail)
    with pytest.raises(checker.EnvironmentCheckError, match="Unable to check Poetry"):
        checker.poetry_output("poetry", "config", "virtualenvs.create")


def test_missing_activation_has_actionable_failure_exit(
    checker: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    assert checker.main() == 1
    assert "conda activate fc-agentic" in capsys.readouterr().err


@pytest.mark.parametrize("task", ["lint", "test", "docs", "preview", "package", "all"])
def test_tasks_stop_before_work_when_environment_check_fails(
    monkeypatch: pytest.MonkeyPatch,
    task: str,
) -> None:
    project = load_script("project")
    calls = []

    def fail(*args: str) -> None:
        calls.append(args)
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(project, "run", fail)
    monkeypatch.setattr(sys, "argv", ["project.py", task])
    with pytest.raises(subprocess.CalledProcessError):
        project.main()
    assert calls == [(sys.executable, "scripts/check_environment.py")]


def test_cleanup_preserves_existing_environments_and_unrelated_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = load_script("project")
    monkeypatch.setattr(project, "ROOT", tmp_path)
    preserved = [
        ".venv/pyvenv.cfg",
        "venv/pyvenv.cfg",
        "conda-env/conda-meta/history",
        ".cache/poetry/virtualenvs/legacy/pyvenv.cfg",
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
