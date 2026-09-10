# Open questions

Everything below is a decision that belongs to Xillio, not to this repo. Phase 0 was built
so that none of them block starting. The first two — which shaped Phase 1 — are now
answered; what is left of question 1 is a licensing conversation, not an engineering one.

## 1. Can Xill4 run as a container? **Answered: yes.**

There is an official Linux image, `docker.cloudsmith.io/xillio/xill4/xill4:v4.62.0`, pulled
with the Cloudsmith entitlement token as the registry password. It listens on 8000 and takes
`XILL4_LICENSE_KEY`, `XILL4_DATABASE_CONNECTION_STRING` and `XILL4_ENVIRONMENT_SECRET`, and
it needs MongoDB — projects and flows live there, not on the filesystem, which is why a
trainee's sandbox now has a database as well as a directory.

`workspace/docker-compose.yml` is written against that image. The VM backend is no longer
needed.

**Still open, and commercial rather than technical:** the licence covers using Xill4 and the
downloads on xillio.community. Whether it covers *five instances running at once, one per
trainee, for the length of a course* has not been confirmed with whoever owns licensing. It
is worth confirming before the first cohort rather than after: the architecture assumes it,
and no amount of engineering substitutes for the answer.

## 1a. Does the per-deployment environment secret constrain anything? *(answered)*

`XILL4_ENVIRONMENT_SECRET` is per deployment, not per trainee: one value for the whole
cohort, generated once into `.env.platform`. Rotating it invalidates whatever running
instances encrypted with the old one, so it is generated at first provision and then left
alone.

## 2. Do trainees need the Xill IDE, or only the server? **Answered: the browser.**

Trainees work against the server's own UI on port 8000. No desktop session, no Azure Virtual
Desktop, no per-trainee Windows licence — which is most of why a cohort fits on one host.

## 3. Does Xill4 expose an API for project and job state?

Still open, but the answer matters less than it did: the state is in MongoDB, and the grader
already runs host-side with credentials the trainee does not have. A `xill4.job_succeeded`
check could read the trainee's database directly, whether or not an HTTP API exists.

That would be a second kind of check, not a replacement. Grading still asserts outcomes in
the target, never method — reading job state to say "your job ran but skipped the archived
records silently" is better *feedback*, not a better *mark*. The line to hold: what a
trainee scores stays a function of what landed in the target.

## 4. Where does the control plane live, and who authenticates?

Partner trainees are external. Entra ID with guest accounts is the obvious fit given the
Azure footprint, but it needs confirming against how partners are contracted.

## 4a. Is scenario 01 expressible in Xill4? *(the one to answer first)*

The brief asks for four artefacts, one of which is a `manifest.json` carrying a **sha256 per
file**, and another an exceptions CSV. Confirmed with the trainer that a Xill4 flow can hash
a file and write JSON and CSV to a mounted path — so scenario 01 stands as the Phase 1
vehicle. The residual risk is not feasibility but *effort*: if producing the manifest takes a
real trainee three times as long as the other three tasks, the 15 points it carries are
mispriced. That is a question the first real run answers, not a question about the product.

## 5. Which existing exercises become scenarios 02+?

Scenario 01 was written from first principles as a proof of the loop. The real curriculum
should come from the exercises already used in the training programme — porting them is
mostly writing `seedgen.py` and the checks, and each one is a day or two of work.

## 6. Real tenants in the curriculum: where, exactly?

Stand-ins are better for grading; a real tenant is better for the final lesson about a real
system's friction. A capstone against a real tenant, with everything before it against
stand-ins, is the proposal — but which system that capstone targets is a curriculum call.
