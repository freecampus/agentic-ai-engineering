from __future__ import annotations

import copy
import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

spec = importlib.util.spec_from_file_location(
    "check_lesson_plan", "scripts/check_lesson_plan.py"
)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

COURSE = yaml.safe_load(Path("docs/courses/_catalog.yml").read_text(encoding="utf-8"))[
    "courses"
][0]


def replace_record(text: str, index: int, **changes: Any) -> str:
    matches = list(re.finditer(r"^```yaml\n(.*?)^```", text, re.M | re.S))
    match = matches[index]
    record = yaml.safe_load(match.group(1))
    record.update(changes)
    return (
        text[: match.start(1)]
        + yaml.safe_dump(record, sort_keys=False, allow_unicode=True)
        + text[match.end(1) :]
    )


def synthetic_plan(course: dict[str, Any]) -> str:
    """Build test-only records from tracked catalog data, never private plans.

    The short synthetic brief text exercises structure, not teaching quality.
    It is not a replacement lesson plan and is never written to the repository.
    """
    chunks = ["# Synthetic checker fixture", checker.START, checker.END]
    reviews = {record["unit_id"] for record in course["cumulative_reviews"]}
    previous: list[str] = []

    def record(**values: Any) -> None:
        values.update(owner="unassigned", last_updated="2026-09-19", blockers=[])
        chunks.append("```yaml\n" + yaml.safe_dump(values, sort_keys=False) + "```")

    def state() -> dict[str, Any]:
        return {"status": "not_done", "evidence": {}}

    for unit in course["units"]:
        number = unit["number"]
        chunks.append(f"## U{number:02} — Unit {number}: {unit['title']}")
        chunks.extend([unit["outcome"], unit["challenge"]["summary"]])
        gates = {
            key: state()
            for key in ("overview", "challenge", "integration", "validation")
        }
        if unit["id"] in reviews:
            gates["cumulative_review"] = state()
        record(
            kind="unit", milestone_id=f"U{number:02}", unit_id=unit["id"], gates=gates
        )
        for index, lesson in enumerate(unit["lessons"], 1):
            task_id = f"L{number:02}.{index}"
            chunks.append(f"### {task_id} — {lesson['title']}")
            record(
                kind="lesson",
                task_id=task_id,
                lesson_id=lesson["id"],
                target="docs/" + lesson["path"],
                depends_on=previous,
                **state(),
            )
            chunks.extend(
                [
                    f"**Scope:** {lesson['summary']}",
                    f"**Expected evidence:** {lesson['evidence']}",
                    "**Entry check:** Test fixture prerequisite.",
                    "**Learner questions**\n\n1. Predict?\n2. Inspect?\n3. Repair?",
                    "**Teaching sequence**\n\n"
                    "1. Specify.\n2. Run.\n3. Inspect.\n4. Explain.",
                    "**Runnable cases and controlled variations:** Test fixture input.",
                    "**Misconceptions and failure clinic:** Test fixture defect.",
                    "**Three checkpoint targets**\n\n"
                    "1. Concept.\n2. Evidence.\n3. Diagnosis.",
                    f"**Lab contract:** Synthetic lab for {lesson['id']}.",
                    "**Independent acceptance checks**\n\n"
                    "1. Ordinary.\n2. Boundary.\n3. Failure.",
                    "**Unfamiliar transfer and mastery:** Test fixture variation.",
                    "**Primary-source verification targets:** "
                    "Test fixture reference target.",
                ]
            )
            previous = [lesson["id"]]
    chunks.append("## Synthetic capstone")
    record(
        kind="capstone",
        project_id=course["capstone"]["id"],
        stages={stage["id"]: state() for stage in course["capstone"]["stages"]},
    )
    chunks.append("## Synthetic release")
    record(
        kind="release",
        gates={
            key: state()
            for key in (
                "dependency_lock",
                "cross_platform_ci",
                "visual_review",
                "workload_pilot",
                "completion_audit",
            )
        },
    )
    text = "\n\n".join(chunks) + "\n"
    return checker.refresh_dashboard(text, checker.parse_records(text), course)


