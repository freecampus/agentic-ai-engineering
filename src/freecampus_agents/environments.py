"""Small deterministic worlds separating full audit state from observation."""

from __future__ import annotations

from dataclasses import dataclass, replace

MOVES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


@dataclass(frozen=True)
class GridState:
    position: tuple[int, int] = (0, 0)
    attempts: int = 0
    status: str = "running"


@dataclass(frozen=True)
class GridObservation:
    position: tuple[int, int]
    outcome: str
    status: str


@dataclass(frozen=True)
class GridTransition:
    before: GridState
    action: str
    after: GridState
    observation: GridObservation | None
    cost: int = 1


@dataclass(frozen=True)
class Grid:
    width: int = 3
    height: int = 2
    blocked: frozenset[tuple[int, int]] = frozenset({(1, 0)})
    goal: tuple[int, int] = (2, 0)
    limit: int = 6

    def step(
        self, state: GridState, action: str, *, missing: bool = False
    ) -> GridTransition:
        if state.status != "running":
            raise RuntimeError("Terminal state: no further action")
        if state.position == self.goal or state.attempts >= self.limit:
            raise ValueError("Inconsistent running state")
        if action not in MOVES:
            raise ValueError("Unknown move")
        dx, dy = MOVES[action]
        target = (state.position[0] + dx, state.position[1] + dy)
        legal = (
            0 <= target[0] < self.width
            and 0 <= target[1] < self.height
            and target not in self.blocked
        )
        position = target if legal else state.position
        attempts = state.attempts + 1
        status = "success" if position == self.goal else "running"
        if status == "running" and attempts >= self.limit:
            status = "exhausted"
        after = GridState(position, attempts, status)
        observation = (
            None
            if missing
            else GridObservation(position, "moved" if legal else "blocked", status)
        )
        return GridTransition(state, action, after, observation)


def update_position(
    previous: tuple[int, int] | None, observation: GridObservation | None
) -> tuple[int, int] | None:
    """Missing evidence yields unknown, NOT a claim that the world did not move."""
    return None if observation is None else observation.position


@dataclass(frozen=True)
class ToolState:
    reads: int = 0
    status: str = "running"
    evidence: str | None = None


@dataclass(frozen=True)
class ToolTransition:
    before: ToolState
    action: str
    after: ToolState
    observation: str | None
    cost: int


def tool_step(
    state: ToolState, action: str, *, missing: bool = False
) -> ToolTransition:
    """Read-only two-action world. 'finish' without evidence is failure, not success."""
    if state.status != "running":
        raise RuntimeError("Terminal state: no further action")
    if action == "read:hours":
        if state.reads >= 1:
            raise RuntimeError("Read budget exhausted")
        observation = None if missing else "Open Saturday 10:00\u201314:00."
        after = replace(state, reads=state.reads + 1, evidence=observation)
        return ToolTransition(state, action, after, observation, 1)
    if action == "finish":
        status = "success" if state.evidence is not None else "insufficient_evidence"
        after = replace(state, status=status)
        return ToolTransition(state, action, after, state.evidence, 0)
    raise PermissionError("Only read:hours and finish are supported")
