"""Offline Unit 1 architecture comparisons; no LLM, network, or isolation claims."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from importlib.resources import files
from typing import TypeVar

T = TypeVar("T")
PUBLIC_TOPICS = frozenset({"shipping", "returns"})
ESCALATION = "Ask a human; no account change was made."


@dataclass(frozen=True)
class Request:
    topic: str
    note: str = ""


@dataclass(frozen=True)
class Reply:
    status: str
    text: str
    source: str | None = None


@dataclass(frozen=True)
class DeskEvent:
    kind: str
    actor: str
    detail: str


def escalate() -> Reply:
    return Reply("escalate", ESCALATION)


def public_policies() -> dict[str, Reply]:
    return {
        "shipping": Reply("answer", "Dispatch within 2 working days.", "shipping-v2"),
        "returns": Reply("answer", "Return unused items within 30 days.", "returns-v1"),
    }


class Desk:
    """Trusted fake runtime with counted decisions and allowlisted public reads.

    Learner Python is trusted, not sandboxed. The note is never executable input.
    A failed permitted read still consumes its allowance. A denied read does not.
    """

    def __init__(
        self,
        *,
        policies: Mapping[str, Reply] | None = None,
        unavailable: frozenset[str] = frozenset(),
        decision_limit: int = 12,
        read_limit: int = 5,
    ) -> None:
        for value in (decision_limit, read_limit):
            if type(value) is not int or value < 0:
                raise ValueError("Limits must be nonnegative integers")
        self._policies = dict(public_policies() if policies is None else policies)
        self.unavailable = unavailable
        self.decision_limit = decision_limit
        self.read_limit = read_limit
        self.events: list[DeskEvent] = []

    def count(self, kind: str) -> int:
        return sum(event.kind == kind for event in self.events)

    def model(self, actor: str, fake: Callable[[], T]) -> T:
        if self.count("decision") >= self.decision_limit:
            self.events.append(DeskEvent("stop", actor, "decision_limit"))
            raise RuntimeError("decision_limit")
        self.events.append(DeskEvent("decision", actor, "scripted model invocation"))
        return fake()

    def read(self, topic: str) -> Reply:
        if topic not in PUBLIC_TOPICS:
            self.events.append(DeskEvent("deny", "runtime", topic))
            raise PermissionError("Only public shipping/returns reads are allowed")
        if self.count("read") >= self.read_limit:
            self.events.append(DeskEvent("stop", "runtime", "read_limit"))
            raise RuntimeError("read_limit")
        self.events.append(DeskEvent("read", "runtime", topic))
        if topic in self.unavailable or topic not in self._policies:
            self.events.append(DeskEvent("observation", "tool", "unavailable"))
            return escalate()
        reply = self._policies[topic]
        self.events.append(DeskEvent("observation", "tool", reply.source or "missing"))
        return reply


def rule(request: Request, desk: Desk) -> Reply:
    """A deliberately inadequate cached rule, not the best possible rules system."""
    if request.topic == "shipping":
        return Reply("answer", "Dispatch tomorrow.", "shipping-v1")
    return escalate()


def retrieval(request: Request, desk: Desk) -> Reply:
    """An exact-key query with an explicit failure path; no model needed."""
    if request.topic not in PUBLIC_TOPICS:
        return escalate()
    return desk.read(request.topic)


def workflow(request: Request, desk: Desk) -> Reply:
    topic = desk.model("classify", lambda: request.topic)
    reply = retrieval(Request(topic), desk)
    return desk.model("format", lambda: reply)


@dataclass(frozen=True)
class Proposal:
    kind: str
    target: str = ""


def choose(request: Request, observation: Reply | None) -> Proposal:
    """A deterministic policy standing in for a model's action-selection port."""
    if observation is not None:
        return Proposal("finish")
    if request.topic in PUBLIC_TOPICS:
        return Proposal("read", request.topic)
    return Proposal("escalate")


def single_agent(request: Request, desk: Desk, actor: str = "assistant") -> Reply:
    observation = None
    # The policy chooses read/finish/escalate; the host owns the hard limit.
    for _ in range(3):
        proposal = desk.model(actor, partial(choose, request, observation))
        if proposal.kind == "finish" and observation is not None:
            return observation
        if proposal.kind == "escalate":
            return escalate()
        if proposal.kind == "read":
            observation = desk.read(proposal.target)
        else:
            raise ValueError("Unsupported proposal")
    raise RuntimeError("local_turn_limit")


def five_agents(request: Request, desk: Desk) -> Reply:
    """Five separate observation loops, identical fake policies, shared limits.

    Roles are cosmetic. Separate local histories do not create independent errors.
    This intentionally redundant baseline is NOT representative of every MAS.
    """
    replies = [
        single_agent(request, desk, actor)
        for actor in ("intake", "policy", "research", "review", "response")
    ]
    return replies[0] if all(reply == replies[0] for reply in replies) else escalate()


Architecture = Callable[[Request, Desk], Reply]
VARIANTS: dict[str, Architecture] = {
    "rule": rule,
    "retrieval": retrieval,
    "workflow": workflow,
    "single-agent": single_agent,
    "five-agents": five_agents,
}


@dataclass(frozen=True)
class Case:
    id: str
    group: str
    request: Request
    unavailable: frozenset[str]
    policies: Mapping[str, Reply]
    expected: Reply


def cases(split: str = "development") -> tuple[Case, ...]:
    """Public fixtures, not secret tests. Freeze choices before qualification."""
    if split not in {"development", "qualification"}:
        raise ValueError("Unknown split")
    records = json.loads(
        files("freecampus_agents")
        .joinpath("fixtures/unit1_requests.json")
        .read_text(encoding="utf-8")
    )
    result = []
    for record in records[split]:
        policies = public_policies()
        for key, value in record.get("overrides", {}).items():
            policies[key] = Reply(**value)
        result.append(
            Case(
                record["id"],
                record["group"],
                Request(**record["request"]),
                frozenset(record.get("unavailable", [])),
                policies,
                Reply(**record["expected"]),
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class Result:
    case_id: str
    quality_pass: bool
    safety_pass: bool
    decisions: int
    reads: int
    reply: Reply | None
    error: str | None
    events: tuple[DeskEvent, ...]

    def cost(self, decision_price: float = 5, read_price: float = 1) -> float:
        """Synthetic work units; not a provider invoice or latency measurement."""
        if decision_price < 0 or read_price < 0:
            raise ValueError("Prices cannot be negative")
        return self.decisions * decision_price + self.reads * read_price


def evaluate(
    architecture: Architecture, fixtures: tuple[Case, ...]
) -> tuple[Result, ...]:
    results = []
    for case in fixtures:
        desk = Desk(policies=case.policies, unavailable=case.unavailable)
        reply = None
        error = None
        try:
            reply = architecture(case.request, desk)
        except (PermissionError, RuntimeError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        # A narrow observed-event safety check, NOT proof about arbitrary Python.
        safety = not any(event.kind in {"deny", "stop"} for event in desk.events)
        results.append(
            Result(
                case.id,
                reply == case.expected and error is None,
                safety and error is None,
                desk.count("decision"),
                desk.count("read"),
                reply,
                error,
                tuple(desk.events),
            )
        )
    return tuple(results)


def eligible(results: tuple[Result, ...]) -> bool:
    """All finite quality AND observed safety gates must pass; empty is no-go."""
    return bool(results) and all(r.quality_pass and r.safety_pass for r in results)
