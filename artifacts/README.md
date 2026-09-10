# Generated artifacts

Output produced during working sessions: the published proposal pages, the slide
deck and its generator, git bundles, and render previews from visual checks.

## What is tracked, and what is not

Text that is worth reviewing in a diff is committed. Binaries and regenerable
output are not.

| Path | Tracked | What it is |
| --- | --- | --- |
| `proposal/business-case.html` | yes | The live proposal — source of the published page. Republishing updates that page in place. |
| `proposal/business-case-detailed-superseded.html` | yes | The earlier long version. Contains figures since corrected — kept for history, **not for circulation**. |
| `proposal/architecture-note.html` | yes | The first technical write-up: three planes, workspace anatomy, grading design. |
| `deck/build.js` | yes | pptxgenjs generator for the slide deck. **Edit this, not the .pptx** — the .pptx is rebuilt from it. |
| `deck/*.pptx` | no | The deck itself. Regenerate with `node artifacts/deck/build.js`. |
| `bundles/` | no | Git bundles of this repository, for moving work to a machine. |
| `previews/` | no | Rendered page screenshots from visual checks. |

Anything untracked here lives only in the session container and disappears when
it is reclaimed. Download it, or regenerate it from the tracked source.

## Rebuilding the deck

```
cd artifacts/deck
npm install pptxgenjs      # first time only
node build.js
```

## The published proposal

`proposal/business-case.html` is the source of a page published on claude.ai. It
carries a feedback box on every section, backed by the artifact's own store, so
reviewers comment in the page rather than by email. Republishing from this path
updates the existing page and keeps its URL — publishing it as a new artifact
would orphan the link people have already been given.
