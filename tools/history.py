#!/usr/bin/env python3
"""The register's change history: data/history.jsonl.

One JSON object per line, appended and never rewritten:

  {"date": "2026-11-02", "run_id": "2026-11-02-discover-europe", "record_id": "FI-03",
   "event": "changed", "field": "status", "old": "Draft / proposed", "new": "In force",
   "reason": "...", "evidence": [{"file", "sha256", "locator", "quote"}], "tool": "...", "model": "..."}

event is one of EVENTS. Only tools write this file: tools/merge.py for added, changed and
re-verified records, and tools/pipeline.py for human checks and scope decisions. Agents never
edit it. A correction is a new event, never an edited line.

    python3 tools/history.py ID        # print the history of one record
    python3 tools/history.py --check   # check that every line parses and has the required keys

Standard library only. Python 3.8+.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history.jsonl"
EVENTS = ["added", "changed", "re-verified", "source-changed", "human-checked", "scope-decision"]
KEYS = ["date", "run_id", "record_id", "event", "field", "old", "new", "reason", "evidence", "tool", "model"]


def today():
    return dt.date.today().isoformat()


def event(record_id, kind, run_id=None, field=None, old=None, new=None, reason=None, evidence=None,
          tool=None, model=None, date=None):
    if kind not in EVENTS:
        raise ValueError("unknown history event %r" % kind)
    return {"date": date or today(), "run_id": run_id, "record_id": record_id, "event": kind, "field": field,
            "old": old, "new": new, "reason": reason, "evidence": evidence or [], "tool": tool, "model": model}


def append(events, root=ROOT):
    """Append events to data/history.jsonl. Never rewrites earlier lines."""
    if not events:
        return 0
    path = root / "data" / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for e in events:
            missing = [k for k in KEYS if k not in e]
            if missing or e.get("event") not in EVENTS:
                raise ValueError("malformed history event: %r" % e)
            f.write(json.dumps({k: e[k] for k in KEYS}, ensure_ascii=False) + "\n")
    return len(events)


def load(root=ROOT):
    path = root / "data" / "history.jsonl"
    if not path.is_file():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    raise SystemExit("data/history.jsonl line %d is not valid JSON" % n)
    return out


def by_record(events):
    out = {}
    for e in events:
        out.setdefault(e.get("record_id"), []).append(e)
    return out


def short(v, n=80):
    if v is None:
        return "-"
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n - 1] + "…"


def describe(e):
    """One line for humans."""
    k = e["event"]
    if k == "changed" and e.get("field") in ("related", "safety_topics"):
        def ids(v):
            return [x.get("id") if isinstance(x, dict) else x for x in (v or [])]
        old, new = ids(e.get("old")), ids(e.get("new"))
        plus = [x for x in new if x not in old]
        minus = [x for x in old if x not in new]
        return "%s: %s" % (e["field"], ", ".join(["+ %s" % x for x in plus] + ["- %s" % x for x in minus]) or "reordered")
    if k == "changed":
        return "%s: %s → %s" % (e.get("field"), short(e.get("old"), 60), short(e.get("new"), 60))
    if k == "added":
        return "added" + (" (%s)" % short(e.get("new"), 70) if e.get("new") else "")
    if k == "re-verified":
        return "re-verified, no change" + (" to %s" % e["field"] if e.get("field") else "")
    if k == "human-checked":
        return "checked by a human: %s" % short(e.get("new"), 70)
    if k == "scope-decision":
        return "scope decision: %s" % short(e.get("new"), 70)
    if k == "source-changed":
        return "source changed: %s" % short(e.get("field") or e.get("new"), 70)
    return k


def main(argv=None):
    ap = argparse.ArgumentParser(description="Show or check data/history.jsonl.")
    ap.add_argument("id", nargs="?", help="record ID to show")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    events = load()
    if args.check:
        bad = [i for i, e in enumerate(events, 1) if [k for k in KEYS if k not in e] or e.get("event") not in EVENTS]
        print("%d events, %d malformed%s" % (len(events), len(bad), (": lines " + ", ".join(map(str, bad[:20]))) if bad else ""))
        return 1 if bad else 0
    for e in events:
        if not args.id or e.get("record_id") == args.id:
            print("%s  %-10s %-34s %s%s" % (e["date"], e["record_id"], e.get("run_id") or "-", describe(e),
                                            ("  [%s]" % e["reason"]) if e.get("reason") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