# Isolate mutation tests from legitimate future publication progress too.
for unit in COURSE["units"]:
    unit["challenge"]["status"] = "planned"
    for lesson in unit["lessons"]:
        lesson["status"] = "planned"
PLAN = synthetic_plan(COURSE)


def test_checker_validates_the_complete_synthetic_course() -> None:
    records = checker.validate(PLAN, COURSE)
    assert len([r for r in records if r["kind"] == "unit"]) == 25
    assert len([r for r in records if r["kind"] == "lesson"]) == 101
    assert len([r for r in records if r["kind"] == "capstone"]) == 1
    assert len([r for r in records if r["kind"] == "release"]) == 1
    assert checker.refresh_dashboard(PLAN, records, COURSE) == PLAN


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        (
            "**Entry check:** Test fixture prerequisite.",
            "",
            "missing brief field Entry check",
        ),
        (
            "**Entry check:** Test fixture prerequisite.",
            "**Entry check:**",
            "missing brief field",
        ),
        ("3. Repair?", "", "Learner questions needs 3"),
        ("4. Explain.", "", "Teaching sequence needs 4"),
        ("3. Diagnosis.", "", "Three checkpoint targets needs 3"),
        ("3. Failure.", "", "Independent acceptance checks needs 3"),
    ],
)
def test_local_brief_checks_reject_missing_or_incomplete_sections(
    old: str, new: str, error: str
) -> None:
    with pytest.raises(checker.PlanError, match=error):
        checker.validate(PLAN.replace(old, new, 1), COURSE)


def test_local_brief_checks_reject_duplicate_labs() -> None:
    lessons = COURSE["units"][0]["lessons"]
    text = PLAN.replace(
        f"**Lab contract:** Synthetic lab for {lessons[1]['id']}.",
        f"**Lab contract:** Synthetic lab for {lessons[0]['id']}.",
        1,
    )
    with pytest.raises(checker.PlanError, match="duplicate lab contract"):
        checker.validate(text, COURSE)


@pytest.mark.parametrize("args", [[], ["--refresh"]])
def test_explicit_local_command_reports_missing_plan_without_creating_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker.main(args) == 1
    output = capsys.readouterr().out
    assert "Local lesson plan not found" in output
    assert "not required by CI" in output
    assert not (tmp_path / "PLAN-LESSONS.md").exists()


def test_explicit_local_command_validates_and_refreshes_supplied_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    catalog = tmp_path / "docs/courses/_catalog.yml"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(yaml.safe_dump({"courses": [COURSE]}), encoding="utf-8")
    path = tmp_path / "PLAN-LESSONS.md"
    stale = replace_record(PLAN, 1, status="in_progress", owner="test editor")
    path.write_text(stale, encoding="utf-8")
    assert checker.main([]) == 1
    assert path.read_text(encoding="utf-8") == stale
    assert checker.main(["--refresh"]) == 0
    assert checker.main([]) == 0
    refreshed = path.read_text(encoding="utf-8")
    assert checker.parse_records(refreshed) == checker.parse_records(stale)
    assert refreshed.split(checker.END)[1] == stale.split(checker.END)[1]
    invalid = refreshed.replace("**Entry check:** Test fixture prerequisite.", "", 1)
    path.write_text(invalid, encoding="utf-8")
    assert checker.main(["--refresh"]) == 1
    assert path.read_text(encoding="utf-8") == invalid


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"status": "done"}, "invalid status"),
        ({"status": ["implemented"]}, "invalid status"),
        ({"status": "in_progress"}, "assign an owner"),
        ({"status": "blocked", "owner": "editor"}, "blocked needs a reason"),
        (
            {"blockers": ["Awaiting review"], "owner": "editor"},
            "require blocked status",
        ),
        ({"last_updated": "2026-02-30"}, "invalid last_updated"),
        ({"last_updated": "tomorrow"}, "quoted ISO date"),
        ({"evidence": []}, "evidence must be a mapping"),
        ({"evidence": {"content": ""}}, "nonempty reference strings"),
        ({"lesson_id": "invented.lesson"}, "wrong lesson ID"),
        ({"task_id": "L01.1"}, "wrong task ID"),
        ({"target": "docs/invented.qmd"}, "wrong target path"),
        ({"depends_on": ["future.lesson"]}, "wrong prerequisite"),
        (
            {"status": "implemented", "owner": "editor"},
            "missing implementation evidence",
        ),
    ],
)
def test_invalid_lesson_records_fail(changes: dict[str, Any], error: str) -> None:
    with pytest.raises(checker.PlanError, match=error):
        checker.validate_records(replace_record(PLAN, 1, **changes), COURSE)


