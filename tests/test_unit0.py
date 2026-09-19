from __future__ import annotations

import json
import re
from pathlib import Path

import nbformat
import pytest

from freecampus_agents.lab import Decision, Task, run_agent, smoke_test
from freecampus_agents.launch_project import check_launch_project, create_launch_project
from freecampus_agents.unit0 import execution_identity, load_task, lookup_documents
from freecampus_agents.unit0_quizzes import unit0_quizzes

UNIT = Path("docs/courses/agentic-ai-engineering/units/launch-agent-lab")
SLUGS = (
    "meet-a-tiny-agent",
    "learn-with-evidence",
    "use-ai-responsibly",
    "work-in-notebooks",
    "build-local-workspace",
    "challenge",
)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        12,
        {},
        {"total": 12},
        {"result": "12"},
        {"result": True},
        {"result": 12, "extra": 1},
    ],
)
def test_malformed_tool_result_stops_at_the_boundary(payload: object) -> None:
    result = run_agent(Task(7, 5), add_tool=lambda task: payload)
    assert result.status == "invalid"
    assert result.answer is None
    assert [event.kind for event in result.events] == ["task", "tool_call", "invalid"]
    assert result.events[-1].detail == "Expected {'result': integer}"


def test_tool_schema_is_not_a_correctness_proof() -> None:
    result = run_agent(Task(7, 5), add_tool=lambda task: {"result": 999})
    assert result.status == "complete"
    assert result.answer == 999  # Schema validity does not establish arithmetic.
    assert result.answer != 12
    assert smoke_test().answer == 12


def test_unauthorized_name_never_calls_the_injected_tool() -> None:
    calls = []

    def watched(task: Task) -> dict[str, int]:
        calls.append(task)
        return {"result": 12}

    class Forbidden:
        def decide(self, task: Task, observation: int | None) -> Decision:
            return Decision("tool", tool="shell")

    result = run_agent(Task(7, 5), model=Forbidden(), add_tool=watched)
    assert result.status == "denied"
    assert calls == []


def test_unexpected_tool_exceptions_are_not_hidden() -> None:
    def broken(task: Task) -> object:
        raise RuntimeError("fixture tool fault")

    with pytest.raises(RuntimeError, match="fixture tool fault"):
        run_agent(Task(7, 5), add_tool=broken)


@pytest.mark.parametrize(
    "requests,limit,status,reads,text",
    [
        (["hours"], 1, "found", ("hours",), "Saturday 10:00\u201314:00"),
        (
            ["holiday", "hours"],
            2,
            "found",
            ("holiday", "hours"),
            "Saturday 10:00\u201314:00",
        ),
        (["holiday"], 2, "missing", ("holiday",), None),
        ([], 2, "missing", (), None),
        (["absent"], 1, "missing", ("absent",), None),
        (["private"], 2, "denied", (), None),
        (["private"], 0, "denied", (), None),
        (["holiday", "private"], 1, "denied", ("holiday",), None),
        (["holiday", "hours"], 1, "budget_exhausted", ("holiday",), None),
        (["hours"], 0, "budget_exhausted", (), None),
        (["hours", "private"], 2, "found", ("hours",), "Saturday 10:00\u201314:00"),
    ],
)
def test_lookup_contract_and_independent_effects(requests, limit, status, reads, text):
    class ReadSpy(dict):
        def __init__(self):
            super().__init__(
                hours="Saturday 10:00\u201314:00", holiday="", private="DUMMY"
            )
            self.reads = []

        def get(self, key, default=None):
            self.reads.append(key)
            return super().get(key, default)

    spy = ReadSpy()
    run = lookup_documents(
        requests,
        spy,
        allowed=frozenset({"hours", "holiday", "absent"}),
        max_lookups=limit,
    )
    assert run.status == status
    assert run.looked_up == reads == tuple(spy.reads)
    assert run.text == text
    assert run.document_id == ("hours" if status == "found" else None)


@pytest.mark.parametrize("limit", [-1, True, 1.5])
def test_lookup_rejects_invalid_budgets(limit):
    with pytest.raises(ValueError, match="nonnegative integer"):
        lookup_documents([], {}, allowed=frozenset(), max_lookups=limit)


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        '{"left": 1}',
        '{"left": 1, "right": 2, "other": 3}',
        '{"left": true, "right": 2}',
        '{"left": 1.1, "right": 2}',
        '{"left": "7", "right": 5}',
    ],
)
def test_loader_rejects_malformed_inputs(tmp_path, payload):
    path = tmp_path / "task.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        load_task(path)


