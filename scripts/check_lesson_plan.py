"""Locally validate lesson briefs, records, and the PLAN-LESSONS.md dashboard.

PLAN*.md files are ignored personal planning material, not CI inputs. This
explicit command requires the local lesson plan; it never creates one. The
tracked catalog and QMD sources own public curriculum and publication status.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- development-dashboard:start -->"
END = "<!-- development-dashboard:end -->"
STATUSES = ("not_done", "in_progress", "in_review", "implemented", "blocked")
LESSON_EVIDENCE = {
    "content",
    "code_and_tests",
    "clean_notebook",
    "pedagogical_review",
    "accessibility_review",
    "references_and_licenses",
}
RELEASE_GATES = {
    "dependency_lock",
    "cross_platform_ci",
    "visual_review",
    "workload_pilot",
    "completion_audit",
}


class PlanError(ValueError):
    """A development record or its generated dashboard is inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanError(message)


def parse_records(text: str) -> list[dict[str, Any]]:
    records = []
    for match in re.finditer(r"^```yaml\n(.*?)^```\s*$", text, re.M | re.S):
        try:
            record = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            raise PlanError(f"Invalid YAML record: {exc}") from exc
        require(isinstance(record, dict), "Each YAML block must be a record")
        require(
            isinstance(record.get("kind"), str)
            and record["kind"] in {"unit", "lesson", "capstone", "release"},
            f"Unknown record kind: {record.get('kind')}",
        )
        records.append(record)
    require(bool(records), "No development records found")
    return records


def check_identity(record: dict[str, Any], label: str) -> None:
    owner = record.get("owner")
    require(isinstance(owner, str) and bool(owner.strip()), f"{label}: missing owner")
    updated = record.get("last_updated")
    require(
        isinstance(updated, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated)),
        f"{label}: last_updated must be a quoted ISO date",
    )
    try:
        dt.date.fromisoformat(updated)
    except ValueError as exc:
        raise PlanError(f"{label}: invalid last_updated date") from exc
    blockers = record.get("blockers")
    require(
        isinstance(blockers, list)
        and all(isinstance(b, str) and bool(b.strip()) for b in blockers),
        f"{label}: blockers must be a list of nonempty reasons",
    )
    if blockers:
        require(owner != "unassigned", f"{label}: assign a blocker owner")


def check_state(
    record: dict[str, Any],
    label: str,
    parent: dict[str, Any] | None = None,
    evidence_keys: set[str] | None = None,
) -> None:
    status = record.get("status")
    require(isinstance(status, str) and status in STATUSES, f"{label}: invalid status")
    identity = parent if parent is not None else record
    if status != "not_done":
        require(identity["owner"] != "unassigned", f"{label}: assign an owner")
    if status == "blocked":
        require(bool(identity["blockers"]), f"{label}: blocked needs a reason")
    evidence = record.get("evidence")
    require(isinstance(evidence, dict), f"{label}: evidence must be a mapping")
    require(
        all(isinstance(v, str) and bool(v.strip()) for v in evidence.values()),
        f"{label}: evidence entries must be nonempty reference strings",
    )
    if status == "implemented":
        keys = evidence_keys if evidence_keys is not None else {"artifact", "review"}
        require(keys <= evidence.keys(), f"{label}: missing implementation evidence")


def unit_status(unit: dict[str, Any], lessons: list[dict[str, Any]]) -> str:
    states = [r["status"] for r in lessons] + [
        gate["status"] for gate in unit["gates"].values()
    ]
    if unit["blockers"] or "blocked" in states:
        return "blocked"
    if all(s == "implemented" for s in states):
        return "implemented"
    if all(s in {"in_review", "implemented"} for s in states):
        return "in_review"
    if any(s != "not_done" for s in states):
        return "in_progress"
    return "not_done"


