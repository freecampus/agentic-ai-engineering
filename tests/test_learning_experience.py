from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

DOCS = Path("docs")
COURSE_ROOT = DOCS / "courses/agentic-ai-engineering"


def front(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def pages() -> list[Path]:
    return [
        p
        for p in DOCS.rglob("*.qmd")
        if not any(part.startswith("_") for part in p.relative_to(DOCS).parts)
    ]


def catalog() -> dict[str, Any]:
    return yaml.safe_load((DOCS / "courses/_catalog.yml").read_text(encoding="utf-8"))[
        "courses"
    ][0]


def sidebar_paths(items: list[Any]) -> list[str]:
    paths = []
    for item in items:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict):
            if "href" in item:
                paths.append(item["href"])
            paths.extend(sidebar_paths(item.get("contents", [])))
    return paths


def test_catalog_records_the_exact_planned_course() -> None:
    course = catalog()
    assert course["id"] == "agentic-ai-engineering"
    assert course["status"] == "in-development"
    units = course["units"]
    assert [u["number"] for u in units] == list(range(25))
    assert [len(u["lessons"]) for u in units] == [5] + [4] * 24
    assert course["planned_unit_count"] == len(units) == 25
    assert (
        course["planned_lesson_count"] == sum(len(u["lessons"]) for u in units) == 101
    )
    assert course["planned_challenge_count"] == len(units) == 25
    assert len(course["milestones"]) == 4
    assert [p["unit_id"] for p in course["milestones"]] == [
        units[i]["id"] for i in [4, 8, 16, 24]
    ]
    for milestone in course["milestones"]:
        unit = next(u for u in units if u["id"] == milestone["unit_id"])
        assert milestone["challenge_id"] == unit["challenge"]["id"]
        assert milestone["title"] == unit["challenge"]["title"]
        path, anchor = milestone["path"].split("#")
        assert f"{{#{anchor}}}" in (DOCS / path).read_text(encoding="utf-8")
    assert [r["unit_id"] for r in course["cumulative_reviews"]] == [
        units[i]["id"] for i in [4, 8, 12, 16, 20, 24]
    ]
    assert [s["id"] for s in course["capstone"]["stages"]] == [
        f"C{i}" for i in range(1, 7)
    ]


def test_catalog_titles_outcomes_and_evidence_match_the_specification() -> None:
    plan = Path("PLAN-DETAILS.md").read_text(encoding="utf-8")
    units = catalog()["units"]
    assert re.findall(r"^# Unit \d+ — (.+)$", plan, re.M) == [u["title"] for u in units]
    assert re.findall(r"^## Lesson \d+\.\d+ — (.+)$", plan, re.M) == [
        lesson["title"] for u in units for lesson in u["lessons"]
    ]
    for unit in units:
        assert unit["outcome"] in plan
        assert unit["challenge"]["summary"] in plan
        for lesson in unit["lessons"]:
            assert lesson["summary"] in plan
            assert lesson["evidence"] in plan


def test_stable_unique_ownership_and_acyclic_unit_prerequisites() -> None:
    seen = set()
    activity_ids = []
    activity_paths = []
    for unit in catalog()["units"]:
        assert unit["id"] not in seen
        assert set(unit["prerequisite_unit_ids"]) <= seen
        seen.add(unit["id"])
        assert [lesson["order"] for lesson in unit["lessons"]] == list(
            range(10, 10 * len(unit["lessons"]) + 1, 10)
        )
        for activity in [*unit["lessons"], unit["challenge"]]:
            assert activity["id"].startswith(unit["id"] + ".")
            assert f"/units/{unit['id']}/" in activity["path"]
            assert activity["status"] in {"planned", "available"}
            activity_ids.append(activity["id"])
            activity_paths.append(activity["path"])
            if activity["status"] == "available":
                assert (DOCS / activity["path"]).is_file()
    assert len(activity_ids) == len(set(activity_ids))
    assert len(activity_paths) == len(set(activity_paths))
    actual = {front(p).get("lesson_id") for p in pages() if front(p).get("lesson_id")}
    registered = {
        lesson["id"]
        for u in catalog()["units"]
        for lesson in u["lessons"]
        if lesson["status"] == "available"
    }
    assert actual == registered


