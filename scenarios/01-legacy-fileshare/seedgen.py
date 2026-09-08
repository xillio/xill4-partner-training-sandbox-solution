#!/usr/bin/env python3
"""Generate one trainee's copy of the legacy file share, plus the grader's answer key.

Everything is derived from a seed string (in practice `hash(trainee_id, scenario_id)`),
so every trainee gets structurally identical but textually different data. That is what
makes the exercise shareable as a curriculum and unshareable as an answer.

Layout produced under the workspace:

    source/     mounted into the trainee's Xill4 instance -- the legacy share
    .expected/  grader only, never mounted -- the answer key derived from this seed

Run:  python3 seedgen.py --workspace /workspaces/alice/01 --seed alice:01
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
from pathlib import Path

CLIENTS = ["ACME", "Northwind", "Contoso", "Initech", "Umbrella", "Globex"]
DEPARTMENTS = ["finance", "legal", "engineering", "marketing"]
# Real shares never hold a clean controlled vocabulary. These are the variants a trainee
# has to fold back onto the four canonical values above.
DEPARTMENT_VARIANTS = {
    "finance": ["Finance", " finance", "FIN", "Finance Dept"],
    "legal": ["Legal", "LEGAL", "legal affairs", " Legal "],
    "engineering": ["Engineering", "ENG", "engineering", "R&D / Engineering"],
    "marketing": ["Marketing", "MKT", " marketing", "Marketing & Comms"],
}
# One topic per document, never reused: the title is built from it, and the target path is
# built from the title. Reusing a topic could put two documents on one target path, where
# one would silently overwrite the other -- and since the answer key would collapse the
# same way, the grader would award full marks for a lost document. Keep this list at least
# DOCUMENT_COUNT long.
TOPICS = ["quarterly report", "service agreement", "design specification", "audit findings",
          "migration plan", "risk register", "vendor assessment", "release notes",
          "budget forecast", "policy update", "training manual", "incident review",
          "capacity study", "data retention policy", "roadmap review", "cost analysis",
          "statement of work", "access review", "disaster recovery plan", "change log",
          "supplier contract", "board minutes", "security assessment", "licence inventory",
          "handover notes", "service catalogue", "penetration test report", "asset register",
          "retention schedule", "escalation procedure"]
SURNAMES = ["Jansen", "de Vries", "Bakker", "Visser", "Smit", "Meijer", "Mulder", "Bos"]
GIVEN_NAMES = ["Anna", "Pieter", "Sofie", "Lars", "Maud", "Tobias", "Ilse", "Ruben"]
EXTENSIONS = ["pdf", "docx", "xlsx", "txt"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

DOCUMENT_COUNT = 26
ARCHIVED_COUNT = 4
MISSING_FILE_COUNT = 2
NO_METADATA_COUNT = 1


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _write_date(rng: random.Random, year: int, month: int, day: int) -> str:
    """Emit a date in one of three formats the legacy system used over the years."""
    style = rng.choice(["iso", "dutch", "long"])
    if style == "iso":
        return f"{year:04d}-{month:02d}-{day:02d}"
    if style == "dutch":
        return f"{day:02d}/{month:02d}/{year:04d}"
    return f"{day} {MONTHS[month - 1]} {year}"


def build_documents(rng: random.Random) -> list[dict]:
    if len(TOPICS) < DOCUMENT_COUNT:
        raise AssertionError(
            f"need at least {DOCUMENT_COUNT} topics to keep every title unique, "
            f"have {len(TOPICS)}"
        )
    documents = []
    for index in range(DOCUMENT_COUNT):
        department = DEPARTMENTS[index % len(DEPARTMENTS)]
        client = rng.choice(CLIENTS)
        year = rng.randint(2016, 2023)
        month, day = rng.randint(1, 12), rng.randint(1, 28)
        topic = TOPICS[index % len(TOPICS)]
        title = f"{client} {topic} {year}"
        extension = rng.choice(EXTENSIONS)
        documents.append({
            "doc_id": slug(title),
            "title": title,
            "author": f"{rng.choice(GIVEN_NAMES)} {rng.choice(SURNAMES)}",
            "created_raw": _write_date(rng, year, month, day),
            "created_iso": f"{year:04d}-{month:02d}-{day:02d}",
            "department_raw": rng.choice(DEPARTMENT_VARIANTS[department]),
            "department": department,
            "year": year,
            "extension": extension,
            "source_path": f"Projects/{client}/{year}/{slug(topic)}-{index:02d}.{extension}",
            "status": "active",
            "body": f"{title}\nPrepared for {client}.\n" + "\n".join(
                f"Section {n}: {rng.choice(TOPICS)}." for n in range(1, rng.randint(4, 9))
            ) + "\n",
        })

    # Deliberate defects. Their positions come from the seed too, so no two trainees hit
    # the same rows -- but every trainee hits the same *kinds* of problem.
    for document in rng.sample(documents, ARCHIVED_COUNT):
        document["status"] = "archived"
    remaining = [d for d in documents if d["status"] == "active"]
    for document in rng.sample(remaining, MISSING_FILE_COUNT):
        document["defect"] = "missing_file"
    remaining = [d for d in remaining if "defect" not in d]
    for document in rng.sample(remaining, NO_METADATA_COUNT):
        document["defect"] = "no_metadata"
    return documents


def write_source(root: Path, documents: list[dict]) -> None:
    for document in documents:
        if document.get("defect") == "missing_file":
            continue  # listed in the metadata, absent from the share
        target = root / document["source_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        # write_bytes, not write_text: text mode rewrites \n as \r\n on Windows, while the
        # answer key hashes the body as written here. The grader compares content by
        # sha256, so a translated newline makes every single document mismatch.
        target.write_bytes(document["body"].encode("utf-8"))

    with (root / "metadata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file_path", "title", "author", "created", "department", "status"])
        for document in documents:
            if document.get("defect") == "no_metadata":
                continue  # present on the share, unknown to the metadata export
            writer.writerow([
                document["source_path"], document["title"], document["author"],
                document["created_raw"], document["department_raw"], document["status"],
            ])


def write_answer_key(root: Path, documents: list[dict]) -> None:
    migrated = [d for d in documents if d["status"] == "active" and "defect" not in d]

    content_tree = {
        f"{d['department']}/{d['year']}/{d['doc_id']}.{d['extension']}":
            hashlib.sha256(d["body"].encode("utf-8")).hexdigest()
        for d in migrated
    }
    (root / "content_tree.json").write_text(json.dumps(content_tree, indent=2, sort_keys=True),
                                            encoding="utf-8")

    with (root / "metadata.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["doc_id", "title", "author", "created", "department"])
        for document in sorted(migrated, key=lambda d: d["doc_id"]):
            writer.writerow([document["doc_id"], document["title"], document["author"],
                             document["created_iso"], document["department"]])

    with (root / "exceptions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file_path", "reason"])
        exceptions = [(d["source_path"], d["defect"]) for d in documents if "defect" in d]
        for file_path, reason in sorted(exceptions):
            writer.writerow([file_path, reason])

    on_disk = sum(1 for d in documents if d.get("defect") != "missing_file")
    (root / "facts.json").write_text(json.dumps({
        "files_on_share": on_disk,
        "documents_to_migrate": len(migrated),
        "exceptions": DOCUMENT_COUNT - len([d for d in documents if "defect" not in d]),
        "archived": ARCHIVED_COUNT,
    }, indent=2), encoding="utf-8")


def generate(workspace: Path, seed: str, force: bool = False) -> None:
    source, expected = workspace / "source", workspace / ".expected"
    for directory in (source, expected):
        if directory.exists():
            if not force:
                raise SystemExit(f"{directory} already exists; pass --force to regenerate")
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    (workspace / "target").mkdir(exist_ok=True)

    rng = random.Random(hashlib.sha256(seed.encode("utf-8")).hexdigest())
    documents = build_documents(rng)
    write_source(source, documents)
    write_answer_key(expected, documents)
    print(f"seeded {workspace} from seed {seed!r}: "
          f"{sum(1 for d in documents if d.get('defect') != 'missing_file')} files on the share")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--seed", required=True, help="stable per trainee, e.g. 'alice:01'")
    parser.add_argument("--force", action="store_true", help="regenerate over existing data")
    args = parser.parse_args()
    generate(args.workspace, args.seed, args.force)


if __name__ == "__main__":
    main()
