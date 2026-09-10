# Developer entry points. The control plane calls the same commands in production.
WORKSPACE ?= .workspaces/demo
SEED      ?= demo:01
SCENARIO  ?= scenarios/01-legacy-fileshare
TRAINEE   ?= demo
SECONDS   ?= 120
COHORT    ?= 5

.PHONY: help install test lint seed solve grade demo clean \
        platform-up platform-down platform-status provision preflight measure

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

platform-up:  ## start the shared MongoDB every trainee's Xill4 keeps its flows in
	./workspace/platform.sh up

platform-down:  ## stop it (trainee data survives in the volume)
	./workspace/platform.sh down

platform-status:  ## what is running, and how much each trainee's database holds
	./workspace/platform.sh status

provision:  ## provision one trainee's sandbox (TRAINEE=alice [SCENARIO=...])
	./workspace/provision.sh $(TRAINEE) $(notdir $(SCENARIO))

preflight:  ## prove one real Xill4 container works, on a host that reaches the registry
	python3 workspace/preflight.py --json preflight-report.json

measure:  ## sample what the running sandboxes cost (SECONDS=300 COHORT=5)
	python3 workspace/measure.py --seconds $(SECONDS) --cohort $(COHORT) \
		--json measurement.json

clean:
	rm -rf .workspaces .pytest_cache **/__pycache__
