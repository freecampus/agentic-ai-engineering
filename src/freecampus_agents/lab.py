"""A bounded, offline agent-shaped loop for the infrastructure smoke lab.

The model is a deterministic test double, not a language model. This module is
deliberately small; the full runtime is a planned Unit 3 learning artifact.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from importlib.resources import files
from typing import Literal, Protocol


@dataclass(frozen=True)
class Task:
    """Add two integers; the runtime enforces the allowed tool and step limit."""

    left: int
    right: int

    def __post_init__(self) -> None:
        if type(self.left) is not int or type(self.right) is not int:
            raise ValueError("task operands must be integers, not booleans")


@dataclass(frozen=True)
class Decision:
    """An observable action, not a private reasoning transcript."""

    kind: Literal["tool", "final"]
    tool: str = ""
    answer: int | None = None


@dataclass(frozen=True)
class Event:
    """One inspectable boundary event."""

    kind: str
    detail: str


@dataclass(frozen=True)
class Run:
    """Terminal result and immutable event history."""

    status: Literal["complete", "denied", "invalid", "budget_exhausted"]
    answer: int | None
    events: tuple[Event, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["events"] = [asdict(event) for event in self.events]
        return result


class Model(Protocol):
    """A small replaceable decision port."""

    def decide(self, task: Task, observation: int | None) -> Decision: ...


class FakeModel:
    """Choose addition, then return the observed result without inference."""

    def decide(self, task: Task, observation: int | None) -> Decision:
        if observation is None:
            return Decision("tool", tool="add")
        return Decision("final", answer=observation)


def add(task: Task) -> dict[str, int]:
    """Return the explicit result envelope taught in Unit 0."""
    return {"result": task.left + task.right}


def run_agent(
    task: Task,
    *,
    model: Model | None = None,
    max_steps: int = 2,
    add_tool: Callable[[Task], object] = add,
) -> Run:
    """Run at most ``max_steps`` decisions with only a pure addition tool.

    This is not a sandbox for arbitrary Python models: callers supply trusted,
    in-process test doubles and tool implementations. No shell, network,
    credential, or filesystem tool is exposed by the defaults. Injected Python
    can do anything the process can do. Unexpected model/tool exceptions
    propagate to the caller; the decision limit is not a wall-clock timeout.
    """
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    selected_model = model if model is not None else FakeModel()
    events = [Event("task", f"Add {task.left} and {task.right}")]
    observation: int | None = None
    for _ in range(max_steps):
        decision = selected_model.decide(task, observation)
        if not isinstance(decision, Decision):
            events.append(Event("invalid", "Expected a Decision record"))
            return Run("invalid", None, tuple(events))
        if decision.kind == "tool":
            if decision.tool != "add":
                events.append(Event("denied", "Requested tool is not allowed"))
                return Run("denied", None, tuple(events))
            events.append(Event("tool_call", "add"))
            result = add_tool(task)
            if (
                not isinstance(result, dict)
                or set(result) != {"result"}
                or type(result["result"]) is not int
            ):
                events.append(Event("invalid", "Expected {'result': integer}"))
                return Run("invalid", None, tuple(events))
            observation = result["result"]
            events.append(Event("observation", str(observation)))
        elif (
            decision.kind == "final"
            and observation is not None
            and type(decision.answer) is int
            and decision.answer == observation
        ):
            events.append(Event("final", str(decision.answer)))
            return Run("complete", decision.answer, tuple(events))
        else:
            events.append(Event("invalid", "Final answer must match a tool result"))
            return Run("invalid", None, tuple(events))
    events.append(Event("budget_exhausted", "Decision limit reached"))
    return Run("budget_exhausted", None, tuple(events))


def smoke_test() -> Run:
    """Verify the packaged fixture and return a known offline run."""
    fixture = json.loads(
        files("freecampus_agents")
        .joinpath("fixtures/addition.json")
        .read_text(encoding="utf-8")
    )
    run = run_agent(Task(**fixture["task"]))
    if run.to_dict() != fixture["expected"]:
        raise RuntimeError("Smoke run differs from its recorded fixture")
    return run


if __name__ == "__main__":
    print(json.dumps(smoke_test().to_dict(), indent=2))
