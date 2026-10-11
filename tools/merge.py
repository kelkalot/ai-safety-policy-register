#!/usr/bin/env python3
"""Merge the output of a research pass into data/records.json, with checks.

    python3 tools/merge.py research.json            # validate, merge, rebuild the data files
    python3 tools/merge.py research.json --dry-run  # only report what would happen

research.json has the shape described in AGENTS.md:
  {"records": [ <new record>, ... ],          full records in the register's schema
   "updates": [ {"id": "VN-02", "official_url": "...", "verification": {...}}, ... ],   fields to change on existing records
   "not_found": [...], "summary": "..."}      kept for the human reader, ignored here

Every new record must have a new id and slug, pass tools/validate.py, and not repeat an
official_url or title that is already in the register. Updates may only touch record fields
(never local_copy, which the archiver owns); when a URL changes, the record's local copy is
reset so the next archiver run fetches it again. Nothing is written if any check fails.

After a successful merge, run the archiver for the new IDs (the command is printed).
Standard library only.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import validate  # noqa: E402

FIELDS = ["id", "slug", "title", "original_title", "short_title", "jurisdiction", "country", "jurisdiction_level", "region",
          "issuing_body", "instrument_type", "legal_force", "status", "date_published", "date_in_force", "date_last_updated",
          "official_identifier", "official_url", "secondary_url", "language", "summary", "safety_topics", "related", "notes",
          "verification"]
UPDATABLE = set(FIELDS) - {"id"}


def norm_title(t):
    return " ".join((t or "").lower().split())


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge a research pass into data/records.json.")
    ap.add_argument("file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    with open(args.file, encoding="utf-8") as f:
        src = json.load(f)
    db = build.normalise(build.load())
    R = db["records"]; by = {r["id"]: r for r in R}
    slugs = {r["slug"] for r in R}
    urls = {r["official_url"]: r["id"] for r in R if r.get("official_url")}
    titles = {norm_title(r["title"]): r["id"] for r in R}
    problems = []
    added, updated = [], []

    for n in src.get("records") or []:
        rid = n.get("id")
        rec = {k: n.get(k) for k in FIELDS}
        for k in ("safety_topics", "related"):
            rec[k] = rec[k] or []
        extra = sorted(set(n) - set(FIELDS) - {"local_copy"})
        if extra:
            problems.append((rid, "unknown fields dropped: %s" % ", ".join(extra)))
        if not rid or rid in by:
            problems.append((rid, "id is missing or already exists")); continue
        if rec["slug"] in slugs:
            problems.append((rid, "slug %r already exists" % rec["slug"])); continue
        if rec.get("official_url") and rec["official_url"] in urls:
            problems.append((rid, "official_url already used by %s" % urls[rec["official_url"]])); continue
        if norm_title(rec.get("title")) in titles:
            problems.append((rid, "title already used by %s" % titles[norm_title(rec["title"])])); continue
        R.append(rec); by[rid] = rec; slugs.add(rec["slug"]); titles[norm_title(rec["title"])] = rid
        if rec.get("official_url"):
            urls[rec["official_url"]] = rid
        added.append(rid)

    for u in src.get("updates") or []:
        rid = u.get("id")
        if rid not in by:
            problems.append((rid, "update for a record that does not exist")); continue
        rec = by[rid]; before = copy.deepcopy(rec)
        for k, v in u.items():
            if k == "id":
                continue
            if k not in UPDATABLE:
                problems.append((rid, "field %r cannot be updated here" % k)); continue
            if k == "verification" and isinstance(v, dict) and isinstance(rec.get("verification"), dict):
                rec["verification"] = {**rec["verification"], **v}
            else:
                rec[k] = v
        if before.get("official_url") != rec.get("official_url") or before.get("secondary_url") != rec.get("secondary_url"):
            rec["local_copy"] = None  # the archiver will fetch the new URLs
        updated.append(rid)

    build.normalise(db)
    touched = set(added) | set(updated)
    checks = validate.check(db)
    errors = [(rid, msg) for level, rid, msg in checks if level == "error" and (rid in touched or rid == "-" or any(t in rid for t in touched))]
    warnings = [(rid, msg) for level, rid, msg in checks if level == "warning" and rid in touched]
    problems += errors

    for rid, msg in problems:
        print("ERROR    %-10s %s" % (rid, msg))
    for rid, msg in warnings:
        print("WARNING  %-10s %s" % (rid, msg))
    print("%d new record(s): %s" % (len(added), ", ".join(added) or "-"))
    print("%d update(s): %s" % (len(updated), ", ".join(updated) or "-"))
    if problems:
        print("Nothing written: fix the %d error(s) above in %s." % (len(problems), args.file)); return 1
    if args.dry_run:
        print("Dry run: nothing written."); return 0
    db["meta"]["record_count"] = len(R)
    build.save(db)
    print("Merged into data/records.json and rebuilt the data files (%d records)." % len(R))
    if touched:
        print("Now archive the sources:  python3 tools/archive.py --only %s" % ",".join(sorted(touched)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
