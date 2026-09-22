"""Unit 1 teaching policy gate: trusted in-process code, not a security sandbox."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

CAPABILITIES = frozenset({"read_public", "send_draft"})
SUCCESS_CAPABILITY = {
    "answer_with_source": "read_public",
    "deliver_draft": "send_draft",
}


def _integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer, not bool")
    return value


def _names(value: object, name: str) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{name} must be a list of strings")
    if len(value) != len(set(value)) or not set(value) <= CAPABILITIES:
        raise ValueError(f"{name}: duplicate or unknown capability")
    return frozenset(value)


@dataclass(frozen=True)
class Contract:
    task_id: str
    success: str
    allowed: frozenset[str]
    forbidden: frozenset[str]
    approval_required: frozenset[str]
    max_actions: int
    deadline: int
    escalation: str


def validate_contract(raw: Mapping[str, object]) -> Contract:
    """Validate THIS record and its cross-field rules, not arbitrary JSON Schema."""
    required = {
        "task_id",
        "success",
        "allowed",
        "forbidden",
        "approval_required",
        "max_actions",
        "deadline",
        "escalation",
    }
    if set(raw) != required:
        raise ValueError("Missing or unknown contract fields")
    for name in ("task_id", "success", "escalation"):
        if not isinstance(raw[name], str) or not str(raw[name]).strip():
            raise ValueError(f"{name} must be a nonempty string")
    success = str(raw["success"])
    if success not in SUCCESS_CAPABILITY:
        raise ValueError("Unknown success predicate")
    allowed = _names(raw["allowed"], "allowed")
    forbidden = _names(raw["forbidden"], "forbidden")
    approval = _names(raw["approval_required"], "approval_required")
    if allowed & forbidden:
        raise ValueError("Contradictory allowed/forbidden capabilities")
    if not approval <= allowed:
        raise ValueError("Approval cannot grant a disallowed capability")
    if SUCCESS_CAPABILITY[success] not in allowed:
        raise ValueError("Success requires a capability the contract does not allow")
    if "send_draft" in allowed and "send_draft" not in approval:
        raise ValueError("Sending requires explicit approval")
    return Contract(
        str(raw["task_id"]),
        success,
        allowed,
        forbidden,
        approval,
        _integer(raw["max_actions"], "max_actions"),
        _integer(raw["deadline"], "deadline"),
        str(raw["escalation"]),
    )


@dataclass(frozen=True)
class Action:
    capability: str
    resource: str
    rationale: str = ""


@dataclass(frozen=True)
class Approval:
    task_id: str
    capability: str
    resource: str
    expires_at: int


@dataclass(frozen=True)
class Decision:
    status: Literal["allow", "deny", "confirm", "stop"]
    reason: str


def authorize(
    contract: Contract,
    action: Action,
    *,
    used: int,
    now: int,
    approval: Approval | None = None,
) -> Decision:
    _integer(used, "used")
    _integer(now, "now")
    if now >= contract.deadline:
        return Decision("stop", "deadline")
    if used >= contract.max_actions:
        return Decision("stop", "action_budget")
    if action.capability not in contract.allowed:
        return Decision("deny", "capability")
    resources = {"read_public": {"shipping", "returns"}, "send_draft": {"draft-1"}}
    if action.resource not in resources[action.capability]:
        return Decision("deny", "resource")
    if action.capability in contract.approval_required:
        if approval is None or (
            approval.task_id != contract.task_id
            or approval.capability != action.capability
            or approval.resource != action.resource
            or approval.expires_at <= now
        ):
            return Decision("confirm", "fresh_matching_approval_required")
    return Decision("allow", "contract")


class ContractRunner:
    """Synchronous toy runtime; trusted approval input and trusted effect callback.

    Stops latch. Budgets count dispatched effects, including failed effects.
    Production identity, concurrent reservations, approval signatures, and OS
    isolation are deliberately NOT implemented in this introductory example.
    """

    def __init__(self, raw: Mapping[str, object]) -> None:
        self.contract = validate_contract(raw)
        self.used = 0
        self.stopped = False
        self.events: list[Decision] = []

    def execute(
        self,
        action: Action,
        effect: Callable[[Action], None],
        *,
        now: int,
        approval: Approval | None = None,
    ) -> Decision:
        decision = (
            Decision("stop", "already_stopped")
            if self.stopped
            else authorize(
                self.contract, action, used=self.used, now=now, approval=approval
            )
        )
        self.events.append(decision)
        if decision.status == "stop":
            self.stopped = True
        if decision.status == "allow":
            self.used += 1
            effect(action)
        return decision


def research_contract() -> dict[str, object]:
    return {
        "task_id": "desk-001",
        "success": "answer_with_source",
        "allowed": ["read_public"],
        "forbidden": ["send_draft"],
        "approval_required": [],
        "max_actions": 2,
        "deadline": 10,
        "escalation": "Return the unresolved question to a human; do not send.",
    }
