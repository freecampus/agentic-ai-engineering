"""Publication barriers must be enforced, not just documented in the review guide."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml


def site_fixture(root: Path) -> None:
    root.mkdir()
    (root / "index.qmd").write_text("---\ntitle: Home\n---\nPublic orientation\n")
    (root / "draft.qmd").write_text(
        "---\ntitle: Draft\ndraft: true\ncontent_status: draft\n"
        "colab_notebook: notebooks/draft.ipynb\n---\nDraft instruction\n"
    )
    for output in ("_site", "_review"):
        folder = root / output
        folder.mkdir()
        (folder / "index.html").write_text("<html>Public orientation</html>")
    (root / "_site/draft.html").write_text("")
    (root / "_review/draft.html").write_text(
        '<header class="fc-learning-header">Review draft</header>'
    )
    (root / "_review/notebooks").mkdir()
    (root / "_review/notebooks/draft.ipynb").write_text("{}")


@pytest.mark.parametrize("review", [False, True])
def test_site_checker_accepts_separate_public_and_review_outputs(
    tmp_path, monkeypatch, review
):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    checker = importlib.import_module("check_site")
    root = tmp_path / "docs"
    site_fixture(root)
    checker.check_site(root, review=review)


@pytest.mark.parametrize("leak", ["notebook", "html", "colab"])
def test_site_checker_rejects_draft_publication_leaks(tmp_path, monkeypatch, leak):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    checker = importlib.import_module("check_site")
    root = tmp_path / "docs"
    site_fixture(root)
    if leak == "notebook":
        folder = root / "_site/notebooks"
        folder.mkdir()
        (folder / "draft.ipynb").write_text("{}")
    elif leak == "html":
        (root / "_site/draft.html").write_text(
            '<header class="fc-learning-header">Leak</header>'
        )
    else:
        (root / "_review/draft.html").write_text(
            '<a href="https://colab.research.google.com/unpublished">Colab</a>'
        )
    with pytest.raises(RuntimeError, match="draft"):
        checker.check_site(root, review=leak == "colab")


def test_review_profile_is_separate_and_links_only_authored_sources():
    config = yaml.safe_load(Path("docs/_quarto.yml").read_text())
    profile = yaml.safe_load(Path("docs/_quarto-review.yml").read_text())
    assert config["website"]["draft-mode"] == "gone"
    assert profile["website"]["draft-mode"] == "visible"
    assert profile["project"]["output-dir"] == "_review"
    entries = profile["website"]["sidebar"][0]["contents"][0]["contents"]
    assert len(entries) == 7
    for item in entries:
        assert (
            Path("docs") / (item["href"] if isinstance(item, dict) else item)
        ).is_file()
    workflow = Path(".github/workflows/docs.yml").read_text()
    assert "docs/_site" in workflow
    assert "_review" not in workflow
