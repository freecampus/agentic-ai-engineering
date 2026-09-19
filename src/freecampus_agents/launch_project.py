"""Explicit, trusted-code scaffolding/checks for the Unit 0 challenge.

The checker starts learner-authored Python with the user's permissions. It is
not a sandbox and must not be used to run an uninspected third-party project.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

import freecampus_agents


def create_launch_project(root: Path) -> Path:
    """Create a new exercise directory; never overwrite an existing workspace."""
    fixture = json.loads(
        files("freecampus_agents")
        .joinpath("fixtures/launch_project.json")
        .read_text(encoding="utf-8")
    )
    root.mkdir(parents=True, exist_ok=False)
    for name, source in fixture["files"].items():
        (root / name).write_text(source, encoding="utf-8")
    return root


def check_launch_project(root: Path) -> list[str]:
    """Check explicit inputs from another cwd in fresh processes, with a timeout.

    PYTHONPATH explicitly points at the course package already imported by this
    process. This supports offline notebook bundles; it does not validate a
    Conda/Poetry installation. Environment readiness is a separate gate.
    """
    entrypoint = root.resolve() / "launch.py"
    package_parent = str(Path(freecampus_agents.__file__).resolve().parent.parent)
    env = {**os.environ, "PYTHONPATH": package_parent, "PYTHONDONTWRITEBYTECODE": "1"}
    checks: list[str] = []
    with TemporaryDirectory(prefix="course acceptance ") as folder:
        workspace = Path(folder)
        input_path = workspace / "explicit input.json"

        def execute() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(entrypoint), str(input_path)],
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        for left, right, expected in [(7, 5, 12), (-5, 5, 0), (9, -4, 5)]:
            input_path.write_text(
                json.dumps({"left": left, "right": right}), encoding="utf-8"
            )
            result = execute()
            assert result.returncode == 0, f"Launch failed: {result.stderr}"
            payload = json.loads(result.stdout)
            assert payload["status"] == "complete"
            assert payload["answer"] == expected, "Answer does not match explicit input"
            assert [event["kind"] for event in payload["events"]] == [
                "task",
                "tool_call",
                "observation",
                "final",
            ]
            checks.append(f"{left} + {right} = {expected}; fresh process passed")
        malformed_inputs = [
            ("boolean operand", {"left": True, "right": 2}),
            ("string operand", {"left": "7", "right": 5}),
            ("unexpected field", {"left": 7, "right": 5, "extra": 0}),
        ]
        for label, data in malformed_inputs:
            input_path.write_text(json.dumps(data), encoding="utf-8")
            invalid = execute()
            assert invalid.returncode != 0, f"Invalid input accepted: {label}"
            assert invalid.stderr.strip(), "Invalid input needs a diagnostic"
            assert invalid.stdout == "", "Invalid input printed a success payload"
            checks.append(f"Rejected {label}; no success payload")
        input_path.unlink()
        missing = execute()
        assert missing.returncode != 0, "Missing input must fail"
        assert "supply its path" in missing.stderr
        assert missing.stdout == "", "Failure must not print a success payload"
        assert not input_path.exists(), "Missing input was fabricated"
        checks.append("Missing input failed explicitly; no replacement file")
    return checks