@pytest.mark.parametrize("status", ["in_review", "implemented"])
def test_review_and_done_require_real_matching_source(
    tmp_path: Path, status: str
) -> None:
    evidence = dict.fromkeys(checker.LESSON_EVIDENCE, "review-report.md#verified-run")
    text = replace_record(PLAN, 1, status=status, owner="editor", evidence=evidence)
    with pytest.raises(checker.PlanError, match="content file does not exist"):
        checker.validate_records(text, COURSE, tmp_path)
    source = tmp_path / "docs" / COURSE["units"][0]["lessons"][0]["path"]
    source.parent.mkdir(parents=True)
    source.write_text("---\nlesson_id: wrong.lesson\n---\n", encoding="utf-8")
    with pytest.raises(checker.PlanError, match="content lesson_id mismatch"):
        checker.validate_records(text, COURSE, tmp_path)
    lid = COURSE["units"][0]["lessons"][0]["id"]
    source.write_text(f"---\nlesson_id: {lid}\n---\n", encoding="utf-8")
    # Structural validation is deliberately not a claim of pedagogical review.
    checker.validate_records(text, COURSE, tmp_path)


def test_refresh_preserves_content_and_states_and_is_idempotent() -> None:
    text = replace_record(PLAN, 1, status="in_progress", owner="editor")
    records = checker.validate_records(text, COURSE)
    with pytest.raises(checker.PlanError, match="Stale development dashboard"):
        checker.validate(text, COURSE)
    refreshed = checker.refresh_dashboard(text, records, COURSE)
    checker.validate(refreshed, COURSE)
    assert checker.refresh_dashboard(refreshed, records, COURSE) == refreshed
    assert checker.parse_records(refreshed) == records
    assert refreshed.split(checker.START)[0] == text.split(checker.START)[0]
    assert refreshed.split(checker.END)[1] == text.split(checker.END)[1]
    assert "`not_done`: 100; `in_progress`: 1" in refreshed
    assert "Lessons implemented: 0/101 (0.0%)" in refreshed
    assert "Publication (separate catalog state): 0 available lessons" in refreshed


def test_all_lessons_done_does_not_complete_a_unit_without_its_gates() -> None:
    records = checker.parse_records(PLAN)
    unit = copy.deepcopy(records[0])
    tasks = copy.deepcopy(records[1:6])
    for task in tasks:
        task["status"] = "implemented"
    assert checker.unit_status(unit, tasks) == "in_progress"
    for gate in unit["gates"].values():
        gate["status"] = "in_review"
    assert checker.unit_status(unit, tasks) == "in_review"
    for gate in unit["gates"].values():
        gate["status"] = "implemented"
    assert checker.unit_status(unit, tasks) == "implemented"
    unit["blockers"] = ["Broken integration regression; editor to repair it"]
    assert checker.unit_status(unit, tasks) == "blocked"


