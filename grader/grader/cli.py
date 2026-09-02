"""Command line entry point: `python -m grader <scenario> --workspace <dir>`.

Trainees run this behind a "Check my work" button; CI runs the same command against a
scenario's reference solution.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from grader.context import Context
from grader.models import ScenarioError, load_scenario
from grader.runner import ScenarioReport, run_scenario

_TICK, _CROSS = "PASS", "FAIL"


def _parse_var(pair: str) -> tuple[str, str]:
    name, sep, value = pair.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {pair!r}")
    return name, value


def render(report: ScenarioReport) -> str:
    lines = [f"{report.title}  [{report.scenario_id}]", ""]
    for task in report.tasks:
        status = _TICK if task.passed else _CROSS
        lines.append(f"  {status}  {task.title}  ({task.weight} pts)")
        for check in task.checks:
            marker = " " if check.passed else "!"
            lines.append(f"      {marker} {check.message}")
        if task.hint:
            lines.append(f"      hint: {task.hint}")
    lines += ["", f"Score: {report.score}/{report.max_score} ({report.percentage}%)  "
                  f"{'PASSED' if report.passed else 'NOT YET PASSED'}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grader", description=__doc__)
    parser.add_argument("scenario", help="path to a scenario directory or scenario.yaml")
    parser.add_argument("--workspace", required=True, help="the trainee's workspace root")
    parser.add_argument("--var", action="append", type=_parse_var, default=[],
                        metavar="NAME=VALUE", help="workspace variable (repeatable)")
    parser.add_argument("--trainee", default="", help="trainee id recorded in the report")
    parser.add_argument("--json", type=Path, help="also write the full report here")
    args = parser.parse_args(argv)

    try:
        scenario = load_scenario(args.scenario)
    except (ScenarioError, OSError) as exc:
        print(f"grader: {exc}", file=sys.stderr)
        return 2

    ctx = Context.from_env(args.workspace, extra=dict(args.var))
    ctx.scenario_dir = scenario.source_dir
    try:
        report = run_scenario(scenario, ctx, trainee_id=args.trainee)
    except KeyError as exc:
        print(f"grader: {exc}", file=sys.stderr)
        return 2

    print(render(report))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
