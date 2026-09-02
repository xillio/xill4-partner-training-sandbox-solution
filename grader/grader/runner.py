"""Run a scenario's checks against one trainee workspace and produce a gradeable report."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from grader.checks import Outcome, get_check
from grader.context import Context
from grader.models import Scenario, Task


@dataclass
class CheckReport:
    id: str
    type: str
    description: str
    passed: bool
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class TaskReport:
    id: str
    title: str
    weight: int
    passed: bool
    checks: list[CheckReport] = field(default_factory=list)
    hint: str = ""


@dataclass
class ScenarioReport:
    scenario_id: str
    title: str
    graded_at: str
    passed: bool
    score: int
    max_score: int
    tasks: list[TaskReport] = field(default_factory=list)
    trainee_id: str = ""

    @property
    def percentage(self) -> int:
        return round(100 * self.score / self.max_score) if self.max_score else 0

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "percentage": self.percentage}


def _run_check(spec, ctx: Context) -> CheckReport:
    started = time.perf_counter()
    try:
        outcome = get_check(spec.type)(spec.params, ctx)
    except KeyError as exc:
        # An unknown check type is an authoring bug. CI catches it; if one ever reaches a
        # trainee it must fail loudly rather than silently award the task.
        outcome = Outcome(False, str(exc), {"error": "unknown_check_type"})
    except Exception as exc:
        outcome = Outcome(False, f"check raised {type(exc).__name__}: {exc}",
                          {"error": type(exc).__name__})

    message = outcome.message
    if not outcome.passed and spec.on_fail:
        message = f"{message} -- {spec.on_fail}"

    return CheckReport(
        id=spec.id,
        type=spec.type,
        description=spec.description,
        passed=outcome.passed,
        message=message,
        evidence=outcome.evidence,
        duration_ms=round((time.perf_counter() - started) * 1000),
    )


def _run_task(task: Task, ctx: Context) -> TaskReport:
    # Every check runs even after the first failure: a trainee should see the whole
    # picture of what is wrong, not fix one thing and rediscover the next.
    checks = [_run_check(spec, ctx) for spec in task.checks]
    passed = all(check.passed for check in checks)
    return TaskReport(
        id=task.id,
        title=task.title,
        weight=task.weight,
        passed=passed,
        checks=checks,
        hint="" if passed else task.hint,
    )


def run_scenario(scenario: Scenario, ctx: Context, trainee_id: str = "") -> ScenarioReport:
    """Grade a workspace. Scoring is all-or-nothing per task, weighted across tasks."""
    missing = [name for name in scenario.requires_vars if name not in ctx.vars]
    if missing:
        raise KeyError(
            f"scenario {scenario.id!r} requires workspace variable(s) "
            f"{', '.join(missing)}, which the context does not provide"
        )

    tasks = [_run_task(task, ctx) for task in scenario.tasks]
    score = sum(task.weight for task in tasks if task.passed)
    return ScenarioReport(
        scenario_id=scenario.id,
        title=scenario.title,
        graded_at=datetime.now(UTC).isoformat(timespec="seconds"),
        passed=all(task.passed for task in tasks),
        score=score,
        max_score=scenario.total_weight,
        tasks=tasks,
        trainee_id=trainee_id,
    )
