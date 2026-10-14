#!/usr/bin/env python3
"""Merge the output of a research pass into data/records.json, with checks.

    python3 tools/merge.py research.json            # validate, merge, rebuild the data files
    python3 tools/merge.py research.json --dry-run  # only report what would happen

research.json has the shape described in AGENTS.md (tools/pipeline.py assemble writes it):
  {"provenance": {"date", "agent", "model", "scope", "run_id"},  who made the pass; appended to meta.provenance.passes
   "records": [ <new record>, ... ],          full records in the register's schema
   "updates": [ {"id": "VN-02", "official_url": "...", "verification": {...}}, ... ],   fields to change on existing records
   "history_context": {"<ID>": {"reason": "...", "evidence": [...],
                                "fields": {"<field>": {"reason": "...", "evidence": [...]}}}},   optional
   "not_found": [...], "summary": "..."}      kept for the human reader, ignored here

Every new record must have a new id and slug, pass tools/validate.py, and not repeat an
official_url or title that is already in the register. Updates may only touch record fields
(never local_copy, which the archiver owns); when a URL changes, the record's local copy is
reset so the next archiver run fetches it again. A new record may bring its own local_copy
when tools/pipeline.py assemble made it from sources the archiver stored during the run.
Nothing is written if any check fails.

Every merge appends to data/history.jsonl (tools/history.py): an "added" event per new record,
a "changed" event per changed field, and a "re-verified" event for an update that changes
only the verification block. Reasons and evidence come from history_context when present.

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
import history  # noqa: E402
import validate  # noqa: E402

FIELDS = ["id", "slug", "title", "original_title", "short_title", "jurisdiction", "country", "jurisdiction_level", "region",
          "issuing_body", "instrument_type", "legal_force", "status", "date_published", "date_in_force", "date_last_updated",
          "official_identifier", "official_url", "secondary_url", "language", "summary", "safety_topics", "related", "notes",
          "verification"]
UPDATABLE = set(FIELDS) - {"id"}


def norm_title(t):
    return " ".join((t or "").lower().split())


def history_events(src, by, added, updated, befores):
    """The history lines for this merge: what was added, which fields changed, what was only re-verified."""
    prov = src.get("provenance") or {}
    ctx = src.get("history_context") or {}
    run_id = prov.get("run_id") or "manual-%s" % (prov.get("date") or history.today())
    tool, model = prov.get("agent"), prov.get("model")
    out = []

    def mk(rid, kind, **kw):
        return history.event(rid, kind, run_id=run_id, tool=tool, model=model, **kw)

    for rid in added:
        c = ctx.get(rid) or {}
        r = by[rid]
        out.append(mk(rid, "added", new="%s; %s; level %s" % (r.get("short_title") or r.get("title"), r.get("status"),
                                                               (r.get("verification") or {}).get("level")),
                      reason=c.get("reason") or prov.get("scope"), evidence=c.get("evidence")))
    for rid in dict.fromkeys(updated):
        c = ctx.get(rid) or {}
        fctx = c.get("fields") or {}
        before, after = befores[rid], by[rid]
        changed = [k for k in FIELDS if k != "verification" and before.get(k) != after.get(k)]
        vb, va = before.get("verification") or {}, after.get("verification") or {}
        for k in changed:
            fc = fctx.get(k) or {}
            out.append(mk(rid, "changed", field=k, old=before.get(k), new=after.get(k),
                          reason=fc.get("reason") or c.get("reason"), evidence=fc.get("evidence")))
        if vb.get("level") != va.get("level"):
            fc = fctx.get("verification.level") or {}
            out.append(mk(rid, "changed", field="verification.level", old=vb.get("level"), new=va.get("level"),
                          reason=fc.get("reason") or c.get("reason"), evidence=fc.get("evidence")))
        if not changed and vb.get("level") == va.get("level"):
            out.append(mk(rid, "re-verified", field=", ".join(c.get("confirmed") or []) or None,
                          new=va.get("verified_on"), reason=c.get("reason"), evidence=c.get("evidence")))
    return out


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
    befores = {}

    for n in src.get("records") or []:
        rid = n.get("id")
        rec = {k: n.get(k) for k in FIELDS}
        for k in ("safety_topics", "related"):
            rec[k] = rec[k] or []
        if isinstance(n.get("local_copy"), dict) and n["local_copy"].get("files"):
            rec["local_copy"] = n["local_copy"]  # stored during a pipeline run (archive/_runs/...)
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
        befores.setdefault(rid, before)
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

    TOKENS = {"A": "official-url-fetched", "B": "alternative-official-url-fetched", "C": "search-confirmed"}
    for rid in list(added) + list(updated):
        v = by[rid].get("verification") or {}
        if isinstance(v, dict) and v.get("level") in TOKENS and v.get("method") not in TOKENS.values():
            # research passes tend to write a sentence here; the register keeps one of three tokens and the sentence in the note
            v["note"] = ((v.get("method") or "").rstrip() + " " + (v.get("note") or "")).strip()
            v["method"] = TOKENS[v["level"]]
        if len(by[rid].get("summary") or "") > 700:
            print("WARNING  %-10s summary is %d characters (700 is the register's limit)" % (rid, len(by[rid]["summary"])))
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
    prov = src.get("provenance")
    events = history_events(src, by, added, updated, befores)
    if isinstance(prov, dict) and (added or updated):
        entry = dict(prov)
        entry.update({"records_added": len(added), "ids": added, "ids_updated": updated, "history_events": len(events)})
        db["meta"].setdefault("provenance", {}).setdefault("passes", []).append(entry)
    elif added or updated:
        print("WARNING  the pass has no 'provenance' entry (date, agent, model, scope); add one so the log stays complete")
    build.save(db)
    history.append(events)
    if events:  # the app data and HISTORY.md show the history, so write them again with the new events
        build.write_js(db)
        build.write_history_md()
    print("Merged into data/records.json and rebuilt the data files (%d records)." % len(R))
    print("Appended %d event(s) to data/history.jsonl." % len(events))
    if touched:
        print("Now archive the sources:  python3 tools/archive.py --only %s" % ",".join(sorted(touched)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
