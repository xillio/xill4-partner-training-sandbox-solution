# Developer entry points. The control plane calls the same commands in production.
WORKSPACE ?= .workspaces/demo
SEED      ?= demo:01
SCENARIO  ?= scenarios/01-legacy-fileshare

.PHONY: help install test lint seed solve grade demo clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

install:  ## install the grader and its dev dependencies
	python3 -m pip install -e ".[dev]"

test:  ## run the full test suite, including the per-scenario grading invariants
	python3 -m pytest

lint:  ## static checks
	python3 -m ruff check .

seed:  ## generate one trainee workspace (WORKSPACE=... SEED=...)
	python3 $(SCENARIO)/seedgen.py --workspace $(WORKSPACE) --seed "$(SEED)" --force

solve:  ## run the reference solution against that workspace
	python3 $(SCENARIO)/solution/solve.py --workspace $(WORKSPACE)

grade:  ## grade the workspace exactly as the "Check my work" button does
	PYTHONPATH=grader python3 -m grader $(SCENARIO) \
		--workspace $(WORKSPACE) --json $(WORKSPACE)/report.json

demo:  ## prove the whole loop in one command -- works without make too
	python3 demo.py

clean:
	rm -rf .workspaces .pytest_cache **/__pycache__
