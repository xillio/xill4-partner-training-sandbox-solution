"""Filesystem checks -- the workhorse for migrations that land content on disk or a share."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from grader.checks import Outcome, check, compare_number
from grader.context import Context

# A failure list longer than this is noise; the trainee needs a sample, not a dump.
_MAX_REPORTED = 10


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative_files(root: Path, pattern: str) -> list[str]:
    """Relative paths under `root`, always with forward slashes.

    Windows hands back backslashes, while every path stored in a manifest, a CSV or a
    scenario file uses forward slashes. Normalising here -- at the one boundary where
    filesystem paths become data -- is what keeps grading identical on both platforms.
    """
    return sorted(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())


@check("fs.file_count")
def file_count(params: dict[str, Any], ctx: Context) -> Outcome:
    """Count files under a directory matching a glob. Params: path, pattern, equals|min|max."""
    root = ctx.path(params["path"])
    pattern = ctx.expand(params.get("pattern", "**/*"))
    if not root.is_dir():
        return Outcome(False, f"{root} does not exist or is not a directory", {"path": str(root)})

    matches = _relative_files(root, pattern)
    label = f"files matching {pattern!r} under {root.name}"
    outcome = compare_number(len(matches), params, label, ctx)
    outcome.evidence["sample"] = matches[:_MAX_REPORTED]
    return outcome


@check("fs.tree_matches")
def tree_matches(params: dict[str, Any], ctx: Context) -> Outcome:
    """Compare a directory against a manifest of {relative path: sha256}.

    Params: path, manifest (JSON file, normally grader-only and derived from the
    trainee's seed), compare ("content" default, or "paths" to ignore file contents).
    """
    root = ctx.path(params["path"])
    manifest_path = ctx.path(params["manifest"])
    compare_content = ctx.expand(params.get("compare", "content")) == "content"

    expected: dict[str, str] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not root.is_dir():
        return Outcome(
            False,
            f"{root} does not exist; expected {len(expected)} files there",
            {"path": str(root), "missing": sorted(expected)[:_MAX_REPORTED]},
        )

    actual = set(_relative_files(root, "**/*"))
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))

    differing: list[str] = []
    if compare_content:
        for relpath in sorted(set(expected) & actual):
            if _sha256(root / relpath) != expected[relpath]:
                differing.append(relpath)

    evidence = {
        "expected_files": len(expected),
        "actual_files": len(actual),
        "missing": missing[:_MAX_REPORTED],
        "unexpected": unexpected[:_MAX_REPORTED],
        "wrong_content": differing[:_MAX_REPORTED],
    }
    problems = [
        f"{len(missing)} missing" if missing else "",
        f"{len(unexpected)} unexpected" if unexpected else "",
        f"{len(differing)} with wrong content" if differing else "",
    ]
    problems = [p for p in problems if p]
    if problems:
        return Outcome(False, f"{root.name} does not match the expected tree: " +
                       ", ".join(problems), evidence)
    return Outcome(True, f"{root.name} matches the expected tree ({len(expected)} files)", evidence)


@check("fs.exists")
def exists(params: dict[str, Any], ctx: Context) -> Outcome:
    """Assert a file or directory exists. Params: path, kind (file|dir|any)."""
    target = ctx.path(params["path"])
    kind = ctx.expand(params.get("kind", "any"))
    found = {"file": target.is_file, "dir": target.is_dir, "any": target.exists}[kind]()
    label = {"file": "file", "dir": "directory", "any": "path"}[kind]
    return Outcome(found, f"{label} {target} {'exists' if found else 'is missing'}",
                   {"path": str(target)})
