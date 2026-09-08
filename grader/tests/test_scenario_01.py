"""The two invariants every scenario must satisfy before it can be put in front of a trainee.

A check suite that passes a correct answer but also passes an empty workspace grades
nothing. Both directions are asserted here, and in CI, for every scenario in the repo.
"""

import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCENARIO_01
from grader.context import Context
from grader.models import load_scenario
from grader.runner import run_scenario

SCENARIOS = sorted(p.parent for p in REPO_ROOT.glob("scenarios/*/scenario.yaml"))


@pytest.mark.parametrize("scenario_dir", SCENARIOS, ids=lambda p: p.name)
def test_scenario_definition_is_valid(scenario_dir: Path) -> None:
    scenario = load_scenario(scenario_dir)
    assert scenario.total_weight == 100, "scenarios are scored out of 100"
    assert (scenario_dir / scenario.brief).is_file(), "every scenario needs a trainee brief"


def test_reference_solution_scores_full_marks(solved_workspace, scenario_vars) -> None:
    scenario = load_scenario(REPO_ROOT / "scenarios" / "01-legacy-fileshare")
    report = run_scenario(scenario, Context(solved_workspace, scenario_vars(solved_workspace)))

    assert report.passed, [c.message for t in report.tasks for c in t.checks if not c.passed]
    assert report.score == report.max_score == 100


def test_untouched_workspace_fails_every_task(seeded_workspace, scenario_vars) -> None:
    scenario = load_scenario(REPO_ROOT / "scenarios" / "01-legacy-fileshare")
    report = run_scenario(scenario, Context(seeded_workspace, scenario_vars(seeded_workspace)))

    assert not report.passed
    assert report.score == 0
    assert all(not task.passed for task in report.tasks)


def test_seed_data_differs_between_trainees(tmp_path, seeded_workspace) -> None:
    other = tmp_path / "other"
    subprocess.run([sys.executable, str(SCENARIO_01 / "seedgen.py"), "--workspace", str(other),
                    "--seed", "someone-else:01"], check=True, capture_output=True)

    assert (other / ".expected" / "metadata.csv").read_text() != \
        (seeded_workspace / ".expected" / "metadata.csv").read_text()


def test_seeding_is_reproducible(tmp_path) -> None:
    outputs = []
    for name in ("first", "second"):
        target = tmp_path / name
        subprocess.run([sys.executable, str(SCENARIO_01 / "seedgen.py"), "--workspace",
                        str(target), "--seed", "same-seed:01"], check=True, capture_output=True)
        outputs.append((target / ".expected" / "content_tree.json").read_text())

    assert outputs[0] == outputs[1], "the same seed must always produce the same workspace"


def test_no_seed_puts_two_documents_on_one_target_path() -> None:
    """A collision would silently lose a document and still score 100/100.

    The answer key is derived from the same seed as the source data, so if two documents
    mapped to one target path both sides would collapse identically and the grader would
    award full marks for a migration that dropped a file. Titles must stay unique.
    """
    spec = importlib.util.spec_from_file_location("seedgen", SCENARIO_01 / "seedgen.py")
    seedgen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seedgen)

    for index in range(200):
        digest = hashlib.sha256(f"trainee-{index}:01".encode()).hexdigest()
        documents = seedgen.build_documents(random.Random(digest))
        migrated = [d for d in documents if d["status"] == "active" and "defect" not in d]
        paths = [f"{d['department']}/{d['year']}/{d['doc_id']}.{d['extension']}" for d in migrated]
        assert len(paths) == len(set(paths)), f"seed trainee-{index}:01 collides"


def test_seeded_documents_are_written_byte_for_byte(seeded_workspace) -> None:
    """Seed content must hit the disk unchanged, on every platform.

    The answer key stores a sha256 of each document body and the grader compares content
    byte for byte. Writing in text mode on Windows rewrote every \n as \r\n, so a correct
    migration scored 60/100 with all 19 documents reported as having the wrong content.
    """
    documents = [p for p in (seeded_workspace / "source").rglob("*")
                 if p.is_file() and p.name != "metadata.csv"]
    assert documents

    for document in documents:
        assert b"\r\n" not in document.read_bytes(), f"{document.name} has translated newlines"

    expected_hashes = set(json.loads(
        (seeded_workspace / ".expected" / "content_tree.json").read_text(encoding="utf-8")
    ).values())
    on_disk = {hashlib.sha256(d.read_bytes()).hexdigest() for d in documents}
    assert expected_hashes <= on_disk, "answer key hashes disagree with the bytes on disk"


def test_partial_work_scores_partially(solved_workspace, scenario_vars) -> None:
    """Deleting one deliverable costs exactly that task's weight and nothing else."""
    (solved_workspace / "target" / "exceptions.csv").unlink()
    scenario = load_scenario(REPO_ROOT / "scenarios" / "01-legacy-fileshare")
    report = run_scenario(scenario, Context(solved_workspace, scenario_vars(solved_workspace)))

    failed = [task.id for task in report.tasks if not task.passed]
    assert failed == ["exceptions"]
    assert report.score == 80
