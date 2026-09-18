"""Small checkpoints shared by the website and notebook widgets."""

from freecampus_agents.questions import MultipleChoiceQuestion as Question
from freecampus_agents.questions import Quiz


def smoke_lab_quiz() -> Quiz:
    """Assess the observable behavior of the offline smoke lab."""
    return Quiz(
        id="agent-lab-checkpoint",
        title="Inspect the bounded run",
        questions=(
            Question(
                id="agent-lab-decision-budget",
                prompt="Why does max_steps=1 stop before a final answer?",
                options=(
                    "The one decision was spent requesting the addition tool.",
                    "The calculator requires internet access.",
                    "A smaller budget makes addition inaccurate.",
                    "The fixture chooses a random stopping point.",
                ),
                answer_index=0,
                explanation="The tool runs on decision one; returning its result needs "
                "decision two. The runtime, not the model, enforces this limit.",
            ),
            Question(
                id="agent-lab-evidence",
                prompt="What does a successful smoke_test establish?",
                options=(
                    "Hosted language models will always choose the right tool.",
                    "This package reproduces one recorded deterministic run.",
                    "Every possible task is supported.",
                    "The course's production security review has passed.",
                ),
                answer_index=1,
                explanation="A fixture checks a narrow contract. It does not measure "
                "model quality or establish production readiness.",
            ),
            Question(
                id="agent-lab-authorization",
                prompt="What happens when a test double requests a shell tool?",
                options=(
                    "The runtime executes the shell but hides its output.",
                    "The model's confidence determines permission.",
                    "The runtime returns denied without executing that tool.",
                    "The runtime retries until permission appears.",
                ),
                answer_index=2,
                explanation="Only the pure add tool is available. A tool name in a "
                "model decision is a request, not authorization.",
            ),
            Question(
                id="agent-lab-zero-observation",
                prompt="What should run_agent(Task(-5, 5)) return?",
                options=(
                    "budget_exhausted because zero is false-like",
                    "invalid because negative inputs are forbidden",
                    "complete with no answer",
                    "complete with answer 0",
                ),
                answer_index=3,
                explanation="The runtime distinguishes None from 0. A zero sum is a "
                "valid observation and final answer.",
            ),
        ),
    )


def readiness_quiz() -> Quiz:
    """Assess concrete prerequisite Python behavior, not self-confidence."""
    return Quiz(
        id="python-readiness-checkpoint",
        title="Check the Python you will use",
        questions=(
            Question(
                id="readiness-alias",
                prompt="a = [1]; b = a; b.append(2). What is a?",
                options=("[1, 2]", "[1]", "[2]", "An unbound name"),
                answer_index=0,
                explanation="Both names refer to the same mutable list. This matters "
                "when a runtime shares state between components.",
            ),
            Question(
                id="readiness-return",
                prompt="A function only prints 12. What value does its call return?",
                options=("12", "None", '"12"', "True"),
                answer_index=1,
                explanation="Displaying output is not returning data. Tool contracts "
                "need explicit return values.",
            ),
            Question(
                id="readiness-failure",
                prompt='What happens when int("twelve") is evaluated?',
                options=(
                    "It returns 12.",
                    "It returns None.",
                    "It raises ValueError.",
                    "It retries with a different spelling.",
                ),
                answer_index=2,
                explanation="Conversion rejects this text; a caller needs an explicit "
                "failure policy rather than assuming a usable number.",
            ),
            Question(
                id="readiness-independent-test",
                prompt="Which test checks an addition function against an independent "
                "expected value?",
                options=(
                    "assert add(2, 3) == add(2, 3)",
                    "print(add(2, 3))",
                    "assert callable(add)",
                    "assert add(2, 3) == 5",
                ),
                answer_index=3,
                explanation="The expected value comes from the contract, not a second "
                "call to the same possibly incorrect implementation.",
            ),
        ),
    )
