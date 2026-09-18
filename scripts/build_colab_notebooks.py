"""Build Google Colab notebooks from canonical Quarto course sources.

The QMD files are the source of truth for the website. This script creates
matching ``.ipynb`` files at the explicit paths in their front matter. Notebook
paths remain independent of source paths and can mirror the curriculum's
course-and-unit organization on the ``gh-pages`` branch.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SOURCE_ROOT = Path("docs")
OUTPUT_ROOT = Path("docs/_site/notebooks")
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src/freecampus_agents"
SITE_URL = "https://freecampus.github.io/agentic-ai-engineering/"


@dataclass(frozen=True)
class FrontMatter:
    title: str
    body: str
    metadata: dict[str, Any]


def notebook_path_for(source: Path, source_root: Path = SOURCE_ROOT) -> Path:
    """Return a safe explicit notebook path relative to ``docs/_site``."""
    del source_root  # Retained for compatibility with existing callers.
    metadata = parse_front_matter(
        source.read_text(encoding="utf-8"), source.stem
    ).metadata
    raw = metadata.get("colab_notebook", "")
    path = Path(str(raw))
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in str(raw)
        or not path.parts
        or path.parts[0] != "notebooks"
        or path.suffix != ".ipynb"
    ):
        raise ValueError(f"Invalid Colab notebook path in {source}: {raw!r}")
    return path


def parse_front_matter(text: str, fallback_title: str) -> FrontMatter:
    """Extract a title and body from a QMD document."""
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not match:
        return FrontMatter(title=fallback_title, body=text, metadata={})
    # Preserve the final line break for YAML folded/literal scalar semantics.
    yaml_text = match.group(1) + "\n"
    body = text[match.end() :].lstrip("\n")
    metadata = yaml.safe_load(yaml_text) or {}
    if not isinstance(metadata, dict):
        raise ValueError("QMD front matter must be a mapping")
    return FrontMatter(
        title=str(metadata.get("title", fallback_title)), body=body, metadata=metadata
    )


def public_qmd_files(source_root: Path = SOURCE_ROOT) -> list[Path]:
    """List canonical public QMD pages that declare notebook output."""
    return sorted(
        path
        for path in source_root.rglob("*.qmd")
        if not any(part.startswith("_") for part in path.relative_to(source_root).parts)
        and re.search(
            r"^colab_notebook:",
            path.read_text(encoding="utf-8"),
            flags=re.M,
        )
    )


def is_python_fence(info: str) -> bool:
    """Return True when a fenced block should become a notebook code cell."""
    normalized = info.strip().lower()
    return normalized == "python" or normalized.startswith("{python")


def clean_code(source: str) -> str:
    """Remove Quarto cell options that are useful for HTML but noisy in Colab."""
    lines = []
    for line in source.splitlines():
        if line.lstrip().startswith("#|"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip("\n")


def convert_quarto_div_start(line: str) -> str | None:
    """Convert a small subset of Quarto div starts to notebook-friendly text."""
    if not line.startswith(":::"):
        return line
    title_match = re.search(r'title="([^"]+)"', line)
    if title_match:
        return f"> **{title_match.group(1)}**"
    if line.strip() == ":::":
        return ""
    return ""


def quiz_markdown(match: re.Match[str]) -> str:
    """Keep browser checkpoint questions as offline notebook practice."""
    quiz = json.loads(match.group(1))
    lines = [f"### {quiz['title']}", "", quiz["instructions"], ""]
    for number, question in enumerate(quiz["questions"], 1):
        lines.append(f"**{number}. {question['prompt']}**\n")
        lines.extend(
            f"- {chr(65 + i)}. {option}" for i, option in enumerate(question["options"])
        )
        answer = chr(65 + question["answer_index"])
        lines.extend(
            [
                "\n<details><summary>Check your answer</summary>\n",
                f"**{answer}.** {question['explanation']}",
                "\n</details>\n",
            ]
        )
    return "\n".join(lines)


def clean_markdown(markdown: str) -> str:
    """Remove website-only syntax from markdown notebook cells."""
    markdown = re.sub(
        r'<script type="application/json" '
        r'class="fcagentic-ojs-quiz-config">(.*?)</script>',
        quiz_markdown,
        markdown,
        flags=re.S,
    )
    markdown = re.sub(r"\{\{<\s*include\s+[^>]+>\}\}", "", markdown)
    markdown = re.sub(r"<!--\s*/?fcagentic-[^>]+-->", "", markdown)

    cleaned_lines = []
    for line in markdown.splitlines():
        converted = convert_quarto_div_start(line.strip())
        if converted is None:
            continue
        cleaned_lines.append(
            converted if line.strip().startswith(":::") else line.rstrip()
        )

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def markdown_cell(source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code_cell(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def package_setup_cell() -> dict[str, Any]:
    """Embed this checkout's small package, not a network install command."""
    sources = {
        path.relative_to(PACKAGE_ROOT.parent).as_posix(): path.read_text(
            encoding="utf-8"
        )
        for path in sorted(PACKAGE_ROOT.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json", ".typed"}
    }
    source = (
        "# Bundled course source: restart the kernel, then run from the top.\n"
        "import json\nimport sys\nimport tempfile\nfrom pathlib import Path\n\n"
        "if any(name == 'freecampus_agents' or name.startswith('freecampus_agents.')\n"
        "       for name in sys.modules):\n"
        "    raise RuntimeError('Restart the kernel before rerunning package setup.')\n"
        "_course_sources = json.loads(" + repr(json.dumps(sources)) + ")\n"
        "_course_root = Path(tempfile.mkdtemp(prefix='freecampus-agents-'))\n"
        "for _name, _source in _course_sources.items():\n"
        "    _file = _course_root / _name\n"
        "    _file.parent.mkdir(parents=True, exist_ok=True)\n"
        "    _file.write_text(_source, encoding='utf-8')\n"
        "sys.path.insert(0, str(_course_root))\n"
    )
    cell = code_cell(source)
    cell["metadata"] = {"jupyter": {"source_hidden": True}, "tags": ["course-setup"]}
    return cell


def split_qmd_cells(markdown: str) -> list[dict[str, Any]]:
    """Split QMD body into notebook markdown and code cells."""
    cells: list[dict[str, Any]] = []
    markdown_buffer: list[str] = []
    fence_info: str | None = None
    fence_buffer: list[str] = []

    def flush_markdown() -> None:
        text = clean_markdown("\n".join(markdown_buffer))
        markdown_buffer.clear()
        if text:
            cells.append(markdown_cell(text))

    def flush_fence() -> None:
        nonlocal fence_info
        info = fence_info or ""
        text = "\n".join(fence_buffer).strip("\n")
        fence_buffer.clear()
        if is_python_fence(info):
            code = clean_code(text)
            if code:
                cells.append(code_cell(code))
        else:
            fenced = f"```{info}\n{text}\n```".strip()
            markdown = clean_markdown(fenced)
            if markdown:
                cells.append(markdown_cell(markdown))
        fence_info = None

    for line in markdown.splitlines():
        if fence_info is None:
            if line.startswith("```"):
                flush_markdown()
                fence_info = line[3:].strip()
                fence_buffer = []
            else:
                markdown_buffer.append(line)
        else:
            if line.startswith("```"):
                flush_fence()
            else:
                fence_buffer.append(line)

    if fence_info is not None:
        # Preserve an unterminated fence as markdown rather than dropping content.
        markdown_buffer.append(f"```{fence_info}")
        markdown_buffer.extend(fence_buffer)
    flush_markdown()
    return cells


def qmd_to_notebook(source: Path, source_root: Path = SOURCE_ROOT) -> dict[str, Any]:
    """Convert one lesson QMD file to an in-memory notebook dictionary."""
    fallback_title = source.stem.replace("-", " ").title()
    parsed = parse_front_matter(source.read_text(encoding="utf-8"), fallback_title)
    rel_source = source.relative_to(source_root).as_posix()
    intro = (
        f"# {parsed.title}\n\n"
        "Generated from FreeCampus Agentic AI Engineering. "
        "Run cells from top to bottom, write predictions before execution, and "
        "change one thing at a time.\n\n"
        f"[Source page]({SITE_URL}{Path(rel_source).with_suffix('.html')})"
    )

    def public_link(match: re.Match[str]) -> str:
        target, _, fragment = match.group(1).partition("#")
        if "://" in target:
            return match.group(0)
        resolved = (source.parent / target).resolve()
        relative = resolved.relative_to(source_root.resolve()).with_suffix(".html")
        anchor = f"#{fragment}" if fragment else ""
        return f"]({SITE_URL}{relative.as_posix()}{anchor})"

    body = re.sub(r"\]\(([^)\s]+\.qmd(?:#[^)]*)?)\)", public_link, parsed.body)
    cells = [markdown_cell(intro)]
    if parsed.metadata.get("notebook_package"):
        cells.append(package_setup_cell())
    cells.extend(split_qmd_cells(body))
    for index, cell in enumerate(cells):
        cell["id"] = f"cell-{index:04d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build_notebooks(
    source_root: Path = SOURCE_ROOT, output_root: Path = OUTPUT_ROOT
) -> list[Path]:
    """Build all public lesson notebooks and return written paths."""
    written: list[Path] = []
    sources = public_qmd_files(source_root)
    destinations = [notebook_path_for(p, source_root) for p in sources]
    if len(set(destinations)) != len(destinations):
        raise ValueError("Duplicate Colab notebook paths")
    for source, destination in zip(sources, destinations, strict=True):
        relative_notebook = destination.relative_to("notebooks")
        output = output_root / relative_notebook
        output.parent.mkdir(parents=True, exist_ok=True)
        notebook = qmd_to_notebook(source, source_root)
        output.write_text(
            json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        written.append(output)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()

    written = build_notebooks(args.source_root, args.output_root)
    print(f"Built {len(written)} Colab notebooks in {args.output_root}")


if __name__ == "__main__":
    main()
