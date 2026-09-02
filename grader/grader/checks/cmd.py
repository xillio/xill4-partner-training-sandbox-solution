"""Command check -- the escape hatch, and the home of holdout grading.

Running a hidden input through whatever pipeline the trainee built is the strongest
signal available: it shows the migration generalises instead of having been hand-fixed
for the records the trainee could see.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from typing import Any

from grader.checks import Outcome, check
from grader.context import Context

_DEFAULT_TIMEOUT = 300


@check("cmd.run")
def run(params: dict[str, Any], ctx: Context) -> Outcome:
    """Params: command (string or list), cwd, expect_exit_code, stdout_matches, timeout."""
    command = ctx.expand(params["command"])
    argv = shlex.split(command) if isinstance(command, str) else [str(a) for a in command]
    cwd = ctx.path(params["cwd"]) if "cwd" in params else ctx.workspace
    expected_code = params.get("expect_exit_code", 0)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    try:
        completed = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except FileNotFoundError:
        return Outcome(False, f"command not found: {argv[0]}", {"command": argv})
    except subprocess.TimeoutExpired:
        return Outcome(False, f"command timed out after {timeout}s", {"command": argv})

    evidence = {
        "command": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    if completed.returncode != expected_code:
        return Outcome(False, f"exited {completed.returncode}, expected {expected_code}", evidence)

    pattern = ctx.expand(params.get("stdout_matches", ""))
    if pattern and not re.search(pattern, completed.stdout, re.MULTILINE):
        return Outcome(False, f"output did not match /{pattern}/", evidence)

    return Outcome(True, f"{argv[0]} completed as expected", evidence)
