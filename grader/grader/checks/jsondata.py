"""JSON checks -- for manifests, job reports and metadata exports produced by a migration."""

from __future__ import annotations

import json
from typing import Any

from grader.checks import Outcome, check, compare_number, resolve_value
from grader.context import Context


class QueryError(ValueError):
    """The scenario asked for a path that cannot be evaluated against this document."""


def query(document: Any, expression: str) -> Any:
    """Evaluate a small dotted path against a JSON document.

    Supports `a.b.c`, list indexing `items[0]`, and the length suffix `items[]`, which is
    deliberately all the power a scenario author needs -- richer queries belong in a
    purpose-built check where the failure message can explain itself.
    """
    current = document
    for raw in expression.split("."):
        if not raw:
            raise QueryError(f"empty segment in query {expression!r}")
        name, _, index = raw.partition("[")
        if name:
            if not isinstance(current, dict) or name not in current:
                raise QueryError(f"{expression!r}: no key {name!r} at this level")
            current = current[name]
        if not _:
            continue
        if not index.endswith("]"):
            raise QueryError(f"{expression!r}: unclosed [ in segment {raw!r}")
        index = index[:-1]
        if not isinstance(current, list):
            raise QueryError(f"{expression!r}: {name or 'value'} is not a list")
        current = len(current) if index == "" else current[int(index)]
    return current


@check("json.assert")
def json_assert(params: dict[str, Any], ctx: Context) -> Outcome:  # noqa: PLR0911
    """Assert on values inside a JSON file.

    Params: path, queries -- a list of {query, equals|min|max|contains}. Every query must
    hold for the check to pass; the message names the first that does not.
    """
    target = ctx.path(params["path"])
    if not target.is_file():
        return Outcome(False, f"{target} is missing", {"path": str(target)})

    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Outcome(False, f"{target.name} is not valid JSON: {exc}", {"path": str(target)})

    evidence: dict[str, Any] = {"path": str(target), "results": {}}
    for spec in ctx.expand(params["queries"]):
        expression = spec["query"]
        try:
            value = query(document, expression)
        except (QueryError, IndexError, ValueError) as exc:
            return Outcome(False, f"{target.name}: {exc}", evidence)
        evidence["results"][expression] = value

        if "contains" in spec:
            wanted = resolve_value(spec["contains"], ctx)
            haystack = value if isinstance(value, (list, str)) else []
            if wanted not in haystack:
                return Outcome(False, f"{target.name}: {expression} does not contain "
                               f"{wanted!r}", evidence)
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if "equals" not in spec:
                return Outcome(False, f"{target.name}: {expression} is not a number, so only "
                               "'equals' can be checked", evidence)
            wanted = resolve_value(spec["equals"], ctx)
            if value != wanted:
                return Outcome(False, f"{target.name}: {expression} is {value!r}, expected "
                               f"{wanted!r}", evidence)
            continue

        numeric = compare_number(value, spec, f"{target.name}: {expression}", ctx)
        if not numeric.passed:
            return Outcome(False, numeric.message, evidence)

    return Outcome(True, f"{target.name}: all {len(params['queries'])} assertions hold", evidence)
