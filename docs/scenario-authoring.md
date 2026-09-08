# Writing a scenario

A scenario is a directory under `scenarios/`:

```
scenarios/01-legacy-fileshare/
  scenario.yaml        tasks, weights and checks
  brief.md             what the trainee reads
  seedgen.py           generates source/ and the grader-only .expected/
  solution/solve.py    reference solution, run by CI -- not shown to trainees
```

## scenario.yaml

```yaml
id: 01-legacy-fileshare
title: Migrate a legacy project file share
level: 1
prerequisites: []           # scenario ids that must pass before this unlocks
brief: brief.md
timebox_minutes: 90
requires_vars: [SOURCE, TARGET, EXPECTED]   # grading aborts if one is missing

tasks:
  - id: load
    title: Load the content into the target structure
    weight: 40              # weights across a scenario must total 100
    hint: shown only when the task fails
    checks:
      - id: content-tree
        type: fs.tree_matches
        description: what this check is for, in the report
        params: {path: "${TARGET}/content", manifest: "${EXPECTED}/content_tree.json"}
        on_fail: appended to the failure message -- teach, don't just report
```

A task is all-or-nothing: it scores its full weight or zero. Every check in it runs even
after the first failure, so a trainee sees the whole picture in one attempt.

## Variables

Params are expanded for `${VAR}` from variables the control plane supplies per trainee
(`SOURCE`, `TARGET`, `EXPECTED`, `S3_ENDPOINT`, …). The grader container reads them from
`SANDBOX_*` environment variables; the CLI takes `--var NAME=VALUE`. Referencing a variable
that was not supplied is an error, not an empty string — grading against `/manifest.json`
because `${TARGET}` silently vanished is exactly the failure mode to avoid.

Anywhere a check takes a number, it also takes a reference to a fact about the trainee's own
seed data:

```yaml
equals: {from: "${EXPECTED}/facts.json", query: "files_on_share"}
```

This is what lets one scenario grade N differently-seeded workspaces.

## Check types

| Type | Asserts | Key params |
| --- | --- | --- |
| `fs.exists` | a path is there | `path`, `kind` (`file`/`dir`/`any`) |
| `fs.file_count` | how many files match a glob | `path`, `pattern`, `equals`/`min`/`max` |
| `fs.tree_matches` | a directory matches a manifest of paths and hashes | `path`, `manifest`, `compare` |
| `json.assert` | values inside a JSON document | `path`, `queries` |
| `csv.matches` | a CSV matches an expected CSV, keyed, order-independent | `path`, `expected`, `key`, `columns` |
| `cmd.run` | a command's exit code and output | `command`, `cwd`, `expect_exit_code`, `stdout_matches` |
| `s3.object_count` | objects under a prefix | `bucket`, `prefix`, `equals`/`min`/`max` |

`json.assert` queries use a deliberately small syntax: `a.b.c`, `items[0]`, and `items[]`
for length. Anything more complex is a sign the assertion wants to be its own check type,
where the failure message can explain itself properly.

Two rules keep a scenario grading identically on Windows and Linux, both learned the hard
way. Any path a scenario **stores or compares** -- in a manifest, a CSV, a check parameter --
must use forward slashes; take them from `Path.as_posix()`, never `str(Path)`. And any file
whose **content** is hashed must be written with `write_bytes`, because text mode rewrites
`\n` as `\r\n` on Windows and every hash then mismatches.

`cmd.run` is the escape hatch and the home of holdout grading: run a hidden input through
whatever the trainee built and assert the output. It is the strongest signal available,
because it shows the migration generalises rather than having been hand-fixed for the
records the trainee could see. Pass its `command` as a **list**, not a string: string
commands go through `shlex.split`, which follows POSIX quoting and mangles Windows paths.

### Adding a check type

```python
@check("xill4.job_succeeded")
def job_succeeded(params: dict[str, Any], ctx: Context) -> Outcome:
    ...
    return Outcome(passed, "human-readable verdict", {"evidence": "..."})
```

Put it in `grader/grader/checks/`, import it from that package's `__init__`, and give it
unit tests. Evidence is stored with the attempt and shown to the trainee, so put in it
whatever someone would otherwise have to re-run the check to learn.

## Rules for a scenario to be shippable

CI enforces the first three; the rest is judgement.

1. **The reference solution scores 100/100.**
2. **An untouched workspace scores 0/100**, with every task failing. A check suite that
   only satisfies rule 1 is grading nothing.
3. Weights total 100 and the brief exists.
4. Seeding is reproducible from its seed, and different seeds produce different data.
5. Checks assert on outcomes in the target, never on how the trainee got there.
6. Every failure message tells the trainee something they can act on.

Run them all with `make test`. Try the whole loop with `make demo`.
