"""Scenario model: the declarative description of an exercise and how it is graded.

A scenario is authored as YAML and reviewed like code. Nothing in here knows how a
workspace is provisioned -- that is deliberate, so the same scenarios grade the same
way whether a trainee's Xill4 instance lives on a VM or in a container.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ScenarioError(ValueError):
    """Raised when a scenario file is malformed. Surfaced in CI, never to a trainee."""


@dataclass(frozen=True)
class CheckSpec:
    id: str
    type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    # Feedback shown to the trainee when this check fails. Written by the scenario
    # author so failures teach rather than just report.
    on_fail: str = ""


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    weight: int
    checks: tuple[CheckSpec, ...]
    hint: str = ""


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    level: int
    tasks: tuple[Task, ...]
    prerequisites: tuple[str, ...] = ()
    brief: str = "brief.md"
    timebox_minutes: int | None = None
    # Workspace variables the scenario expects; the runner fails fast if one is missing
    # rather than silently grading against an empty path.
    requires_vars: tuple[str, ...] = ()
    source_dir: Path | None = None

    @property
    def total_weight(self) -> int:
        return sum(task.weight for task in self.tasks)


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ScenarioError(f"{where}: missing required key {key!r}")
    return data[key]


def _parse_check(data: Any, where: str) -> CheckSpec:
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: each check must be a mapping, got {type(data).__name__}")
    return CheckSpec(
        id=str(_require(data, "id", where)),
        type=str(_require(data, "type", where)),
        description=str(data.get("description", "")),
        params=dict(data.get("params") or {}),
        on_fail=str(data.get("on_fail", "")),
    )


def _parse_task(data: Any, where: str) -> Task:
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: each task must be a mapping, got {type(data).__name__}")
    task_id = str(_require(data, "id", where))
    where = f"{where} task {task_id!r}"

    weight = _require(data, "weight", where)
    if not isinstance(weight, int) or weight <= 0:
        raise ScenarioError(f"{where}: weight must be a positive integer, got {weight!r}")

    raw_checks = _require(data, "checks", where)
    if not isinstance(raw_checks, list) or not raw_checks:
        raise ScenarioError(f"{where}: needs a non-empty list of checks")
    checks = tuple(_parse_check(c, where) for c in raw_checks)
    _reject_duplicates([c.id for c in checks], f"{where}: duplicate check id")

    return Task(
        id=task_id,
        title=str(_require(data, "title", where)),
        weight=weight,
        checks=checks,
        hint=str(data.get("hint", "")),
    )


def _reject_duplicates(ids: list[str], message: str) -> None:
    seen: set[str] = set()
    for value in ids:
        if value in seen:
            raise ScenarioError(f"{message}: {value!r}")
        seen.add(value)


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario.yaml. Raises ScenarioError with an actionable message."""
    path = Path(path)
    if path.is_dir():
        path = path / "scenario.yaml"
    where = str(path)

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{where}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioError(f"{where}: top level must be a mapping")

    raw_tasks = _require(data, "tasks", where)
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ScenarioError(f"{where}: needs a non-empty list of tasks")
    tasks = tuple(_parse_task(t, where) for t in raw_tasks)
    _reject_duplicates([t.id for t in tasks], f"{where}: duplicate task id")

    level = data.get("level", 1)
    if not isinstance(level, int) or level < 1:
        raise ScenarioError(f"{where}: level must be a positive integer, got {level!r}")

    return Scenario(
        id=str(_require(data, "id", where)),
        title=str(_require(data, "title", where)),
        level=level,
        tasks=tasks,
        prerequisites=tuple(str(p) for p in data.get("prerequisites") or ()),
        brief=str(data.get("brief", "brief.md")),
        timebox_minutes=data.get("timebox_minutes"),
        requires_vars=tuple(str(v) for v in data.get("requires_vars") or ()),
        source_dir=path.parent,
    )
