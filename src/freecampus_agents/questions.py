"""Reusable quiz question models for FreeCampus Agentic AI Engineering lessons."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from typing import Any


@dataclass(frozen=True)
class MultipleChoiceQuestion:
    """A single multiple-choice question with one correct answer."""

    id: str
    prompt: str
    options: tuple[str, ...]
    answer_index: int
    explanation: str

    def __post_init__(self) -> None:
        """Validate question data as soon as it is created."""
        if not self.id.strip():
            msg = "question id must not be empty"
            raise ValueError(msg)
        if not self.prompt.strip():
            msg = "question prompt must not be empty"
            raise ValueError(msg)
        if len(self.options) < 2:
            msg = "a multiple-choice question needs at least two options"
            raise ValueError(msg)
        if not 0 <= self.answer_index < len(self.options):
            msg = "answer_index must point to one of the options"
            raise ValueError(msg)
        if not self.explanation.strip():
            msg = "question explanation must not be empty"
            raise ValueError(msg)

    @property
    def answer(self) -> str:
        """Return the correct answer text."""
        return self.options[self.answer_index]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for web/notebook renderers."""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "options": list(self.options),
            "answer_index": self.answer_index,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class Quiz:
    """A small quiz that can be rendered in Quarto OJS or ipywidgets."""

    id: str
    title: str
    questions: tuple[MultipleChoiceQuestion, ...]
    instructions: str = "Choose an answer, then check your work."

    def __post_init__(self) -> None:
        """Validate quiz data as soon as it is created."""
        if not self.id.strip():
            msg = "quiz id must not be empty"
            raise ValueError(msg)
        if not self.title.strip():
            msg = "quiz title must not be empty"
            raise ValueError(msg)
        if not self.questions:
            msg = "quiz must include at least one question"
            raise ValueError(msg)
        question_ids = [question.id for question in self.questions]
        if len(set(question_ids)) != len(question_ids):
            msg = "question ids must be unique within a quiz"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for renderers."""
        return {
            "id": self.id,
            "title": self.title,
            "instructions": self.instructions,
            "questions": [question.to_dict() for question in self.questions],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize the quiz as JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_json_script(
        self,
        *,
        css_class: str = "fcagentic-ojs-quiz-config",
        indent: int | None = 2,
    ) -> str:
        """Render quiz JSON inside a script tag for a Quarto OJS include.

        The returned string is intended for Quarto cells that use
        ``#| output: asis``. The script tag does not execute JavaScript; it only
        stores structured data that the OJS quiz component can read.
        """
        # Script contents are raw text: HTML entities would change the JSON.
        # Escaping '<' also prevents an authored '</script>' from closing it.
        payload = (
            self.to_json(indent=indent)
            .replace("<", r"\u003c")
            .replace(">", r"\u003e")
            .replace("&", r"\u0026")
        )
        safe_class = escape(css_class, quote=True)
        return (
            f'<script type="application/json" class="{safe_class}">\n'
            f"{payload}\n"
            "</script>"
        )
