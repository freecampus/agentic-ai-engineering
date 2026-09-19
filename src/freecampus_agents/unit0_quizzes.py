"""Reusable Unit 0 question banks, mirrored by the canonical QMD checkpoints."""

import json
from importlib.resources import files

from freecampus_agents.questions import MultipleChoiceQuestion, Quiz


def unit0_quizzes(slug: str) -> tuple[Quiz, ...]:
    """Return concept, evidence, and failure checkpoints for one activity slug."""
    banks = json.loads(
        files("freecampus_agents")
        .joinpath("fixtures/unit0_quizzes.json")
        .read_text(encoding="utf-8")
    )
    return tuple(
        Quiz(
            id=bank["id"],
            title=bank["title"],
            instructions=bank["instructions"],
            questions=tuple(
                MultipleChoiceQuestion(
                    id=question["id"],
                    prompt=question["prompt"],
                    options=tuple(question["options"]),
                    answer_index=question["answer_index"],
                    explanation=question["explanation"],
                )
                for question in bank["questions"]
            ),
        )
        for bank in banks[slug]
    )
