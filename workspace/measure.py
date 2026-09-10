"""Measure what the sandbox costs, so cohort sizing is a number rather than a guess.

`docker stats` reports an instant; a cohort has to be sized on a session. This samples
every running sandbox container over a window and reports mean and peak per container, plus
what the shared MongoDB adds once for everyone.

  python workspace/measure.py --seconds 300              # sample for five minutes
  python workspace/measure.py --seconds 300 --csv run.csv --json run.json

Run it while trainees are actually working: an idle container tells you the floor, not the
cost. The per-trainee number to plan with is the peak, because a cohort peaks together --
they are all told to press "run" at the same time.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# docker stats reports memory as "123.4MiB / 15.7GiB"; only the first half is the container.
_SIZE = re.compile(r"([\d.]+)\s*([KMGT]?i?B)", re.IGNORECASE)
_UNITS = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4,
          "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4}


def to_megabytes(value: str) -> float:
    match = _SIZE.search(value)
    if not match:
        return 0.0
    amount, unit = match.groups()
    return float(amount) * _UNITS.get(unit.lower(), 1) / 1024**2


def sample(names: list[str]) -> list[dict[str, float | str]]:
    """One `docker stats` reading for every sandbox container."""
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format",
         "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}", *names],
        capture_output=True, text=True, check=False)
    rows = []
    for line in result.stdout.strip().splitlines():
        name, _, rest = line.partition("|")
        cpu, _, memory = rest.partition("|")
        rows.append({"when": round(time.time(), 1), "container": name,
                     "cpu_percent": float(cpu.strip().rstrip("%") or 0),
                     "memory_mb": round(to_megabytes(memory), 1)})
    return rows


def sandbox_containers() -> tuple[list[str], list[str]]:
    """Sandbox containers, split into the healthy ones and the ones not actually running.

    A crash-looping container reports zero CPU and zero memory, which silently drags a
    cohort estimate down. Better to name it than to average it in.
    """
    result = subprocess.run(["docker", "ps", "--format", "{{.Names}}|{{.State}}", "--filter",
                             "name=xill4-sbx-"], capture_output=True, text=True, check=False)
    running, troubled = [], []
    for line in result.stdout.strip().splitlines():
        name, _, state = line.partition("|")
        (running if state == "running" else troubled).append(name)
    return running, troubled


def summarise(rows: list[dict]) -> dict[str, dict[str, float]]:
    by_container: dict[str, list[dict]] = {}
    for row in rows:
        by_container.setdefault(str(row["container"]), []).append(row)
    summary = {}
    for name, samples in sorted(by_container.items()):
        cpu = [float(s["cpu_percent"]) for s in samples]
        memory = [float(s["memory_mb"]) for s in samples]
        summary[name] = {
            "samples": len(samples),
            "cpu_mean": round(sum(cpu) / len(cpu), 2), "cpu_peak": round(max(cpu), 2),
            "memory_mean_mb": round(sum(memory) / len(memory), 1),
            "memory_peak_mb": round(max(memory), 1),
        }
    return summary


def cohort_estimate(summary: dict[str, dict[str, float]], cohort: int) -> dict[str, float]:
    """What a cohort of this size needs, sized on peaks rather than means.

    The engines scale with the cohort; MongoDB is shared and counted once, which is the
    whole reason it is not one database server per trainee.
    """
    engines = [stats for name, stats in summary.items() if name.endswith("-engine")]
    shared = [stats for name, stats in summary.items() if not name.endswith("-engine")]
    per_engine = max((stats["memory_peak_mb"] for stats in engines), default=0.0)
    per_engine_cpu = max((stats["cpu_peak"] for stats in engines), default=0.0)
    shared_memory = sum(stats["memory_peak_mb"] for stats in shared)
    return {
        "cohort": cohort,
        "measured_engines": len(engines),
        "per_engine_peak_memory_mb": round(per_engine, 1),
        "per_engine_peak_cpu_percent": round(per_engine_cpu, 2),
        "shared_peak_memory_mb": round(shared_memory, 1),
        "cohort_peak_memory_mb": round(per_engine * cohort + shared_memory, 1),
        "cohort_peak_cpu_cores": round(per_engine_cpu * cohort / 100, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="measure", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=int, default=120, help="sampling window")
    parser.add_argument("--interval", type=int, default=10, help="seconds between samples")
    parser.add_argument("--cohort", type=int, default=5,
                        help="cohort size to extrapolate to (default: 5)")
    parser.add_argument("--csv", type=Path, help="write every sample here")
    parser.add_argument("--json", type=Path, help="write the summary here")
    args = parser.parse_args(argv)

    names, troubled = sandbox_containers()
    if troubled:
        print(f"warning: not running, excluded from the measurement: {', '.join(troubled)}",
              file=sys.stderr)
    if not names:
        print("no sandbox containers are running (looked for name=xill4-sbx-)", file=sys.stderr)
        return 2

    print(f"sampling {len(names)} container(s) every {args.interval}s for {args.seconds}s")
    rows: list[dict] = []
    deadline = time.monotonic() + args.seconds
    while True:
        rows.extend(sample(names))
        if time.monotonic() >= deadline:
            break
        time.sleep(args.interval)

    summary = summarise(rows)
    estimate = cohort_estimate(summary, args.cohort)

    print(f"\n{'container':<34}{'CPU mean':>10}{'CPU peak':>10}"
          f"{'MB mean':>10}{'MB peak':>10}")
    for name, stats in summary.items():
        print(f"{name:<34}{stats['cpu_mean']:>9}%{stats['cpu_peak']:>9}%"
              f"{stats['memory_mean_mb']:>10}{stats['memory_peak_mb']:>10}")
    print(f"\na cohort of {estimate['cohort']}: "
          f"{estimate['cohort_peak_memory_mb']} MB peak memory, "
          f"{estimate['cohort_peak_cpu_cores']} CPU cores at peak "
          f"(measured from {estimate['measured_engines']} engine container(s))")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"samples written to {args.csv}")
    if args.json:
        args.json.write_text(json.dumps({"per_container": summary, "cohort": estimate},
                                        indent=2), encoding="utf-8")
        print(f"summary written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
