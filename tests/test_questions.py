from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from freecampus_agents.questions import MultipleChoiceQuestion, Quiz
from freecampus_agents.quiz_banks import readiness_quiz, smoke_lab_quiz
from freecampus_agents.widgets import quiz_summary, show_quiz


@pytest.mark.parametrize("bank", [readiness_quiz, smoke_lab_quiz])
def test_quiz_round_trip_and_answer_balance(bank) -> None:
    quiz = bank()
    assert json.loads(quiz.to_json()) == quiz.to_dict()
    assert {q.answer_index for q in quiz.questions} == {0, 1, 2, 3}
    assert len(quiz_summary(quiz)) == 4


def test_multiple_choice_question_validates_answer_index() -> None:
    with pytest.raises(ValueError, match="answer_index"):
        MultipleChoiceQuestion("bad", "Bad index?", ("A", "B"), 2, "Outside options.")


@pytest.mark.parametrize(
    "field,value",
    [("id", ""), ("prompt", ""), ("options", ("A",)), ("explanation", "")],
)
def test_question_validates_required_fields(field, value) -> None:
    args = dict(
        id="q",
        prompt="Choose?",
        options=("A", "B"),
        answer_index=0,
        explanation="A fits.",
    )
    args[field] = value
    with pytest.raises(ValueError):
        MultipleChoiceQuestion(**args)


def test_quiz_rejects_duplicate_ids_and_empty_questions() -> None:
    question = smoke_lab_quiz().questions[0]
    with pytest.raises(ValueError, match="unique"):
        Quiz("q", "Title", (question, question))
    with pytest.raises(ValueError, match="at least one"):
        Quiz("q", "Title", ())


def test_json_script_preserves_code_and_cannot_close_its_tag() -> None:
    question = MultipleChoiceQuestion(
        "safe", 'Is x < 3 & "yes"? </script>', ("a < b", "b > a"), 0, "Compare < and >."
    )
    quiz = Quiz("safe", "Markup", (question,))
    script = quiz.to_json_script()
    assert script.count("</script>") == 1
    assert json.loads(script.split("\n", 1)[1].rsplit("\n", 1)[0]) == quiz.to_dict()
    assert 'class="fcagentic-ojs-quiz-config"' in script


@pytest.mark.parametrize(
    "bank,path",
    [
        (smoke_lab_quiz, "docs/resources/agent-lab.qmd"),
        (readiness_quiz, "docs/courses/agentic-ai-engineering/readiness.qmd"),
    ],
)
def test_support_page_quizzes_match_reusable_bank(bank, path) -> None:
    match = re.search(
        r'class="fcagentic-ojs-quiz-config">(.*?)</script>',
        Path(path).read_text(encoding="utf-8"),
        re.S,
    )
    assert match
    assert json.loads(match[1]) == bank().to_dict()


def test_widget_checks_and_resets_without_exposing_markup() -> None:
    pytest.importorskip("ipywidgets")
    widget = show_quiz(smoke_lab_quiz())
    assert widget.__class__.__name__ == "VBox"
    radios = [
        child for child in widget.children if child.__class__.__name__ == "RadioButtons"
    ]
    for radio, question in zip(radios, smoke_lab_quiz().questions, strict=True):
        radio.value = question.answer_index
    check, reset = widget.children[-2].children
    check.click()
    assert "4/4" in widget.children[-1].value
    reset.click()
    assert all(radio.value is None for radio in radios)
    assert widget.children[-1].value == ""


def test_shared_renderer_keeps_keyboard_navigation_and_no_auto_advance() -> None:
    renderer = Path("docs/_includes/ojs-quiz.qmd").read_text(encoding="utf-8")
    for token in [
        "ArrowRight",
        "ArrowLeft",
        "Home",
        "End",
        "aria-live",
        "Check answers",
        "Next question",
        "Previous",
        "Reset",
        "scripts.find",
    ]:
        assert token in renderer
    change_handler = renderer.split('addEventListener("change"', 1)[1].split("});", 1)[
        0
    ]
    assert "showQuestion(questionIndex + 1)" not in change_handler
