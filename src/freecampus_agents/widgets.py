"""ipywidgets renderers for FreeCampus Agentic AI Engineering quizzes."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Any

from freecampus_agents.questions import MultipleChoiceQuestion, Quiz


def _option_labels(question: MultipleChoiceQuestion) -> list[tuple[str, int]]:
    """Return labels paired with answer indexes for an ipywidgets radio group."""
    return [(option, index) for index, option in enumerate(question.options)]


def show_quiz(quiz: Quiz) -> Any:
    """Return an interactive ipywidgets quiz.

    The caller should display the returned widget in Jupyter or Colab. Keeping
    quiz data in :mod:`freecampus_agents.quiz_banks` lets the same questions be
    reused by Quarto/OJS and notebook widgets.
    """
    import ipywidgets as widgets

    title = widgets.HTML(
        f"<h3>{escape(quiz.title)}</h3><p>{escape(quiz.instructions)}</p>"
    )
    question_widgets: list[widgets.RadioButtons] = []
    feedback_widgets: list[widgets.HTML] = []
    children: list[widgets.Widget] = [title]

    for number, question in enumerate(quiz.questions, start=1):
        prompt = widgets.HTML(
            f"<p><strong>{number}. {escape(question.prompt)}</strong></p>"
        )
        radio = widgets.RadioButtons(
            options=_option_labels(question),
            value=None,
            description="",
            disabled=False,
        )
        feedback = widgets.HTML("")
        question_widgets.append(radio)
        feedback_widgets.append(feedback)
        children.extend([prompt, radio, feedback])

    score = widgets.HTML("")
    check = widgets.Button(description="Check answers", button_style="primary")
    reset = widgets.Button(description="Reset", button_style="")

    def selected_answers() -> list[int | None]:
        return [radio.value for radio in question_widgets]

    def update_feedback(_: object) -> None:
        answers = selected_answers()
        correct_count = 0
        for answer, question, feedback in zip(
            answers, quiz.questions, feedback_widgets, strict=True
        ):
            if answer is None:
                feedback.value = "<em>Choose an answer before checking.</em>"
            elif answer == question.answer_index:
                correct_count += 1
                feedback.value = f"✅ Correct. {escape(question.explanation)}"
            else:
                correct = question.answer
                feedback.value = (
                    f"❌ Not yet. Correct answer: <strong>{escape(correct)}</strong>. "
                    f"{escape(question.explanation)}"
                )
        score.value = f"<strong>Score: {correct_count}/{len(quiz.questions)}</strong>"

    def reset_quiz(_: object) -> None:
        for radio in question_widgets:
            radio.value = None
        for feedback in feedback_widgets:
            feedback.value = ""
        score.value = ""

    check.on_click(update_feedback)
    reset.on_click(reset_quiz)
    children.extend([widgets.HBox([check, reset]), score])
    return widgets.VBox(children)


def quiz_summary(quiz: Quiz) -> Sequence[str]:
    """Return plain-text quiz prompts for non-interactive contexts."""
    return tuple(question.prompt for question in quiz.questions)
