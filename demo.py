#!/usr/bin/env python3
"""Prove the grading loop works, in one command, on any OS.

    python demo.py

Needs Python 3.11+ and PyYAML. No make, no bash, no Docker, no Xill4.

Five checks, each printing what it proves. A non-zero exit means one of the claims in
the README does not hold on this machine.
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "scenarios" / "01-legacy-fileshare"
SANDBOX = ROOT / ".workspaces" / "demo"

RULE = "─" * 72
failures: list[str] = []


def step(number: int, title: str, proves: str) -> None:
    print(f"\n{RULE}\n{number}. {title}\n   proves: {proves}\n{RULE}")


def run(script: Path, *args: str) -> str:
    result = subprocess.run([sys.executable, str(script), *args],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"could not run {script.name}:\n{result.stderr}")
    return result.stdout


def grade(workspace: Path) -> tuple[int, str]:
    """Grade a workspace the way the Check my work button will. Returns (score, output)."""
    result = subprocess.run(
        [sys.executable, "-m", "grader", str(SCENARIO), "--workspace", str(workspace)],
        capture_output=True, text=True, cwd=ROOT, check=False,
        env={**_env(), "PYTHONPATH": str(ROOT / "grader")},
    )
    output = result.stdout + result.stderr
    score = next((int(line.split(":")[1].split("/")[0])
                  for line in output.splitlines() if line.startswith("Score:")), -1)
    return score, output


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("SANDBOX_")}


def expect(label: str, actual: object, wanted: object) -> None:
    ok = actual == wanted
    print(f"   {'OK  ' if ok else 'BAD '} {label}: {actual!r}"
          f"{'' if ok else f' (expected {wanted!r})'}")
    if not ok:
        failures.append(label)


def main() -> int:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)

    step(1, "Seed one trainee's workspace",
         "each trainee gets their own generated copy of the legacy share")
    print(run(SCENARIO / "seedgen.py", "--workspace", str(SANDBOX), "--seed", "alice:01").strip())
    files = sorted(p for p in (SANDBOX / "source").rglob("*") if p.is_file())
    print(f"   source/ holds {len(files)} files, e.g. "
          f"{files[1].relative_to(SANDBOX / 'source')}")
    expect("answer key is generated outside source/ and target/",
           (SANDBOX / ".expected").is_dir(), True)

    step(2, "Grade it before anyone has done the work",
         "the checks actually test something -- an empty target scores nothing")
    score, output = grade(SANDBOX)
    print("\n".join(f"   {line}" for line in output.splitlines() if line.strip()))
    expect("score on an untouched workspace", score, 0)

    step(3, "Run the reference solution, then grade again",
         "a correct migration scores full marks")
    print("   " + run(SCENARIO / "solution" / "solve.py", "--workspace", str(SANDBOX)).strip())
    score, output = grade(SANDBOX)
    print("\n".join(f"   {line}" for line in output.splitlines() if line.strip()))
    expect("score on a correct workspace", score, 100)

    step(4, "Introduce two mistakes a trainee would actually make",
         "grading is specific: it names the wrong value and costs only that task")
    metadata = SANDBOX / "target" / "metadata.csv"
    with metadata.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    print(f"   row 1: created {rows[0]['created']!r} -> '04/03/2019'   (date left unnormalised)")
    print(f"   row 2: department {rows[1]['department']!r} -> 'Finance Dept'"
          "   (vocabulary not applied)")
    rows[0]["created"] = "04/03/2019"
    rows[1]["department"] = "Finance Dept"
    with metadata.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    score, output = grade(SANDBOX)
    print("\n".join(f"   {line}" for line in output.splitlines() if line.strip()))
    expect("score with one task broken", score, 75)

    step(5, "Seed a second trainee",
         "seeds differ per trainee, so a copied answer is worth nothing")
    other = ROOT / ".workspaces" / "demo-other"
    if other.exists():
        shutil.rmtree(other)
    run(SCENARIO / "seedgen.py", "--workspace", str(other), "--seed", "bob:01")
    for name, workspace in (("alice", SANDBOX), ("bob", other)):
        with (workspace / "source" / "metadata.csv").open(newline="", encoding="utf-8") as handle:
            row = next(csv.DictReader(handle))
        print(f"   {name:<6} {row['file_path']}")
        print(f"          created={row['created']!r}  department={row['department']!r}")
    expect("the two trainees got different data",
           (SANDBOX / ".expected" / "metadata.csv").read_text(encoding="utf-8") !=
           (other / ".expected" / "metadata.csv").read_text(encoding="utf-8"), True)

    print(f"\n{RULE}")
    if failures:
        print(f"FAILED: {len(failures)} claim(s) did not hold: {', '.join(failures)}")
        return 1
    print("All five claims hold. Workspaces left in .workspaces/ if you want to poke around;")
    print("delete them with:  python demo.py --clean")
    return 0


if __name__ == "__main__":
    if "--clean" in sys.argv:
        shutil.rmtree(ROOT / ".workspaces", ignore_errors=True)
        print("removed .workspaces/")
        raise SystemExit(0)
    raise SystemExit(main())
