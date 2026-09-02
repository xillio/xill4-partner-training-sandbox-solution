"""Scenario loading and grading semantics.

Authoring mistakes must fail loudly in CI, and a broken check must never silently award
points to a trainee who has not earned them.
"""

import textwrap

import pytest
from grader.checks import Outcome, check
from grader.context import Context
from grader.models import ScenarioError, load_scenario
from grader.runner import run_scenario

VALID = """
id: demo
title: Demo
level: 1
tasks:
  - id: only
    title: Only task
    weight: 100
    checks:
      - id: c1
        type: fs.exists
        params: {path: "does-not-exist"}
"""


def write(tmp_path, body):
    path = tmp_path / "scenario.yaml"
    path.write_text(textwrap.dedent(body))
    return path


def test_loads_a_valid_scenario(tmp_path):
    scenario = load_scenario(write(tmp_path, VALID))
    assert scenario.id == "demo" and scenario.total_weight == 100


def test_a_directory_resolves_to_its_scenario_file(tmp_path):
    write(tmp_path, VALID)
    assert load_scenario(tmp_path).id == "demo"


@pytest.mark.parametrize("mutation,message", [
    (lambda s: s.replace("  - id: only\n", "  - title: Only task\n"), "missing required key"),
    (lambda s: s.replace("weight: 100", "weight: 0"), "positive integer"),
    (lambda s: s.replace("level: 1", "level: 0"), "positive integer"),
    (lambda s: s.replace("tasks:", "tasks: []\nunused:"), "non-empty list of tasks"),
    (lambda s: s + "\n  - id: only\n    title: Dup\n    weight: 1\n"
                   "    checks: [{id: c1, type: fs.exists, params: {path: x}}]",
     "duplicate task id"),
])
def test_rejects_malformed_scenarios(tmp_path, mutation, message):
    with pytest.raises(ScenarioError, match=message):
        load_scenario(write(tmp_path, mutation(VALID)))


def test_rejects_invalid_yaml(tmp_path):
    with pytest.raises(ScenarioError, match="invalid YAML"):
        load_scenario(write(tmp_path, "id: [unclosed\n"))


def test_missing_workspace_variable_is_an_error_not_a_zero(tmp_path):
    scenario = load_scenario(write(tmp_path, VALID + "\nrequires_vars: [TARGET]\n"))
    with pytest.raises(KeyError, match="TARGET"):
        run_scenario(scenario, Context(tmp_path, {}))


def test_unknown_check_type_fails_the_task(tmp_path):
    scenario = load_scenario(write(tmp_path, VALID.replace("fs.exists", "fs.nonsense")))
    report = run_scenario(scenario, Context(tmp_path, {}))

    assert not report.passed and report.score == 0
    assert report.tasks[0].checks[0].evidence["error"] == "unknown_check_type"


def test_a_raising_check_fails_rather_than_aborting_the_run(tmp_path):
    @check("test.explodes")
    def explodes(params, ctx):
        raise RuntimeError("boom")

    scenario = load_scenario(write(tmp_path, VALID.replace("fs.exists", "test.explodes")))
    report = run_scenario(scenario, Context(tmp_path, {}))

    assert not report.passed
    assert "boom" in report.tasks[0].checks[0].message


def test_on_fail_guidance_is_appended_only_to_failures(tmp_path):
    body = VALID.replace('params: {path: "does-not-exist"}',
                         'params: {path: "does-not-exist"}\n        on_fail: try harder')
    report = run_scenario(load_scenario(write(tmp_path, body)), Context(tmp_path, {}))
    assert report.tasks[0].checks[0].message.endswith("try harder")


def test_report_serialises_with_a_percentage(tmp_path):
    report = run_scenario(load_scenario(write(tmp_path, VALID)), Context(tmp_path, {}))
    assert report.to_dict()["percentage"] == 0
    assert report.to_dict()["tasks"][0]["checks"][0]["type"] == "fs.exists"


def test_all_checks_run_even_after_the_first_failure(tmp_path):
    body = VALID + """
      - id: c2
        type: fs.exists
        params: {path: "also-missing"}
"""
    report = run_scenario(load_scenario(write(tmp_path, body)), Context(tmp_path, {}))
    assert [c.id for c in report.tasks[0].checks] == ["c1", "c2"]


def test_registering_a_duplicate_check_type_is_refused():
    with pytest.raises(RuntimeError, match="already registered"):
        check("fs.exists")(lambda params, ctx: Outcome(True, ""))
