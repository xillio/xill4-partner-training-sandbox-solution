# Xill4 partner training sandbox

A multi-tenant sandbox for the Xill4 partner training programme: every trainee gets their
own isolated Xill4 instance and their own seeded data, works through scenarios of
increasing difficulty, and has their results recorded and graded automatically.

This repository is **Phase 0** — one scenario, end to end, proving the loop that everything
else hangs off. It runs today, without Xill4, because the grading layer is deliberately
independent of how a workspace is provisioned.

## Try it

```bash
make install     # or just: pip install PyYAML
make demo        # seed a workspace, run the reference solution, grade it
```

```
  PASS  Inventory the share  (15 pts)
  PASS  Normalise the metadata  (25 pts)
  PASS  Load the content into the target structure  (40 pts)
  PASS  Report what could not be migrated  (20 pts)

Score: 100/100 (100%)  PASSED
```

Grade a workspace nobody has touched and it scores 0/100 with every task failing. Both of
those are asserted in CI, for every scenario, on every commit — see
[docs/architecture.md](docs/architecture.md#grading).

## How one trainee's sandbox comes up

```bash
./workspace/provision.sh alice 01-legacy-fileshare   # seeds alice's own data, picks her port
cd workspace && docker compose up -d                 # her Xill4 instance
make grade WORKSPACE=.workspaces/alice/01-legacy-fileshare
```

Alice's Xill4 gets `source/` read-only and `target/` read-write. It does not get
`.expected/` — the answer key derived from her seed, which only the grader can read. Her
data is generated from `hash("alice", scenario)`, so it differs from every other trainee's
and an answer copied from a colleague scores nothing.

> The Xill4 image in `workspace/docker-compose.yml` is a placeholder. Whether Xill4 can run
> as a container is the one blocking unknown — see
> [docs/open-questions.md](docs/open-questions.md). Everything else here works regardless of
> the answer; the VM fallback changes only the provisioner.

## Layout

| Path | What it is |
| --- | --- |
| `scenarios/` | One directory per exercise: tasks, brief, seed generator, reference solution |
| `grader/` | The grading engine and its check plugins |
| `workspace/` | Per-trainee stack: compose file, provisioning script, grader image |
| `docs/` | Architecture, scenario authoring, open questions |

## Documentation

- **[Architecture](docs/architecture.md)** — the constraint that shapes the design, the
  three planes, workspace backends, how grading works and why, and the phasing.
- **[Writing a scenario](docs/scenario-authoring.md)** — the scenario format, the check
  types, and the rules a scenario must satisfy before it goes in front of a partner.
- **[Open questions](docs/open-questions.md)** — the decisions that belong to Xillio.

## Commands

| Command | |
| --- | --- |
| `make test` | full suite, including the per-scenario grading invariants |
| `make lint` | ruff |
| `make demo` | seed, solve and grade in one go |
| `make grade WORKSPACE=…` | grade a workspace as the "Check my work" button does |

`make grade` exits non-zero when a workspace has not passed. That is intentional — it is
what makes the same command usable from CI.
