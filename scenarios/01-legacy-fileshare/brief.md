# Migrate a legacy project file share

**Level 1 · 90 minutes · 100 points**

A departing client has handed over a project file share and a metadata export. Your job is
to migrate it into the target structure, normalising the metadata on the way and reporting
whatever cannot be migrated.

## What you have

| Location | What it is |
| --- | --- |
| `source/` | The legacy share: `Projects/<Client>/<Year>/<file>` |
| `source/metadata.csv` | The client's metadata export: `file_path,title,author,created,department,status` |
| `target/` | Empty. Everything you produce goes here. |

The export was maintained by hand for years. It is not consistent, and it does not agree
with the share in every case. Both of those are part of the exercise.

## What to produce

### 1. `target/manifest.json` — inventory the share (15 pts)

Every file physically present under `source/`, excluding `metadata.csv` itself:

```json
{ "documents": [ { "path": "Projects/ACME/2019/audit-findings-03.pdf",
                   "bytes": 412, "sha256": "..." } ] }
```

### 2. `target/metadata.csv` — normalise the metadata (25 pts)

Columns `doc_id,title,author,created,department`, one row per **migrated** document.

- `doc_id` — the title, lowercased, with every run of non-alphanumeric characters replaced
  by a single hyphen and hyphens trimmed from both ends.
- `created` — ISO-8601 (`YYYY-MM-DD`). The export contains `2019-03-04`, `04/03/2019`
  (day first) and `4 Mar 2019`.
- `department` — one of `finance`, `legal`, `engineering`, `marketing`. The export holds
  variants of each: case, padding, abbreviations (`FIN`, `ENG`, `MKT`) and longer labels
  (`Finance Dept`, `R&D / Engineering`, `Marketing & Comms`, `legal affairs`).
- Records with `status = archived` are **not** migrated and do not appear here.

### 3. `target/content/` — load the content (40 pts)

Copy each migrated document to `target/content/<department>/<year>/<doc_id>.<ext>`, where
`<year>` comes from the normalised `created` date and `<ext>` is the source extension.
Content must be byte-identical to the source.

### 4. `target/exceptions.csv` — report the defects (20 pts)

Columns `file_path,reason`, using exactly these reason codes:

| Reason | Meaning |
| --- | --- |
| `missing_file` | The metadata lists a file that is not on the share |
| `no_metadata` | A file is on the share but has no row in the export |

Archived records are not exceptions — they are a deliberate exclusion.

## How you are graded

Run **Check my work** whenever you like; there is no penalty for attempts, and the number
of attempts and the time to your first pass are recorded for your trainer.

Grading looks only at what ended up in `target/`. How you get there — which Xill4 constructs
you use, in what order — is yours to decide. Your seed data is unique to you, so an answer
copied from another trainee will not pass.
