"""Version alignment tests."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_init_version_matches_pyproject():
    """__init__.__version__ must match pyproject.toml version."""
    from payroll_engine import __version__

    pyproject = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, "Could not find version in pyproject.toml"
    assert __version__ == match.group(1), (
        f"__init__.__version__ ({__version__}) != pyproject.toml ({match.group(1)})"
    )


def test_version_is_semver():
    """Version must be valid semver."""
    from payroll_engine import __version__

    assert re.match(r"^\d+\.\d+\.\d+", __version__), (
        f"Version {__version__} is not valid semver"
    )


def test_cli_version_flag():
    """psp --version must print version and exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "payroll_engine.psp.cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "psp" in result.stdout
    # Version string should contain digits
    assert re.search(r"\d+\.\d+\.\d+", result.stdout)
