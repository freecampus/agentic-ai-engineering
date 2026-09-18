from __future__ import annotations

import shutil
import subprocess

import pytest


def test_progress_uses_only_published_ids_and_survives_invalid_storage() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed for the browser-progress behavior test")
    subprocess.run(
        [node, "tests/browser_progress.cjs"],
        check=True,
        capture_output=True,
        text=True,
    )
