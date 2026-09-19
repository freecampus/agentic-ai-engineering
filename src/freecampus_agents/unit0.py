"""Small, offline fixtures for the launch unit; not a general agent framework."""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from freecampus_agents import __version__
from freecampus_agents.lab import Task


@dataclass(frozen=True)
class LookupRun:
    """Only completed reads count toward the lookup budget."""

    status: Literal["found", "missing", "denied", "budget_exhausted"]
    document_id: str | None
    text: str | None
    looked_up: tuple[str, ...]


def lookup_documents(
    requests: Sequence[str],
    documents: Mapping[str, str],
    *,
    allowed: frozenset[str],
    max_lookups: int,
) -> LookupRun:
    """Read approved synthetic documents, stopping at the first nonempty result.

    Requests are a trusted, finite script, not an LLM. Authorization is checked
    before budget, and both precede access. Mapping implementations are trusted
    Python, not a security boundary. No network or filesystem is involved.
    """
    if type(max_lookups) is not int or max_lookups < 0:
        raise ValueError("max_lookups must be a nonnegative integer")
    looked_up: list[str] = []
    for document_id in requests:
        if document_id not in allowed:
            return LookupRun("denied", None, None, tuple(looked_up))
        if len(looked_up) >= max_lookups:
            return LookupRun("budget_exhausted", None, None, tuple(looked_up))
        text = documents.get(document_id)
        looked_up.append(document_id)
        if text:
            return LookupRun("found", document_id, text, tuple(looked_up))
    return LookupRun("missing", None, None, tuple(looked_up))


def load_task(path: Path) -> Task:
    """Load exactly two integer operands; never silently synthesize missing input."""
    if not path.is_file():
        raise FileNotFoundError(f"Task input is missing: {path.name}; supply its path.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Task input must be a JSON object with left and right"
        ) from exc
    if not isinstance(data, dict) or set(data) != {"left", "right"}:
        raise ValueError("Task input must contain exactly left and right")
    return Task(data["left"], data["right"])


def execution_identity(task: Task) -> dict[str, str]:
    """A shareable identity report without usernames, paths, or environment values.

    This records normalized inputs, not a dependency lock or proof of execution.
    A launch card must also preserve commands, outputs, and limitations.
    """
    normalized = json.dumps(
        {"left": task.left, "right": task.right}, sort_keys=True, separators=(",", ":")
    )
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "course_package": __version__,
        "task_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }
