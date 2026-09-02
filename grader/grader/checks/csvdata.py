"""CSV checks -- metadata mappings and exception reports are the usual shape of these."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from grader.checks import Outcome, check
from grader.context import Context

_MAX_REPORTED = 5


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


@check("csv.matches")
def csv_matches(params: dict[str, Any], ctx: Context) -> Outcome:
    """Compare a CSV the trainee produced against an expected CSV, keyed by one column.

    Params: path, expected (normally a grader-only file derived from the seed), key,
    columns (subset to compare; defaults to every column in the expected file).

    Row order is ignored on purpose: a migration is judged on the records it produced,
    not the order a job happened to emit them in.
    """
    actual_path = ctx.path(params["path"])
    expected_path = ctx.path(params["expected"])
    key = ctx.expand(params["key"])

    if not actual_path.is_file():
        return Outcome(False, f"{actual_path} is missing", {"path": str(actual_path)})

    expected_rows = _read_rows(expected_path)
    actual_rows = _read_rows(actual_path)
    columns = list(ctx.expand(params.get("columns")) or (expected_rows[0].keys() if expected_rows
                                                         else []))

    missing_columns = [c for c in [key, *columns] if actual_rows and c not in actual_rows[0]]
    if missing_columns:
        return Outcome(False, f"{actual_path.name} is missing column(s): "
                       f"{', '.join(missing_columns)}",
                       {"expected_columns": [key, *columns],
                        "actual_columns": list(actual_rows[0]) if actual_rows else []})

    expected_by_key = {row[key]: row for row in expected_rows}
    actual_by_key = {row[key]: row for row in actual_rows}

    missing = sorted(set(expected_by_key) - set(actual_by_key))
    unexpected = sorted(set(actual_by_key) - set(expected_by_key))
    wrong = [
        {"key": k, "column": c, "expected": expected_by_key[k][c], "actual": actual_by_key[k][c]}
        for k in sorted(set(expected_by_key) & set(actual_by_key))
        for c in columns
        if expected_by_key[k].get(c, "") != actual_by_key[k].get(c, "")
    ]

    evidence = {
        "expected_rows": len(expected_rows),
        "actual_rows": len(actual_rows),
        "missing_rows": missing[:_MAX_REPORTED],
        "unexpected_rows": unexpected[:_MAX_REPORTED],
        "wrong_values": wrong[:_MAX_REPORTED],
    }
    problems = [
        f"{len(missing)} row(s) missing" if missing else "",
        f"{len(unexpected)} row(s) that should not be there" if unexpected else "",
        f"{len(wrong)} incorrect value(s)" if wrong else "",
    ]
    problems = [p for p in problems if p]
    if problems:
        return Outcome(False, f"{actual_path.name}: {', '.join(problems)}", evidence)
    return Outcome(True, f"{actual_path.name}: all {len(expected_rows)} rows correct", evidence)
