"""Fail the documentation build if expected pages or notebooks are missing."""

import base64
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from build_colab_notebooks import notebook_path_for, public_qmd_files


class LocalLinks(HTMLParser):
    """Collect file references without confusing inline code with markup."""

    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and key in {"href", "src"}:
                self.targets.append(value)


def check_site(source_root: Path = Path("docs")) -> None:
    site = source_root / "_site"
    public_pages = [
        path
        for path in source_root.rglob("*.qmd")
        if not any(part.startswith("_") for part in path.relative_to(source_root).parts)
    ]
    expected = [
        site / path.relative_to(source_root).with_suffix(".html")
        for path in public_pages
    ]
    expected.extend(
        site / notebook_path_for(path) for path in public_qmd_files(source_root)
    )
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise RuntimeError("Missing generated output:\n" + "\n".join(missing))
    broken = []
    for source in public_pages:
        output = site / source.relative_to(source_root).with_suffix(".html")
        html = output.read_text(encoding="utf-8")
        links = LocalLinks()
        links.feed(html)
        for value in links.targets:
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            target = (
                site / path.lstrip("/")
                if path.startswith("/")
                else output.parent / path
            )
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                broken.append(f"{output}: {value}")
        quiz_count = source.read_text(encoding="utf-8").count(
            'class="fcagentic-ojs-quiz-config"'
        )
        if quiz_count:
            modules = re.findall(
                r'<script type="ojs-module-contents">\s*(.*?)\s*</script>', html, re.S
            )
            executed = [
                cell
                for module in modules
                for cell in json.loads(base64.b64decode(module))["contents"]
                if "script.fcagentic-ojs-quiz-config" in cell.get("source", "")
            ]
            if len(executed) != quiz_count:
                broken.append(f"{output}: missing executable quiz renderer")
    if broken:
        raise RuntimeError("Broken rendered references:\n" + "\n".join(broken))
    print(f"Verified {len(expected)} generated HTML pages and notebooks.")


if __name__ == "__main__":
    check_site()
