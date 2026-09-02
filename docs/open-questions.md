# Open questions

Everything below is a decision that belongs to Xillio, not to this repo. Phase 0 was built
so that none of them block starting — but the first two decide what Phase 1 looks like.

## 1. Can Xill4 run as a container? *(blocking for Phase 1)*

Specifically: is there a Linux image, or can the engine be installed headless into one? And
does the licence permit N short-lived instances rather than N named servers?

- **Yes** → container per trainee. One host serves a cohort; reset is seconds; the
  `docker-compose.yml` in `workspace/` becomes real by swapping the placeholder image.
- **No** → VM per trainee, provisioned with Bicep or Terraform, with auto-shutdown. More
  expensive and slower to reset, but it works, and nothing in `scenarios/` or `grader/`
  changes.

## 2. Do trainees need the Xill IDE, or only the server?

If exercises can be done against the server alone, everything is browser-reachable and the
container path is open. If the desktop IDE is required, the workspace becomes an Azure
Virtual Desktop session rather than a container, and the grader runs beside it instead of
against a mounted volume — the scenarios are unaffected either way.

## 3. Does Xill4 expose an API for project and job state?

If it does, checks can also assert on the *migration* rather than only its output: job
completed without errors, the pipeline contains a transformation step, the run processed
N records. That makes richer feedback possible ("your job ran but skipped the archived
records silently"). If it does not, outcome checks on the target carry the whole load —
which is workable, and is what scenario 01 does today.

## 4. Where does the control plane live, and who authenticates?

Partner trainees are external. Entra ID with guest accounts is the obvious fit given the
Azure footprint, but it needs confirming against how partners are contracted.

## 5. Which existing exercises become scenarios 02+?

Scenario 01 was written from first principles as a proof of the loop. The real curriculum
should come from the exercises already used in the training programme — porting them is
mostly writing `seedgen.py` and the checks, and each one is a day or two of work.

## 6. Real tenants in the curriculum: where, exactly?

Stand-ins are better for grading; a real tenant is better for the final lesson about a real
system's friction. A capstone against a real tenant, with everything before it against
stand-ins, is the proposal — but which system that capstone targets is a curriculum call.
