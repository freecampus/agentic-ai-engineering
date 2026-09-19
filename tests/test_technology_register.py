"""Validate tracked research metadata without reading private plans or the web."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path("docs/courses/agentic-ai-engineering")


def test_technology_references_belong_to_existing_catalog_lessons() -> None:
    course = yaml.safe_load(Path("docs/courses/_catalog.yml").read_text())["courses"][0]
    register = yaml.safe_load((ROOT / "_technology.yml").read_text())
    assert register["schema_version"] == 1
    assert register["course_id"] == course["id"]
    lesson_ids = {
        lesson["id"] for unit in course["units"] for lesson in unit["lessons"]
    }
    entries = register["entries"]
    assert entries
    assert len({entry["id"] for entry in entries}) == len(entries)
    for entry in entries:
        assert entry["role"] in {
            "mechanism-reference",
            "optional-case-study",
            "legacy-comparison",
        }
        assert entry["lesson_ids"]
        assert len(set(entry["lesson_ids"])) == len(entry["lesson_ids"])
        assert set(entry["lesson_ids"]) <= lesson_ids
        # A researched product must not become a compulsory live dependency.
        assert entry["required_live_dependency"] is False
        assert entry["notes"].strip()


def test_review_dates_and_validation_claims_have_explicit_evidence() -> None:
    register = yaml.safe_load((ROOT / "_technology.yml").read_text())
    interval = register["review_interval_days"]
    assert 0 < interval <= 90
    assert set(register["review_triggers"]) == {
        "before-authoring-or-publication",
        "security-advisory",
        "breaking-change",
        "deprecation",
        "license-or-provider-policy-change",
    }
    for entry in register["entries"]:
        assert entry["owner"].strip() and entry["owner"] != "unassigned"
        reviewed = date.fromisoformat(entry["documentation_reviewed_on"])
        due = date.fromisoformat(entry["review_due_on"])
        assert reviewed < due <= reviewed + timedelta(days=interval)
        # Deliberately no wall-clock/network check: scheduling is not proof that
        # a human source review or an integration test was performed.
        assert entry["primary_sources"]
        for source in entry["primary_sources"]:
            parsed = urlparse(source)
            assert parsed.scheme == "https" and parsed.hostname
        assert entry["source_revision"] is None or isinstance(
            entry["source_revision"], str
        )
        status = entry["integration_status"]
        assert status in {"not-validated", "validated", "withheld", "retired"}
        assert isinstance(entry["validation_evidence"], list)
        if status == "validated":
            assert isinstance(entry["validated_version"], str)
            assert entry["validated_version"].strip()
            assert entry["validated_version"].casefold() != "latest"
            assert entry["validation_evidence"]
            assert all(
                isinstance(evidence, str) and evidence.strip()
                for evidence in entry["validation_evidence"]
            )
        elif status == "not-validated":
            assert entry["validated_version"] is None
            assert entry["validation_evidence"] == []


def test_named_cases_remain_research_not_unreviewed_runtime_adoption() -> None:
    register = yaml.safe_load((ROOT / "_technology.yml").read_text())
    entries = {entry["id"]: entry for entry in register["entries"]}
    for name in ("openclaw", "hermes-agent"):
        assert entries[name]["role"] == "optional-case-study"
        assert entries[name]["required_live_dependency"] is False
    assert entries["tgi"]["role"] == "legacy-comparison"
    guide = Path("docs/resources/contributing.qmd").read_text()
    assert "_technology.yml" in guide
    assert "90 days" in guide
    assert "recorded" in guide and "optional live integration" in guide
