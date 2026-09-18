from __future__ import annotations

import json

import pytest

from freecampus_agents.lab import Decision, FakeModel, Task, run_agent, smoke_test


def test_smoke_run_matches_recorded_fixture() -> None:
    run = smoke_test()
    assert run.status == "complete"
    assert run.answer == 12
    assert [e.kind for e in run.events] == ["task", "tool_call", "observation", "final"]
    assert json.loads(json.dumps(run.to_dict())) == run.to_dict()
    assert smoke_test() == run


@pytest.mark.parametrize(
    "left,right,expected", [(0, 0, 0), (-5, 5, 0), (7, 8, 15), (-7, -5, -12)]
)
def test_addition_contract(left: int, right: int, expected: int) -> None:
    run = run_agent(Task(left, right))
    assert run.status == "complete"
    assert run.answer == expected


def test_budget_counts_decisions_not_events() -> None:
    run = run_agent(Task(7, 5), max_steps=1)
    assert run.status == "budget_exhausted"
    assert run.answer is None
    assert [e.kind for e in run.events] == [
        "task",
        "tool_call",
        "observation",
        "budget_exhausted",
    ]


@pytest.mark.parametrize("budget", [0, -1, True, 1.5])
def test_invalid_budget_is_rejected(budget: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        run_agent(Task(1, 2), max_steps=budget)


@pytest.mark.parametrize("left,right", [(True, 1), (1, False), ("1", 2), (1, 2.5)])
def test_task_rejects_non_integer_inputs(left: int, right: int) -> None:
    with pytest.raises(ValueError, match="integers"):
        Task(left, right)


class ScriptedModel:
    def __init__(self, *decisions: Decision) -> None:
        self.decisions = iter(decisions)

    def decide(self, task: Task, observation: int | None) -> Decision:
        return next(self.decisions)


def test_unavailable_tool_is_denied_before_an_observation() -> None:
    run = run_agent(Task(1, 2), model=ScriptedModel(Decision("tool", tool="shell")))
    assert run.status == "denied"
    assert [e.kind for e in run.events] == ["task", "denied"]


@pytest.mark.parametrize("answer", [None, 999, True])
def test_final_answer_must_match_an_observation(answer: int | None) -> None:
    run = run_agent(
        Task(1, 2),
        model=ScriptedModel(
            Decision("tool", tool="add"), Decision("final", answer=answer)
        ),
    )
    assert run.status == "invalid"
    assert run.answer is None


def test_answer_without_tool_result_is_rejected() -> None:
    run = run_agent(Task(1, 2), model=ScriptedModel(Decision("final", answer=3)))
    assert run.status == "invalid"


def test_repeated_actions_terminate_at_the_limit() -> None:
    run = run_agent(
        Task(1, 2),
        model=ScriptedModel(*[Decision("tool", tool="add")] * 3),
        max_steps=3,
    )
    assert run.status == "budget_exhausted"
    assert sum(e.kind == "tool_call" for e in run.events) == 3


def test_malformed_model_response_is_rejected() -> None:
    class MalformedModel(FakeModel):
        def decide(self, task: Task, observation: int | None) -> Decision:
            return "add"  # type: ignore[return-value]

    assert run_agent(Task(1, 2), model=MalformedModel()).status == "invalid"


def test_unexpected_model_exception_is_not_hidden() -> None:
    class BrokenModel(FakeModel):
        def decide(self, task: Task, observation: int | None) -> Decision:
            raise RuntimeError("model fault")

    with pytest.raises(RuntimeError, match="model fault"):
        run_agent(Task(1, 2), model=BrokenModel())
