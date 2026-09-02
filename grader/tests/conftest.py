import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_01 = REPO_ROOT / "scenarios" / "01-legacy-fileshare"


def _run(script: Path, *args: str) -> None:
    subprocess.run([sys.executable, str(script), *args], check=True, capture_output=True)


@pytest.fixture
def seeded_workspace(tmp_path: Path) -> Path:
    """A freshly seeded scenario-01 workspace with an empty target/ -- an untouched trainee."""
    _run(SCENARIO_01 / "seedgen.py", "--workspace", str(tmp_path), "--seed", "test-trainee:01")
    return tmp_path


@pytest.fixture
def solved_workspace(seeded_workspace: Path) -> Path:
    """The same workspace after the reference solution has run."""
    _run(SCENARIO_01 / "solution" / "solve.py", "--workspace", str(seeded_workspace))
    return seeded_workspace


@pytest.fixture
def scenario_vars():
    def build(workspace: Path) -> dict[str, str]:
        return {
            "SOURCE": str(workspace / "source"),
            "TARGET": str(workspace / "target"),
            "EXPECTED": str(workspace / ".expected"),
        }

    return build
