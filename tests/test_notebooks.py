from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

spec = importlib.util.spec_from_file_location(
    "build_colab_notebooks", "scripts/build_colab_notebooks.py"
)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


def test_explicit_notebook_paths_are_unique_and_mirror_source_structure() -> None:
    paths = builder.public_qmd_files()
    assert len(paths) == 30
    destinations = []
    for source in paths:
        assert "_includes/colab-link.qmd" in source.read_text(encoding="utf-8")
        target = builder.notebook_path_for(source)
        assert target == Path("notebooks") / source.relative_to("docs").with_suffix(
            ".ipynb"
        )
        destinations.append(target)
    assert len(destinations) == len(set(destinations))


def test_export_preserves_practice_without_website_scripts() -> None:
    notebook = builder.qmd_to_notebook(Path("docs/resources/agent-lab.qmd"))
    nbformat.validate(nbformat.from_dict(notebook))
    code = "\n".join(
        "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
    )
    markdown = "\n".join(
        "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "markdown"
    )
    assert "limited = run_agent" in code
    assert "class UnavailableToolModel" in code
    assert "Check your answer" in markdown
    assert "Why does max_steps=1" in markdown
    assert "document.querySelector" not in code
    assert '<script type="application/json"' not in markdown
    assert "{{<" not in markdown
    assert "](engineering-journal.qmd)" not in markdown
    assert "resources/engineering-journal.html" in markdown
    assert "Run the Offline Agent Smoke Lab" in markdown


def test_intentional_invalid_code_stays_editable() -> None:
    cells = builder.split_qmd_cells(
        "<!-- fcagentic-intentional-invalid-python -->\n"
        '```python\nif True\n    print("repair me")\n```'
    )
    assert cells[0]["cell_type"] == "code"
    assert "if True\n" in "".join(cells[0]["source"])
    assert "fcagentic" not in "".join(cells[0]["source"])


def test_smoke_notebook_executes_in_isolated_python_without_the_installed_package(
    tmp_path: Path,
) -> None:
    notebook = builder.qmd_to_notebook(Path("docs/resources/agent-lab.qmd"))
    cells = [
        "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
    ]
    script = "\n\n".join(cells)
    # -I ignores PYTHONPATH and the working directory; setup must supply the package.
    result = subprocess.run(
        [sys.executable, "-I"],
        input=script,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "TMPDIR": str(tmp_path)},
        check=True,
    )
    assert "final 12" in result.stdout
    assert "Course package: 0.1.0" in result.stdout


def test_build_writes_valid_notebooks_for_every_declared_page(tmp_path: Path) -> None:
    written = builder.build_notebooks(output_root=tmp_path)
    assert len(written) == 30
    for path in written:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        assert notebook.cells
        assert len({cell.id for cell in notebook.cells}) == len(notebook.cells)
        assert all(
            cell.execution_count is None and not cell.outputs
            for cell in notebook.cells
            if cell.cell_type == "code"
        )


@pytest.mark.parametrize(
    "target",
    [
        "../escape.ipynb",
        "notebooks/../../escape.ipynb",
        "/tmp/escape.ipynb",
        "notebooks/wrong.txt",
        "notebooks/..\\escape.ipynb",
    ],
)
def test_notebook_path_cannot_escape_output(tmp_path: Path, target: str) -> None:
    source = tmp_path / "page.qmd"
    source.write_text(
        f"---\ntitle: Test\ncolab_notebook: {json.dumps(target)}\n---\nBody\n"
    )
    with pytest.raises(ValueError, match="Invalid Colab"):
        builder.notebook_path_for(source)


def test_duplicate_destinations_fail_before_writing(tmp_path: Path) -> None:
    for name in ["first", "second"]:
        (tmp_path / f"{name}.qmd").write_text(
            "---\ntitle: Test\ncolab_notebook: notebooks/same.ipynb\n---\nBody"
        )
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Duplicate"):
        builder.build_notebooks(tmp_path, output)
    assert not output.exists()


def test_yaml_front_matter_uses_delimiter_lines_not_title_punctuation() -> None:
    parsed = builder.parse_front_matter(
        '---\ntitle: "A --- B"\ndescription: >\n'
        "  First line\n  second line\n---\nBody\n",
        "Fallback",
    )
    assert parsed.title == "A --- B"
    assert parsed.metadata["description"] == "First line second line\n"
    assert parsed.body == "Body\n"


def test_yaml_front_matter_requires_a_mapping() -> None:
    with pytest.raises(ValueError, match="mapping"):
        builder.parse_front_matter("---\n- one\n- two\n---\nBody", "Fallback")


UNIT0 = Path("docs/courses/agentic-ai-engineering/units/launch-agent-lab")
UNIT0_DRAFTS = sorted(path for path in UNIT0.glob("*.qmd") if path.stem != "index")
UNIT1 = Path("docs/courses/agentic-ai-engineering/units/choose-agent-architecture")
UNIT1_DRAFTS = sorted(path for path in UNIT1.glob("*.qmd") if path.stem != "index")