def test_gate_progress_changes_milestone_but_not_lesson_counts() -> None:
    gates = checker.parse_records(PLAN)[0]["gates"]
    gates["overview"]["status"] = "in_progress"
    text = replace_record(PLAN, 0, owner="editor", gates=gates)
    records = checker.validate_records(text, COURSE)
    assert checker.unit_status(records[0], records[1:6]) == "in_progress"
    refreshed = checker.refresh_dashboard(text, records, COURSE)
    assert "`not_done`: 101; `in_progress`: 0" in refreshed
    assert "Unit gates implemented: 0/106" in refreshed


def test_cumulative_review_and_capstone_stages_cannot_be_dropped() -> None:
    records = checker.parse_records(PLAN)
    index = next(i for i, r in enumerate(records) if r.get("milestone_id") == "U04")
    gates = records[index]["gates"]
    del gates["cumulative_review"]
    with pytest.raises(checker.PlanError, match="wrong gates"):
        checker.validate_records(replace_record(PLAN, index, gates=gates), COURSE)
    with pytest.raises(checker.PlanError, match="Wrong capstone stages"):
        checker.validate_records(
            replace_record(PLAN, len(records) - 2, stages={}), COURSE
        )


def test_missing_or_duplicate_records_are_rejected() -> None:
    block = re.search(r"^```yaml\n.*?^```", PLAN, re.M | re.S)
    assert block
    with pytest.raises(checker.PlanError, match="Record counts/order"):
        checker.validate_records(PLAN.replace(block.group(), "", 1), COURSE)
    with pytest.raises(checker.PlanError, match="Record counts/order"):
        checker.validate_records(PLAN + "\n" + block.group(), COURSE)


def test_missing_scope_and_renamed_headings_are_rejected() -> None:
    with pytest.raises(checker.PlanError, match="Lesson headings"):
        checker.validate_records(
            PLAN.replace("### L00.1 —", "### Lesson one —"), COURSE
        )
    evidence = COURSE["units"][0]["lessons"][0]["evidence"]
    # Allow Markdown wrapping without hiding missing instructional scope.
    flattened = " ".join(PLAN.split())
    assert evidence in flattened
    text = re.sub(re.escape(evidence).replace(r"\ ", r"\s+"), "REMOVED", PLAN)
    with pytest.raises(checker.PlanError, match="missing scope/evidence"):
        checker.validate_records(text, COURSE)


def test_available_catalog_lessons_cannot_be_unimplemented() -> None:
    course = copy.deepcopy(COURSE)
    course["units"][0]["lessons"][0]["status"] = "available"
    with pytest.raises(checker.PlanError, match="published before done"):
        checker.validate_records(PLAN, course)


def test_available_challenges_require_a_completed_assessment_gate() -> None:
    course = copy.deepcopy(COURSE)
    course["units"][0]["challenge"]["status"] = "available"
    with pytest.raises(checker.PlanError, match="challenge published before gate done"):
        checker.validate_records(PLAN, course)


def test_unit_blockers_need_an_accountable_owner() -> None:
    text = replace_record(PLAN, 0, blockers=["Missing browser; arrange review"])
    with pytest.raises(checker.PlanError, match="assign a blocker owner"):
        checker.validate_records(text, COURSE)


@pytest.mark.parametrize(
    "text", ["[]", "kind: unknown", "kind: [lesson]", "kind: [unterminated"]
)
def test_malformed_yaml_has_a_clear_error(text: str) -> None:
    with pytest.raises(checker.PlanError):
        checker.parse_records(f"```yaml\n{text}\n```\n")


@pytest.mark.parametrize(
    "text",
    [
        "no markers",
        checker.END + checker.START,
        checker.START + checker.START + checker.END,
    ],
)
def test_refresh_refuses_missing_duplicate_or_reversed_markers(text: str) -> None:
    with pytest.raises(checker.PlanError, match=r"[Dd]ashboard marker"):
        checker.refresh_dashboard(text, checker.parse_records(PLAN), COURSE)