def test_publication_counts_completion_and_home_metadata_agree() -> None:
    course = catalog()
    metadata = yaml.safe_load(
        (COURSE_ROOT / "_metadata.yml").read_text(encoding="utf-8")
    )
    home = front(COURSE_ROOT / "index.qmd")
    lessons = [
        lesson["id"]
        for u in course["units"]
        for lesson in u["lessons"]
        if lesson["status"] == "available"
    ]
    challenges = [
        u["challenge"]["id"]
        for u in course["units"]
        if u["challenge"]["status"] == "available"
    ]
    assert (
        course["completion"]["lesson_ids"]
        == metadata["completion_lesson_ids"]
        == lessons
    )
    assert (
        course["completion"]["challenge_ids"]
        == metadata["completion_challenge_ids"]
        == challenges
    )
    assert course["available_lesson_count"] == len(lessons) == 0
    assert course["available_challenge_count"] == len(challenges) == 0
    assert not course["completion"]["enabled"]
    assert not metadata["completion_enabled"]
    assert metadata["course_id"] == course["id"]
    assert metadata["curriculum_version"] == course["curriculum_version"] == 1
    assert metadata["completion_rule_version"] == course["completion"]["rule_version"]
    for key in [
        "planned_unit_count",
        "planned_lesson_count",
        "planned_challenge_count",
        "available_lesson_count",
        "available_challenge_count",
    ]:
        assert home[key] == course[key]
    assert "0 of 101 lessons and 0 of 25 unit challenges" in (
        COURSE_ROOT / "index.qmd"
    ).read_text(encoding="utf-8")


def test_overviews_metadata_outcomes_and_sidebar_match() -> None:
    course = catalog()
    outcomes = yaml.safe_load(
        (COURSE_ROOT / "_outcomes.yml").read_text(encoding="utf-8")
    )
    assert outcomes["curriculum_version"] == course["curriculum_version"]
    assert outcomes["course_id"] == course["id"]
    assert len(outcomes["units"]) == 25
    config = yaml.safe_load((DOCS / "_quarto.yml").read_text(encoding="utf-8"))
    sidebar = config["website"]["sidebar"][0]
    paths = sidebar_paths(sidebar["contents"])
    for unit, mapped in zip(course["units"], outcomes["units"], strict=True):
        path = DOCS / unit["overview"]
        meta = front(path)
        inherited = yaml.safe_load(
            path.with_name("_metadata.yml").read_text(encoding="utf-8")
        )
        assert inherited["unit_id"] == unit["id"]
        assert inherited["unit_number"] == unit["number"]
        assert inherited["course_id"] == course["id"]
        assert meta["title"] == unit["title"] + " Overview"
        assert meta["content_kind"] == "unit-overview"
        assert "lesson_id" not in meta and "challenge_id" not in meta
        assert "fcagentic-ojs-quiz-config" not in path.read_text(encoding="utf-8")
        assert "Curriculum preview—not a released unit" in path.read_text(
            encoding="utf-8"
        )
        assert mapped["id"] == unit["id"]
        assert mapped["outcome"] == unit["outcome"]
        assert mapped["lesson_ids"] == [lesson["id"] for lesson in unit["lessons"]]
        assert mapped["challenge_id"] == unit["challenge"]["id"]
        assert (
            set(mapped["graduate_outcome_ids"]) <= outcomes["graduate_outcomes"].keys()
        )
        assert unit["overview"] in paths
        assert any(
            i.get("section") == f"Unit {unit['number']}: {unit['title']}"
            for i in sidebar["contents"]
        )
    for path in paths:
        assert (DOCS / path).is_file(), path
    for item in config["website"]["navbar"]["left"]:
        assert (DOCS / item["href"]).is_file()