def validate_records(
    text: str, course: dict[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    records = parse_records(text)
    units = course["units"]
    expected_kinds = []
    for unit in units:
        expected_kinds.extend(["unit"] + ["lesson"] * len(unit["lessons"]))
    expected_kinds.extend(["capstone", "release"])
    require(
        [r["kind"] for r in records] == expected_kinds,
        "Record counts/order must match unit milestones and their catalog lessons",
    )
    require(
        len(units) == course["planned_unit_count"]
        and sum(len(u["lessons"]) for u in units) == course["planned_lesson_count"],
        "Catalog planned counts disagree with its records",
    )
    require(
        re.findall(r"^## (U\d{2} — Unit \d+: .+)$", text, re.M)
        == [f"U{u['number']:02} — Unit {u['number']}: {u['title']}" for u in units],
        "Unit headings must match catalog titles and order",
    )
    require(
        re.findall(r"^### (L\d{2}\.\d+ — .+)$", text, re.M)
        == [
            f"L{u['number']:02}.{i} — {lesson['title']}"
            for u in units
            for i, lesson in enumerate(u["lessons"], 1)
        ],
        "Lesson headings must match catalog titles and order",
    )
    normalized = " ".join(text.split())
    reviews = {r["unit_id"] for r in course["cumulative_reviews"]}
    previous: list[str] = []
    index = 0
    for unit in units:
        record = records[index]
        index += 1
        uid = unit["id"]
        mid = f"U{unit['number']:02}"
        require(record.get("milestone_id") == mid, f"{uid}: wrong milestone ID")
        require(record.get("unit_id") == uid, f"{mid}: wrong unit ID")
        check_identity(record, mid)
        require(
            "status" not in record, f"{mid}: milestone status is derived, not stored"
        )
        gates = record.get("gates")
        expected = {"overview", "challenge", "integration", "validation"}
        if uid in reviews:
            expected.add("cumulative_review")
        require(
            isinstance(gates, dict) and set(gates) == expected, f"{mid}: wrong gates"
        )
        for name, gate in gates.items():
            require(isinstance(gate, dict), f"{mid}/{name}: gate must be a mapping")
            check_state(gate, f"{mid}/{name}", record)
        if unit["challenge"]["status"] == "available":
            require(
                gates["challenge"]["status"] == "implemented",
                f"{mid}: challenge published before gate done",
            )
        for field in [unit["outcome"], unit["challenge"]["summary"]]:
            require(" ".join(field.split()) in normalized, f"{mid}: missing unit scope")
        for number, lesson in enumerate(unit["lessons"], 1):
            task = records[index]
            index += 1
            tid = f"L{unit['number']:02}.{number}"
            require(task.get("task_id") == tid, f"{tid}: wrong task ID")
            require(task.get("lesson_id") == lesson["id"], f"{tid}: wrong lesson ID")
            require(task.get("depends_on") == previous, f"{tid}: wrong prerequisite")
            target = "docs/" + lesson["path"]
            require(task.get("target") == target, f"{tid}: wrong target path")
            check_identity(task, tid)
            check_state(task, tid, evidence_keys=LESSON_EVIDENCE)
            require(
                not task["blockers"] or task["status"] == "blocked",
                f"{tid}: unresolved blockers require blocked status",
            )
            if task["status"] in {"in_review", "implemented"}:
                path = root / target
                require(path.is_file(), f"{tid}: content file does not exist")
                parts = path.read_text(encoding="utf-8").split("---", 2)
                require(
                    len(parts) == 3 and not parts[0].strip(), f"{tid}: no front matter"
                )
                try:
                    front = yaml.safe_load(parts[1])
                except yaml.YAMLError as exc:
                    raise PlanError(f"{tid}: invalid front matter") from exc
                require(
                    isinstance(front, dict) and front.get("lesson_id") == lesson["id"],
                    f"{tid}: content lesson_id mismatch",
                )
            if lesson["status"] == "available":
                require(
                    task["status"] == "implemented", f"{tid}: published before done"
                )
            for field in [lesson["summary"], lesson["evidence"]]:
                require(
                    " ".join(field.split()) in normalized,
                    f"{tid}: missing scope/evidence",
                )
            previous = [lesson["id"]]
    capstone, release = records[-2:]
    for record in [capstone, release]:
        check_identity(record, record["kind"])
        require("status" not in record, "Course-level rollups are derived, not stored")
    require(capstone.get("project_id") == course["capstone"]["id"], "Wrong capstone ID")
    stages = capstone.get("stages")
    require(
        isinstance(stages, dict)
        and list(stages) == [s["id"] for s in course["capstone"]["stages"]],
        "Wrong capstone stages/order",
    )
    for name, stage in stages.items():
        require(isinstance(stage, dict), f"{name}: stage must be a mapping")
        check_state(stage, name, capstone)
    gates = release.get("gates")
    require(
        isinstance(gates, dict) and set(gates) == RELEASE_GATES,
        "Wrong course release gates",
    )
    for name, gate in gates.items():
        require(isinstance(gate, dict), f"{name}: gate must be a mapping")
        check_state(gate, name, release)
    return records


def dashboard(records: list[dict[str, Any]], course: dict[str, Any]) -> str:
    units = [r for r in records if r["kind"] == "unit"]
    lessons = [r for r in records if r["kind"] == "lesson"]
    counts = Counter(r["status"] for r in lessons)
    gate_counts = Counter(g["status"] for u in units for g in u["gates"].values())
    rows = []
    statuses = []
    for record, unit in zip(units, course["units"], strict=True):
        tasks = [r for r in lessons if r["lesson_id"].split(".")[0] == unit["id"]]
        c = Counter(t["status"] for t in tasks)
        state = unit_status(record, tasks)
        statuses.append(state)
        done_gates = sum(g["status"] == "implemented" for g in record["gates"].values())
        rows.append(
            f"| [{record['milestone_id']}](#{record['milestone_id'].lower()}) "
            f"| {unit['title']} | {len(tasks)} | "
            + " | ".join(str(c[s]) for s in STATUSES)
            + f" | {done_gates}/{len(record['gates'])} | `{state}` |"
        )
    done = counts["implemented"]
    published = sum(
        lesson["status"] == "available"
        for unit in course["units"]
        for lesson in unit["lessons"]
    )
    challenges = sum(u["challenge"]["status"] == "available" for u in course["units"])
    capstone, release = records[-2:]
    cap_done = sum(s["status"] == "implemented" for s in capstone["stages"].values())
    release_done = sum(g["status"] == "implemented" for g in release["gates"].values())
    return "\n".join(
        [
            START,
            "",
            f"**Lessons implemented: {done}/{len(lessons)} "
            f"({100 * done / len(lessons):.1f}%).** "
            f"Unit milestones implemented: "
            f"{statuses.count('implemented')}/{len(units)}.",
            "",
            "Lesson states: "
            + "; ".join(f"`{s}`: {counts[s]}" for s in STATUSES)
            + ".",
            "",
            f"Unit gates implemented: "
            f"{gate_counts['implemented']}/{sum(gate_counts.values())}. "
            f"Capstone stages implemented: {cap_done}/{len(capstone['stages'])}. "
            f"Course release gates implemented: "
            f"{release_done}/{len(release['gates'])}.",
            "",
            f"Publication (separate catalog state): {published} available lessons; "
            f"{challenges} available unit challenges. Previews do not count.",
            "",
            "| Milestone | Unit | Lessons | Not done | In progress | In review "
            "| Implemented | Blocked | Gates done | Derived status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            *rows,
            "",
            END,
        ]
    )


def refresh_dashboard(
    text: str, records: list[dict[str, Any]], course: dict[str, Any]
) -> str:
    require(
        text.count(START) == text.count(END) == 1,
        "Need exactly one dashboard marker pair",
    )
    start, end = text.index(START), text.index(END)
    require(start < end, "Dashboard markers are reversed")
    return text[:start] + dashboard(records, course) + text[end + len(END) :]


def validate(
    text: str, course: dict[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    records = validate_records(text, course, root)
    validate_briefs(text)
    require(
        refresh_dashboard(text, records, course) == text,
        "Stale development dashboard; run scripts/check_lesson_plan.py --refresh",
    )
    return records


def validate_briefs(text: str) -> None:
    """Keep the former real-plan pytest checks in the explicit local command.

    These are structural checks, not a substitute for independent teaching review.
    Each brief is isolated so a later lesson/unit cannot supply its missing fields.
    """
    headings = list(re.finditer(r"^### (L\d{2}\.\d+) — [^\n]+$", text, re.M))
    require(bool(headings), "No lesson briefs found")
    labs = set()
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end() : end]
        body = re.split(r"^## ", body, maxsplit=1, flags=re.M)[0]
        parts = re.split(r"^\*\*([^*\n]+)\*\*", body, flags=re.M)
        fields = {
            name.removesuffix(":"): content.strip()
            for name, content in zip(parts[1::2], parts[2::2], strict=True)
        }
        label = heading.group(1)
        for name in (
            "Scope",
            "Expected evidence",
            "Entry check",
            "Learner questions",
            "Teaching sequence",
            "Runnable cases and controlled variations",
            "Misconceptions and failure clinic",
            "Three checkpoint targets",
            "Lab contract",
            "Independent acceptance checks",
            "Unfamiliar transfer and mastery",
            "Primary-source verification targets",
        ):
            require(bool(fields.get(name)), f"{label}: missing brief field {name}")
        for name, count in (
            ("Learner questions", 3),
            ("Teaching sequence", 4),
            ("Three checkpoint targets", 3),
            ("Independent acceptance checks", 3),
        ):
            numbers = re.findall(r"^(\d+)\. ", fields[name], re.M)
            require(
                numbers == [str(i) for i in range(1, count + 1)],
                f"{label}: {name} needs {count} numbered items",
            )
        lab = " ".join(fields["Lab contract"].split())
        require(lab not in labs, f"{label}: duplicate lab contract")
        labs.add(lab)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh dashboard only")
    args = parser.parse_args(argv)
    path = ROOT / "PLAN-LESSONS.md"
    if not path.is_file():
        print(
            "Local lesson plan not found: PLAN-LESSONS.md. PLAN*.md files are "
            "intentionally ignored and are not required by CI. Obtain your "
            "maintainer's local plan before running plan.check or plan.refresh; "
            "no placeholder has been created."
        )
        return 1
    try:
        course = yaml.safe_load(
            (ROOT / "docs/courses/_catalog.yml").read_text(encoding="utf-8")
        )["courses"][0]
        text = path.read_text(encoding="utf-8")
        if args.refresh:
            records = validate_records(text, course, ROOT)
            validate_briefs(text)
            text = refresh_dashboard(text, records, course)
            path.write_text(text, encoding="utf-8")
        records = validate(text, course, ROOT)
    except (PlanError, OSError, yaml.YAMLError) as exc:
        print(f"Lesson plan check failed: {exc}")
        return 1
    print(
        f"Lesson plan valid: {sum(r['kind'] == 'unit' for r in records)} "
        f"unit milestones, {sum(r['kind'] == 'lesson' for r in records)} "
        "lesson tasks; dashboard current."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
