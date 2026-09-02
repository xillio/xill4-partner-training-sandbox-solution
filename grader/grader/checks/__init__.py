"""Check plugins.

A check answers one question about the state of a trainee's workspace and returns
evidence for its verdict. Checks assert on *outcomes* -- what ended up in the target
system -- not on how the trainee got there, so there is always more than one valid way
to solve a task.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from grader.context import Context


@dataclass
class Outcome:
    passed: bool
    message: str
    # Structured detail shown to the trainee and stored with the attempt, so a failure
    # can be understood without re-running anything.
    evidence: dict[str, Any] = field(default_factory=dict)


CheckFn = Callable[[dict[str, Any], Context], Outcome]

_REGISTRY: dict[str, CheckFn] = {}


def check(type_name: str) -> Callable[[CheckFn], CheckFn]:
    def register(fn: CheckFn) -> CheckFn:
        if type_name in _REGISTRY:
            raise RuntimeError(f"check type {type_name!r} is already registered")
        _REGISTRY[type_name] = fn
        return fn

    return register


def get_check(type_name: str) -> CheckFn:
    try:
        return _REGISTRY[type_name]
    except KeyError:
        raise KeyError(
            f"unknown check type {type_name!r} (available: {', '.join(sorted(_REGISTRY))})"
        ) from None


def registered_types() -> list[str]:
    return sorted(_REGISTRY)


def resolve_value(value: Any, ctx: Context) -> Any:
    """Resolve a scenario parameter, following `{from: <json file>, query: <path>}` references.

    Expected values are usually not constants: they are facts about the trainee's own seed
    data. A reference lets one scenario file grade every trainee's distinct workspace.
    """
    if isinstance(value, dict) and "from" in value:
        from grader.checks.jsondata import query  # noqa: PLC0415 -- avoids a circular import

        document = json.loads(ctx.path(value["from"]).read_text(encoding="utf-8"))
        return query(document, value.get("query", ""))
    return ctx.expand(value)


def compare_number(actual: int, params: dict[str, Any], label: str, ctx: Context) -> Outcome:
    """Shared equals/min/max comparison used by the counting checks."""
    constraints = {key: resolve_value(params[key], ctx)
                   for key in ("equals", "min", "max") if key in params}
    if not constraints:
        raise ValueError(f"{label}: needs one of equals, min or max")

    failures = []
    if "equals" in constraints and actual != constraints["equals"]:
        failures.append(f"expected exactly {constraints['equals']}")
    if "min" in constraints and actual < constraints["min"]:
        failures.append(f"expected at least {constraints['min']}")
    if "max" in constraints and actual > constraints["max"]:
        failures.append(f"expected at most {constraints['max']}")

    if failures:
        return Outcome(False, f"{label}: found {actual}, {'; '.join(failures)}",
                       {"actual": actual, **constraints})
    return Outcome(True, f"{label}: found {actual}", {"actual": actual, **constraints})


# Importing the modules is what populates the registry.
from grader.checks import cmd, csvdata, fs, jsondata, s3  # noqa: F401