def test_internal_links_and_includes_resolve_without_planned_lesson_links() -> None:
    for page in pages():
        text = page.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)\s]+\.qmd(?:#[^)]*)?)\)", text):
            if "://" not in target:
                assert (page.parent / target.split("#")[0]).resolve().is_file(), (
                    page,
                    target,
                )
        for target in re.findall(r"\{\{< include (.+?) >\}\}", text):
            assert (page.parent / target).is_file(), (page, target)


def test_all_public_quiz_payloads_are_valid_unique_and_balanced() -> None:
    quiz_ids = []
    question_ids = []
    positions = Counter()
    for page in pages():
        text = page.read_text(encoding="utf-8")
        payloads = re.findall(
            r'class="fcagentic-ojs-quiz-config">(.*?)</script>', text, re.S
        )
        if front(page).get("assessable"):
            assert payloads, page
        assert text.count("_includes/ojs-quiz.qmd") == len(payloads)
        for raw in payloads:
            quiz = json.loads(raw)
            quiz_ids.append(quiz["id"])
            assert quiz["questions"]
            for question in quiz["questions"]:
                question_ids.append(question["id"])
                assert len(question["options"]) == 4
                assert question["explanation"]
                assert 0 <= question["answer_index"] < 4
                positions[question["answer_index"]] += 1
    assert len(quiz_ids) >= 2
    assert len(quiz_ids) == len(set(quiz_ids))
    assert len(question_ids) == len(set(question_ids))
    assert max(positions.values()) - min(positions.values()) <= 1


def test_python_fences_parse_or_have_exactly_one_intentional_marker() -> None:
    for page in pages():
        text = page.read_text(encoding="utf-8")
        for fence in re.finditer(
            r"```(?:python|\{python[^}]*\})\n(.*?)\n```", text, re.S
        ):
            marked = (
                text[: fence.start()]
                .rstrip()
                .endswith("<!-- fcagentic-intentional-invalid-python -->")
            )
            try:
                ast.parse(fence[1])
            except SyntaxError:
                assert marked, (page, fence[1])
            else:
                assert not marked, page
        for mermaid in re.findall(r"```\{mermaid\}\n(.*?)\n```", text, re.S):
            assert "%%| echo: false" in mermaid
            assert "%%| eval: true" in mermaid
            assert "flowchart" in mermaid


def test_shared_site_configuration_and_retired_identity_cleanup() -> None:
    config = yaml.safe_load((DOCS / "_quarto.yml").read_text(encoding="utf-8"))
    assert config["execute"]["eval"] is False
    assert (
        config["website"]["repo-url"]
        == "https://github.com/freecampus/agentic-ai-engineering"
    )
    assert config["website"]["site-url"].endswith("/agentic-ai-engineering/")
    assert "In development" in config["website"]["page-footer"]["center"]
    assert "_includes/course-ui.html" in config["format"]["html"]["include-after-body"]
    for path in [
        *pages(),
        Path("README.md"),
        Path("AGENTS.md"),
        DOCS / "_includes/colab-link.qmd",
        DOCS / "_partials/title-block.html",
    ]:
        for retired in [
            "fcpython",
            "python-foundations",
            "freecampus/python",
            "FreeCampus Python",
        ]:
            assert retired not in path.read_text(encoding="utf-8"), (path, retired)
    assert not Path("src/fcpython").exists()
    assert not Path("poetry.lock").exists()


def test_preserved_quiz_css_and_title_identity() -> None:
    styles = (DOCS / "styles.css").read_text(encoding="utf-8")
    for selector in [
        ".fcagentic-quiz",
        ".fcagentic-quiz-step",
        ".fcagentic-quiz-feedback",
    ]:
        assert selector in styles
    title = (DOCS / "_partials/title-block.html").read_text(encoding="utf-8")
    for attr in [
        "data-fc-course-id",
        "data-fc-content-status",
        "data-fc-lesson-id",
        "data-fc-challenge-id",
        "data-fc-lesson-ids",
        "data-fc-storage-status",
    ]:
        assert attr in title
