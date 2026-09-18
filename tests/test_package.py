from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import freecampus_agents


def test_package_exposes_version() -> None:
    assert freecampus_agents.__version__ == "0.1.0"
    # In installed builds, distribution metadata must agree too.
    try:
        installed = version("freecampus-agents")
    except PackageNotFoundError:
        installed = None
    if installed is not None:
        assert installed == freecampus_agents.__version__


def test_package_has_typed_marker_and_fixture() -> None:
    root = Path(freecampus_agents.__file__).parent
    assert (root / "py.typed").is_file()
    assert (root / "fixtures/addition.json").is_file()
