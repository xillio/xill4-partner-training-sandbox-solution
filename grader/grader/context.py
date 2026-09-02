"""Grading context: the trainee's workspace, plus the variables checks resolve against.

Checks never hardcode paths. They reference ${VARS} that the control plane fills in per
trainee, so one scenario grades many isolated workspaces.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class MissingVariable(KeyError):
    """A check referenced a workspace variable that was not supplied."""


@dataclass
class Context:
    """Everything a check needs to inspect one trainee's workspace.

    `vars` holds both trainee-visible locations (SOURCE, TARGET) and grader-only ones
    (EXPECTED -- the answer key derived from the trainee's seed). Keeping the answer key
    in the context rather than in the scenario file is what lets every trainee get
    different seed data while sharing one set of checks.
    """

    workspace: Path
    vars: dict[str, str] = field(default_factory=dict)
    scenario_dir: Path | None = None

    @classmethod
    def from_env(cls, workspace: str | Path, extra: dict[str, str] | None = None) -> Context:
        """Build a context from SANDBOX_* environment variables plus explicit overrides."""
        workspace = Path(workspace).resolve()
        variables = {
            key.removeprefix("SANDBOX_"): value
            for key, value in os.environ.items()
            if key.startswith("SANDBOX_")
        }
        variables.setdefault("WORKSPACE", str(workspace))
        variables.update(extra or {})
        return cls(workspace=workspace, vars=variables)

    def expand(self, value: Any) -> Any:
        """Recursively substitute ${VAR} references in strings, lists and mappings."""
        if isinstance(value, str):
            return _VAR.sub(self._lookup, value)
        if isinstance(value, list):
            return [self.expand(item) for item in value]
        if isinstance(value, dict):
            return {key: self.expand(item) for key, item in value.items()}
        return value

    def _lookup(self, match: re.Match[str]) -> str:
        name = match.group(1)
        try:
            return self.vars[name]
        except KeyError:
            raise MissingVariable(
                f"workspace variable ${{{name}}} is not set "
                f"(known: {', '.join(sorted(self.vars)) or 'none'})"
            ) from None

    def path(self, value: str) -> Path:
        """Expand a path parameter, resolving relative paths against the workspace."""
        expanded = Path(self.expand(value))
        return expanded if expanded.is_absolute() else self.workspace / expanded
