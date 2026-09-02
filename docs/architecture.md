# Architecture

## The constraint everything else follows from

Xill4 is a server product, and a Xill4 instance is effectively single-occupancy: partner
training servers today allow one or two logins, and two trainees working at the same time
on one instance interfere with each other. So the sandbox cannot be "one Xill4 with many
users". It has to be **N isolated instances, one per trainee**, provisioned and reclaimed
on demand.

That is the hard part. Grading, progression and reporting are comparatively easy, and they
should not be entangled with it.

## Three planes

```
  Control plane            Scenario plane              Workspace plane
  ─────────────            ──────────────              ───────────────
  who is enrolled          scenario.yaml               a Xill4 instance
  which scenario is next   brief.md                    source/ + target/
  attempts, scores, time   seedgen.py                  stand-in target systems
  trainer dashboard        checks                      one per trainee
        │                        │                            │
        └──── asks ──────────────┴──────── inspects ──────────┘
                            grader (this repo)
```

The grader is the seam. It takes a workspace path plus a handful of variables and returns a
scored report. It has no idea whether that workspace is a directory on a VM, a Docker
volume, or a bucket. **This is deliberate**: the workspace backend is the part most likely
to change once we know what Xill4 supports, and we do not want that change to invalidate a
single scenario or check.

## Workspace backends

Provisioning is behind one interface — "give me an isolated Xill4 with these volumes
mounted, and tell me how to reach it". Three implementations are plausible:

| Backend | Fits when | Cost per trainee | Reset time | Status |
| --- | --- | --- | --- | --- |
| **VM per trainee** | Xill4 only installs onto a full OS (likely Windows) | One VM, always | Minutes (redeploy) | Works today, safe fallback |
| **Container per trainee** | Xill4 can run headless on Linux | A slice of one host | Seconds | Target state |
| **Pooled desktop** | Trainees need the Xill IDE, not just the engine | AVD session host slice | Minutes | Only if the IDE is required |

The recommendation is to **build against the container backend and keep the VM backend as
the fallback**, because the whole economics of the sandbox change with it: 10 containers on
one host instead of 10 VMs, and a reset that takes seconds instead of a redeploy. Whether
that is available is the one genuinely blocking unknown — see
[open-questions.md](open-questions.md).

Nothing in `scenarios/` or `grader/` depends on the answer.

## What a workspace contains

```
<workspace>/
  source/      mounted read-only into the trainee's Xill4  -- the legacy system
  target/      mounted read-write                          -- where the migration lands
  .expected/   mounted nowhere                             -- the grader's answer key
```

`.expected/` sitting outside every mount is the entire isolation mechanism for grading. The
trainee's instance cannot read it; the grader, which runs in its own container on the host
side, can. No secrets in the trainee's reach, no obfuscation needed.

## Grading

Four decisions, and each buys something specific.

**Grade outcomes, not keystrokes.** A check asserts on what ended up in the target system,
never on which Xill4 constructs the trainee used. Two trainees can solve a scenario
differently and both score 100. This is what makes the sandbox teach migration rather than
teach button order — and it means scenarios survive Xill4 UI changes.

**Seed per trainee.** Every workspace is generated from `hash(trainee_id, scenario_id)`.
Trainees get structurally identical, textually different data: the same *kinds* of dirty
records in different rows. Expected values are therefore not constants in the scenario file;
checks reference facts derived from the trainee's own seed
(`equals: {from: "${EXPECTED}/facts.json", query: files_on_share}`). One scenario, N answer
keys, and a copied answer scores zero.

**Fail loudly, never silently pass.** An unknown check type, a raising check, a missing
workspace variable — all fail the task or abort the run with a named error. The one thing a
grader must never do is award points because it could not tell.

**Every scenario carries a reference solution, and CI runs it.** Two invariants are asserted
for every scenario on every commit:

- the reference solution scores 100/100
- an untouched workspace scores 0/100, with every task failing

A check suite that only satisfies the first grades nothing. Both together are what makes a
scenario safe to put in front of a paying partner. See
`grader/tests/test_scenario_01.py`.

## Recording and progression

The grader emits a JSON report per run; the control plane stores it. That gives the trainer,
without any extra instrumentation:

- score and per-task breakdown, with the evidence behind each verdict
- number of attempts before first pass, and time to first pass
- which task in which scenario a cohort gets stuck on — the signal that says the *material*
  needs work, not the trainee

Progression is a prerequisite graph: `prerequisites: [01-legacy-fileshare]` in a
`scenario.yaml` unlocks the next level once the previous one passes. Levels are emergent
from that graph rather than a separate concept to maintain.

Trainees can re-run **Check my work** as often as they like. Attempts are recorded but not
penalised: the point is a fast feedback loop, and a grader that costs points to consult is
one trainees avoid consulting.

## Target systems: from real tenants to stand-ins

Scenarios today migrate against real SaaS tenants. The direction of travel is containerised
stand-ins — MinIO for object storage, a mock CMS, Postgres — for the levels where realism
teaches nothing that determinism doesn't. The reasons are grading reasons: a real tenant is
slow to seed, slow to reset, rate-limited, and occasionally flaky in ways that fail a
correct trainee. Every one of those turns into a support ticket and an erosion of trust in
the score.

A sensible end state is mixed: early levels against stand-ins, a final capstone against a
real tenant where the friction of a real system *is* the lesson.

## Phasing

**Phase 0 — prove the loop (this repo).** One scenario, end to end, with manual
provisioning. Seed → work → grade → report. Done: `make demo`.

**Phase 1 — automate the workspace.** Provisioner behind the interface above, per-trainee
isolation, reset, persistence across a multi-day course.

**Phase 2 — control plane.** Entra ID login for partner trainees, scenario list with
locked/available/passed state, "Check my work" button, trainer dashboard over the stored
reports.

**Phase 3 — curriculum.** More scenarios, holdout data for the advanced levels
(`cmd.run` a hidden input through the trainee's pipeline and assert the output — the check
that proves a migration generalises instead of having been hand-fixed), a capstone against a
real tenant.

Phase 0 is deliberately the only phase that has to happen before we know the answers in
[open-questions.md](open-questions.md).