def test_explicit_path_and_missing_input_do_not_depend_on_cwd(tmp_path, monkeypatch):
    path = tmp_path / "input with spaces.json"
    path.write_text('{"left": -5, "right": 5}', encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    assert run_agent(load_task(path)).answer == 0
    with pytest.raises(FileNotFoundError, match="supply its path"):
        load_task(Path("input with spaces.json"))
    assert not (other / path.name).exists()


def test_identity_covers_normalized_input_without_private_environment(monkeypatch):
    monkeypatch.setenv("DUMMY_TOKEN", "DO_NOT_PUBLISH")
    first = execution_identity(Task(7, 5))
    assert first == execution_identity(Task(7, 5))
    assert first["task_sha256"] != execution_identity(Task(-5, 5))["task_sha256"]
    assert set(first) == {
        "python",
        "implementation",
        "platform",
        "course_package",
        "task_sha256",
    }
    assert "DO_NOT_PUBLISH" not in json.dumps(first)


@pytest.mark.parametrize("slug", SLUGS)
def test_unit0_checkpoint_banks_match_canonical_sources(slug):
    text = (UNIT / f"{slug}.qmd").read_text(encoding="utf-8")
    payloads = [
        json.loads(raw)
        for raw in re.findall(
            r'class="fcagentic-ojs-quiz-config">(.*?)</script>', text, re.S
        )
    ]
    assert [quiz.to_dict() for quiz in unit0_quizzes(slug)] == payloads
    assert len(payloads) == 3
    assert all(len(quiz["questions"]) == 2 for quiz in payloads)
    assert "@@QUIZ" not in text
    assert "notebook_package: true" in text
    assert (
        "Primary references checked 2026-09-19" in text
        or "references\nchecked 2026-09-19" in text
    )


def test_challenge_structure_and_completion_remain_gated():
    text = (UNIT / "challenge.qmd").read_text(encoding="utf-8")
    for heading in [
        "## 3. Start from the contract",
        "## 5. Run progressive assertions",
        "## 6. Use the hint ladder only when needed",
        "## 7. Keep debugging evidence",
    ]:
        assert heading in text
    assert re.findall(r"<summary>Hint (\d):", text) == ["1", "2", "3"]
    assert "<!-- fcagentic-unit-challenge: practical -->" in text
    assert "data-fc-challenge-complete" in text
    assert 'aria-pressed="false" hidden' in text
    assert "lesson_id:" not in text


def test_starter_does_not_overwrite_existing_work_and_exposes_stale_state(tmp_path):
    project = create_launch_project(tmp_path / "repair cafe")
    before = (project / "launch.py").read_text()
    with pytest.raises(FileExistsError):
        create_launch_project(project)
    assert (project / "launch.py").read_text() == before
    notebook = nbformat.read(project / "stale.ipynb", as_version=4)
    nbformat.validate(notebook)
    scope = {}
    for cell in notebook.cells:
        exec(compile(cell.source, "synthetic-stale-fixture", "exec"), scope)
    assert scope["cached_answer"] == 12
    assert scope["left"] + scope["right"] == 0


def test_project_original_fails_and_qmd_solution_passes_fresh_processes(tmp_path):
    project = create_launch_project(tmp_path / "repair cafe")
    with pytest.raises(
        AssertionError,
        match="Launch failed",
    ):
        check_launch_project(project)
    text = (UNIT / "challenge.qmd").read_text(encoding="utf-8")
    solution = re.search(r"```python\n(# File: launch.py.*?)```", text, re.S)
    assert solution
    (project / "launch.py").write_text(solution[1], encoding="utf-8")
    checks = check_launch_project(project)
    assert len(checks) == 7
    assert "0; fresh process passed" in checks[1]
    # Correct result for the ordinary fixture must not conceal cached-answer bugs.
    wrong = solution[1].replace("run_agent(task)", "run_agent(type(task)(7, 5))")
    (project / "launch.py").write_text(wrong, encoding="utf-8")
    with pytest.raises(AssertionError, match="explicit input"):
        check_launch_project(project)
    # A right-looking sum must not conceal a weakened schema at the CLI boundary.
    coercing = solution[1].replace(
        "task = load_task(Path(arguments[0]))",
        "data = json.loads(Path(arguments[0]).read_text())\n"
        "        from freecampus_agents.lab import Task\n"
        "        task = Task(int(data['left']), int(data['right']))",
    )
    (project / "launch.py").write_text(coercing, encoding="utf-8")
    with pytest.raises(AssertionError, match="boolean operand"):
        check_launch_project(project)
