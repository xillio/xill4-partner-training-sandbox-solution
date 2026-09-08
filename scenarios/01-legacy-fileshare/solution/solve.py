#!/usr/bin/env python3
"""Reference solution for 01-legacy-fileshare.

This is not what a trainee writes -- they build the equivalent as a Xill4 migration. It
exists so CI can prove two things about the scenario on every commit: the checks pass on a
correct answer, and they fail on an untouched workspace. A scenario whose checks have never
been shown to do both is not safe to put in front of a trainee.

It reads only `source/`, never the answer key.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

DEPARTMENT_KEYWORDS = [
    ("finance", ("fin",)),
    ("legal", ("legal",)),
    ("engineering", ("eng", "r&d")),
    ("marketing", ("mkt", "marketing")),
]
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y")


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def normalise_date(raw: str) -> str:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unrecognised date format: {raw!r}")


def normalise_department(raw: str) -> str:
    lowered = raw.strip().lower()
    for canonical, keywords in DEPARTMENT_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return canonical
    raise ValueError(f"unrecognised department: {raw!r}")


def solve(workspace: Path) -> None:
    source, target = workspace / "source", workspace / "target"
    target.mkdir(exist_ok=True)

    # as_posix(), not str(): metadata.csv records paths with forward slashes, so comparing
    # against a Windows backslash path would match nothing.
    files_on_share = sorted(
        path.relative_to(source).as_posix() for path in source.rglob("*")
        if path.is_file() and path.name != "metadata.csv"
    )

    # 1. Inventory
    (target / "manifest.json").write_text(json.dumps({"documents": [
        {
            "path": relpath,
            "bytes": (source / relpath).stat().st_size,
            "sha256": hashlib.sha256((source / relpath).read_bytes()).hexdigest(),
        }
        for relpath in files_on_share
    ]}, indent=2), encoding="utf-8")

    with (source / "metadata.csv").open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))

    described = {record["file_path"] for record in records}
    exceptions = [(record["file_path"], "missing_file") for record in records
                  if not (source / record["file_path"]).is_file()]
    exceptions += [(relpath, "no_metadata") for relpath in files_on_share
                   if relpath not in described]

    # 2 and 3. Transform, then load
    migrated = []
    content_root = target / "content"
    for record in records:
        file_path = source / record["file_path"]
        if record["status"].strip().lower() == "archived" or not file_path.is_file():
            continue
        created = normalise_date(record["created"])
        department = normalise_department(record["department"])
        doc_id = slug(record["title"])
        migrated.append({
            "doc_id": doc_id, "title": record["title"], "author": record["author"],
            "created": created, "department": department,
        })
        destination = content_root / department / created[:4] / f"{doc_id}{file_path.suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file_path, destination)

    _write_csv(target / "metadata.csv", ["doc_id", "title", "author", "created", "department"],
               [[row[column] for column in
                 ("doc_id", "title", "author", "created", "department")]
                for row in sorted(migrated, key=lambda r: r["doc_id"])])
    _write_csv(target / "exceptions.csv", ["file_path", "reason"], sorted(exceptions))

    print(f"migrated {len(migrated)} documents, {len(exceptions)} exception(s)")


def _write_csv(path: Path, header: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    solve(parser.parse_args().workspace)