def test_draft_exports_are_explicit_and_never_target_the_public_site(tmp_path):
    assert len(UNIT0_DRAFTS) == 6
    assert len(UNIT1_DRAFTS) == 5
    assert not set(UNIT1_DRAFTS) & set(builder.public_qmd_files())
    assert set(UNIT1_DRAFTS) <= set(builder.public_qmd_files(include_drafts=True))
    assert not set(UNIT0_DRAFTS) & set(builder.public_qmd_files())
    assert set(UNIT0_DRAFTS) <= set(builder.public_qmd_files(include_drafts=True))
    with pytest.raises(ValueError, match="separate review"):
        builder.build_notebooks(include_drafts=True)
    written = builder.build_notebooks(output_root=tmp_path, include_drafts=True)
    assert len(written) == 41
    for path in written:
        nbformat.validate(nbformat.read(path, as_version=4))


def test_hidden_solutions_stay_hidden_reading_material_not_run_all_cells():
    cells = builder.split_qmd_cells(
        "Before\n<details>\n<summary>Solution</summary>\n\n"
        "```python\nanswer = 99\n```\n\n</details>\n\n"
        "```python\nprint('ordinary')\n```\n"
    )
    code = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")
    markdown = "\n".join(
        "".join(c["source"]) for c in cells if c["cell_type"] == "markdown"
    )
    assert "answer = 99" not in code
    assert "print('ordinary')" in code
    assert "<details>" in markdown and "</details>" in markdown
    assert "```python\nanswer = 99\n```" in markdown


@pytest.mark.parametrize(
    "source",
    UNIT0_DRAFTS + UNIT1_DRAFTS,
    ids=lambda path: f"{path.parent.name}-{path.stem}",
)
def test_authored_notebooks_run_cellwise_in_fresh_python_without_site_packages(
    source, tmp_path
):
    notebook = builder.qmd_to_notebook(source)
    nbformat.validate(nbformat.from_dict(notebook))
    code = [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]
    # Separate exec calls preserve notebook cell boundaries; -I -S removes ambient
    # path/site-package assistance. The bundled setup must provide the package.
    script = (
        "import json\nnamespace = {'__name__': '__main__'}\n"
        f"cells = json.loads({json.dumps(code)!r})\n"
        "for number, source in enumerate(cells):\n"
        "    exec(compile(source, f'cell-{number}', 'exec'), namespace)\n"
        "print('CLEAN_CELL_RUN_OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S"],
        input=script,
        cwd=tmp_path,
        env={**os.environ, "TMPDIR": str(tmp_path), "TEMP": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "CLEAN_CELL_RUN_OK" in result.stdout
    markdown = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )
    assert "Review draft, not a published assessment" in markdown
    assert "[Source page]" not in markdown
    assert markdown.count("<summary>Check your answer</summary>") == (
        9 if source in UNIT1_DRAFTS else 6
    )
    assert "<script" not in markdown
    for heading in re.findall(r"^## .+$", source.read_text(encoding="utf-8"), re.M):
        assert heading in markdown


@pytest.mark.parametrize(
    "source",
    UNIT0_DRAFTS + UNIT1_DRAFTS,
    ids=lambda path: f"{path.parent.name}-{path.stem}",
)
def test_authored_worked_examples_and_hidden_solutions_execute_separately(
    source, tmp_path
):
    text = source.read_text(encoding="utf-8")
    code = re.findall(r"```python\n(.*?)```", text, re.S)
    # The challenge CLI solution is a separate file, tested as such in test_unit0.
    code = [block for block in code if not block.startswith("# File: launch.py")]
    script = (
        "".join(builder.package_setup_cell()["source"]) + "\n\n" + "\n\n".join(code)
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S"],
        input=script,
        cwd=tmp_path,
        env={**os.environ, "TMPDIR": str(tmp_path), "TEMP": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    expected = {
        "meet-a-tiny-agent": "Envelope repair and denial checks passed",
        "learn-with-evidence": "Lookup contract passed",
        "use-ai-responsibly": "Reviewed arithmetic checks passed",
        "work-in-notebooks": "Explicit-input launch checks passed",
        "build-local-workspace": "Unsupported mode rejected",
        "challenge": "Denial, malformed result, and decision budget checks passed",
    }
    if source in UNIT1_DRAFTS:
        expected = {
            "separate-automation-workflows-and-agents": (
                "Classification replacement checks passed"
            ),
            "model-the-agent-environment-loop": (
                "Transition and observation checks passed"
            ),
            "bound-autonomy-with-task-contracts": (
                "Contract authorization checks passed"
            ),
            "choose-the-simplest-adequate-architecture": (
                "Architecture selection checks passed"
            ),
            "challenge": (
                "De-agentification development and qualification checks passed"
            ),
        }
    assert expected[source.stem] in result.stdout
