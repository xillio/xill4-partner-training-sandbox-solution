# Xill4 partner training sandbox

A multi-tenant sandbox for the Xill4 partner training programme: every trainee gets their
own isolated Xill4 instance and their own seeded data, works through scenarios of
increasing difficulty, and has their results recorded and graded automatically.

This repository is **Phase 0** — one scenario, end to end, proving the loop that everything
else hangs off. It runs today, without Xill4, because the grading layer is deliberately
independent of how a workspace is provisioned.

## Where to run this

Everything below runs on **your own laptop** — macOS, Windows or Linux — in a terminal
(Terminal, PowerShell, or the Claude Desktop app's built-in terminal). You need two things:

- **Python 3.11 or newer** — check with `python --version` (or `python3 --version`)
- **PyYAML** — `pip install PyYAML`

You do not need Docker, Xill4, an Azure subscription, `make`, or a Unix shell. Nothing here
touches the network.

The grader and `demo.py` are tested on Windows and Linux in CI. Two files in this repo are
Unix-only and not needed to try anything: `workspace/provision.sh` (bash) and the `Makefile`
(needs `make`). On Windows use `python demo.py` and the commands under
[Running the pieces separately](#running-the-pieces-separately).

To get the code: clone this repository if you have access, or, if you were sent
`xill4-sandbox-phase0.bundle`, save that file and clone from it directly — a bundle is a
complete repository in one file:

```
git clone xill4-sandbox-phase0.bundle xill4-sandbox
cd xill4-sandbox
```

## Try it

One command, on any OS:

```
python demo.py
```

It seeds a trainee workspace, grades it untouched, runs the reference solution, grades it
again, then breaks two values the way a real trainee would and grades a third time —
printing what each step proves. It exits non-zero if any claim below fails to hold.

```
1. Seed one trainee's workspace          24 files on the share
2. Grade it before anyone has worked       0/100   every task failed
3. Run the reference solution            100/100   PASSED
4. Break two values                       75/100   only the transform task lost
5. Seed a second trainee                  different data, same defects
```

Step 4 is the one worth reading closely, because it is the claim everything rests on:

```
  FAIL  Normalise the metadata  (25 pts)
      ! metadata.csv: 2 incorrect value(s) -- dates must be ISO-8601 and
        departments must be one of the four canonical values.
```

and `report.json` names them:

```json
{"key": "acme-migration-plan-2016", "column": "created",
 "expected": "2016-04-03", "actual": "04/03/2019"}
```

The workspaces are left in `.workspaces/` so you can open the generated file share and the
graded output yourself. `python demo.py --clean` removes them.

### Running the pieces separately

```
python -m pytest                                          # 58 tests
python scenarios/01-legacy-fileshare/seedgen.py --workspace ws/alice --seed alice:01
python scenarios/01-legacy-fileshare/solution/solve.py --workspace ws/alice
python -m grader scenarios/01-legacy-fileshare --workspace ws/alice
```

The grader assumes the conventional layout — `source/`, `target/` and `.expected/` inside
the workspace — so no paths need passing. Override any of them with `--var NAME=VALUE`
when a workspace is laid out differently. On Windows, prefix the grader command with
`set PYTHONPATH=grader` (cmd) or `$env:PYTHONPATH="grader"` (PowerShell), or run
`pip install -e .` once and use the installed `grader` command instead.

## How one trainee's sandbox comes up

Xill4 ships an official Linux image, so a trainee's sandbox is a container rather than a VM.
It keeps its projects and flows in MongoDB, not on disk, so a trainee's state has two halves
and both are provisioned — and reset — together.

```bash
docker login docker.cloudsmith.io -u 'xillio/xill4'  # password: the entitlement token
make platform-up                                     # the shared MongoDB, once per host
./workspace/provision.sh alice 01-legacy-fileshare   # alice's data, database, port
cd workspace && docker compose --env-file .env.platform --env-file .env.alice up -d
make grade WORKSPACE=.workspaces/alice/01-legacy-fileshare
```

Alice's Xill4 gets `source/` read-only and `target/` read-write. It does not get
`.expected/` — the answer key derived from her seed, which only the grader can read. Her
data is generated from `hash("alice", scenario)`, so it differs from every other trainee's
and an answer copied from a colleague scores nothing. Her flows live in `xill4_alice`, which
her credentials — and only hers — can read.

`./workspace/provision.sh alice 01-legacy-fileshare --reset` starts her over: reseeded data
*and* an empty database. Without `--reset` her flows survive, which is what you want between
attempts.

### Before the first cohort, on the host that will run it

```
make preflight        # writes preflight-report.json
```

One command that pulls the real image, starts one instance, and answers what the compose
file still has to guess: which uid it runs as (and therefore whether it can write the
mounted `target/`), which URL answers a healthcheck, whether the trainee's scoped database
credentials really hold its state, and what one container costs. It provisions a throwaway
trainee and removes it again. Everything it finds is in the report; the two values it asks
you to copy into `.env.platform` are printed at the end.

`make measure SECONDS=300` samples the running cohort and extrapolates — run it while
trainees are working, because an idle container is the floor, not the cost.

## Layout

| Path | What it is |
| --- | --- |
| `scenarios/` | One directory per exercise: tasks, brief, seed generator, reference solution |
| `grader/` | The grading engine and its check plugins |
| `workspace/` | The stack: compose files, provisioning, preflight, measurement |
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
| `python demo.py` | prove the whole loop, on any OS, without make |
| `make platform-up` | start the shared MongoDB the trainee instances need |
| `make preflight` | prove one real Xill4 container works, and report what it costs |
| `make measure` | sample what the running sandboxes consume |
| `make test` | full suite, including the per-scenario grading invariants |
| `make lint` | ruff |
| `make grade WORKSPACE=…` | grade a workspace as the "Check my work" button does |

`make grade` exits non-zero when a workspace has not passed. That is intentional — it is
what makes the same command usable from CI.
