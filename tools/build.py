#!/usr/bin/env python3
"""Regenerate the derived data files from data/records.json.

    python3 tools/build.py

Writes:
  data/records.js       the data the web app loads (works from file:// too)
  data/records.csv      one row per record, for spreadsheets
  data/register.sqlite  a relational copy for SQL queries
  data/register.xlsx    an Excel workbook (only when the openpyxl package is installed)
  HISTORY.md            the change history from data/history.jsonl, newest first, for readers

data/records.json is the single source of truth. Edit it (or let
tools/archive.py update it), then run this script. It first runs the checks in
tools/validate.py and stops if there are errors (unknown vocabulary values,
malformed dates, dangling related IDs, ...), so a bad edit never reaches the app.

Standard library only. Python 3.8+.
"""
import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history  # noqa: E402  (same folder)
import validate  # noqa: E402  (same folder)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

LOCAL_STATUSES = [
    "archived",            # official source saved, no warnings
    "archived-review",     # saved, but the content needs a human look (bot check, JS page, title mismatch)
    "partial",             # official source failed; only a secondary source was saved
    "failed",              # nothing could be saved
    "no-url",              # the record has no official URL
    "not-attempted",       # the archiver has not run for this record yet
]

CSV_COLS = [
    "id", "title", "original_title", "short_title", "jurisdiction", "country", "jurisdiction_level", "region",
    "issuing_body", "instrument_type", "legal_force", "status", "date_published", "date_in_force",
    "date_last_updated", "official_identifier", "official_url", "secondary_url", "language", "english_version",
    "english_version_url", "english_version_by", "summary",
    "safety_topics", "related_ids", "notes", "scope_note", "open_questions", "verification_level", "verified_on", "verification_method",
    "verification_note", "second_check", "local_status", "local_flag", "local_last_attempt", "local_files",
    "local_sha256",
]


def load(root=ROOT):
    with open(root / "data" / "records.json", encoding="utf-8") as f:
        return json.load(f)


def default_local_copy(rec):
    if not rec.get("official_url") and not rec.get("secondary_url"):
        return {"status": "no-url", "flag": "No official URL is recorded, so nothing can be archived.",
                "last_attempt": None, "files": [], "attempts": []}
    return {"status": "not-attempted", "flag": "The archiver has not been run for this record yet.",
            "last_attempt": None, "files": [], "attempts": []}


def normalise(db):
    for r in db["records"]:
        lc = r.get("local_copy")
        if not lc or lc.get("status") not in LOCAL_STATUSES:
            r["local_copy"] = default_local_copy(r)
        elif lc.get("status") == "not-attempted" and not r.get("official_url") and not r.get("secondary_url"):
            r["local_copy"] = default_local_copy(r)
    return db


_QUESTIONS = {}


def open_questions(root=ROOT):
    """record ID -> its open questions from pipeline/questions.json: [{"issue", "url", "title"}]."""
    key = str(root)
    if key not in _QUESTIONS:
        out = {}
        try:
            reg = json.loads((root / "pipeline" / "questions.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            reg = {}
        for q in reg.get("questions") or []:
            if q.get("state") == "open" and q.get("kind") == "record":
                out.setdefault(q.get("subject"), []).append(
                    {"issue": q.get("issue"), "url": q.get("url"), "run_id": q.get("run_id"),
                     "why": (q.get("why") or "")[:300]})
        _QUESTIONS[key] = out
    return _QUESTIONS[key]


def flat(r):
    v = r.get("verification") or {}
    ev = r.get("english_version") or {}
    lc = r.get("local_copy") or {}
    files = lc.get("files") or []
    return {
        "id": r["id"], "title": r.get("title"), "original_title": r.get("original_title"),
        "short_title": r.get("short_title"), "jurisdiction": r.get("jurisdiction"), "country": r.get("country"),
        "jurisdiction_level": r.get("jurisdiction_level"), "region": r.get("region"),
        "issuing_body": r.get("issuing_body"), "instrument_type": r.get("instrument_type"),
        "legal_force": r.get("legal_force"), "status": r.get("status"), "date_published": r.get("date_published"),
        "date_in_force": r.get("date_in_force"), "date_last_updated": r.get("date_last_updated"),
        "official_identifier": r.get("official_identifier"), "official_url": r.get("official_url"),
        "secondary_url": r.get("secondary_url"), "language": r.get("language"),
        "english_version": ev.get("kind"), "english_version_url": ev.get("url"), "english_version_by": ev.get("by"),
        "summary": r.get("summary"),
        "safety_topics": "; ".join(r.get("safety_topics") or []),
        "related_ids": "; ".join(x.get("id") for x in (r.get("related") or []) if x.get("id")),
        "notes": r.get("notes"), "scope_note": r.get("scope_note"),
        "open_questions": "; ".join(q["url"] or "open question (no issue yet)" for q in open_questions().get(r["id"], [])) or None,
        "verification_level": v.get("level"), "verified_on": v.get("verified_on"),
        "verification_method": v.get("method"), "verification_note": v.get("note"),
        "second_check": v.get("second_check"), "local_status": lc.get("status"),
        "local_flag": " ".join(x for x in (lc.get("flag"), lc.get("integrity_flag")) if x) or None,
        "local_last_attempt": lc.get("last_attempt"),
        "local_files": "; ".join(f.get("path", "") for f in files),
        "local_sha256": "; ".join(f.get("sha256", "") for f in files),
    }


def history_for_app(root=ROOT):
    """The history per record for the app, with evidence cut down to the first quote."""
    out = {}
    for e in history.load(root):
        ev = e.get("evidence") or []
        first = ev[0] if ev and isinstance(ev[0], dict) else {}
        out.setdefault(e.get("record_id"), []).append({
            "date": e.get("date"), "run_id": e.get("run_id"), "event": e.get("event"), "field": e.get("field"),
            "old": e.get("old"), "new": e.get("new"), "reason": e.get("reason"), "tool": e.get("tool"),
            "model": e.get("model"), "evidence": len(ev),
            "quote": (first.get("quote") or "")[:240] or None, "file": first.get("file")})
    return out


def write_js(db, root=ROOT):
    hist = history_for_app(root)
    _QUESTIONS.pop(str(root), None)
    payload = dict(db, history=hist) if hist else dict(db)
    payload["questions"] = open_questions(root)
    payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    text = ("/* Generated by tools/build.py from data/records.json. Do not edit by hand. */\n"
            "window.REGISTER = " + payload + ";\n")
    (root / "data" / "records.js").write_text(text, encoding="utf-8")


def write_csv(db, root=ROOT):
    with open(root / "data" / "records.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for r in db["records"]:
            w.writerow(flat(r))


def write_sqlite(db, root=ROOT):
    path = root / "data" / "register.sqlite"
    tmp = path.with_suffix(".sqlite.tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(str(tmp))
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE records (
      id TEXT PRIMARY KEY, slug TEXT, title TEXT, original_title TEXT, short_title TEXT,
      jurisdiction TEXT, country TEXT, jurisdiction_level TEXT, region TEXT, issuing_body TEXT,
      instrument_type TEXT, legal_force TEXT, status TEXT,
      date_published TEXT, date_in_force TEXT, date_last_updated TEXT,
      official_identifier TEXT, official_url TEXT, secondary_url TEXT, language TEXT,
      english_version TEXT, english_version_url TEXT, english_version_by TEXT,
      summary TEXT, notes TEXT, scope_note TEXT,
      verification_level TEXT, verified_on TEXT, verification_method TEXT, verification_note TEXT, second_check TEXT,
      local_status TEXT, local_flag TEXT, local_last_attempt TEXT
    );
    CREATE TABLE topics (record_id TEXT REFERENCES records(id), topic TEXT);
    CREATE TABLE related (record_id TEXT REFERENCES records(id), related_id TEXT REFERENCES records(id));
    CREATE TABLE open_questions (record_id TEXT REFERENCES records(id), issue INTEGER, url TEXT, question TEXT);
    CREATE TABLE archive_files (
      record_id TEXT REFERENCES records(id), role TEXT, path TEXT, url TEXT, final_url TEXT,
      http_status INTEGER, content_type TEXT, bytes INTEGER, sha256 TEXT, retrieved_at TEXT,
      last_checked TEXT, method TEXT, last_modified TEXT, warning TEXT, integrity TEXT
    );
    CREATE TABLE archive_attempts (
      record_id TEXT REFERENCES records(id), role TEXT, url TEXT, attempted_at TEXT,
      ok INTEGER, http_status INTEGER, error TEXT
    );
    CREATE INDEX idx_records_country ON records(country);
    CREATE INDEX idx_records_status ON records(status);
    CREATE INDEX idx_records_local ON records(local_status);
    CREATE INDEX idx_topics ON topics(topic);
    """)
    for k, v in (db.get("meta") or {}).items():
        cur.execute("INSERT INTO meta VALUES (?, ?)", (k, json.dumps(v) if isinstance(v, (dict, list)) else str(v)))
    for r in db["records"]:
        v = r.get("verification") or {}
        lc = r.get("local_copy") or {}
        ev = r.get("english_version") or {}
        cur.execute("INSERT INTO records VALUES (" + ",".join(["?"] * 34) + ")", (
            r["id"], r.get("slug"), r.get("title"), r.get("original_title"), r.get("short_title"),
            r.get("jurisdiction"), r.get("country"), r.get("jurisdiction_level"), r.get("region"),
            r.get("issuing_body"), r.get("instrument_type"), r.get("legal_force"), r.get("status"),
            r.get("date_published"), r.get("date_in_force"), r.get("date_last_updated"),
            r.get("official_identifier"), r.get("official_url"), r.get("secondary_url"), r.get("language"),
            ev.get("kind"), ev.get("url"), ev.get("by"),
            r.get("summary"), r.get("notes"), r.get("scope_note"),
            v.get("level"), v.get("verified_on"), v.get("method"), v.get("note"), v.get("second_check"),
            lc.get("status"), " ".join(x for x in (lc.get("flag"), lc.get("integrity_flag")) if x) or None,
            lc.get("last_attempt"),
        ))
        for t in r.get("safety_topics") or []:
            cur.execute("INSERT INTO topics VALUES (?, ?)", (r["id"], t))
        for q in open_questions().get(r["id"], []):
            cur.execute("INSERT INTO open_questions VALUES (?, ?, ?, ?)", (r["id"], q.get("issue"), q.get("url"), q.get("why")))
        for x in r.get("related") or []:
            if x.get("id"):
                cur.execute("INSERT INTO related VALUES (?, ?)", (r["id"], x["id"]))
        for f in lc.get("files") or []:
            cur.execute("INSERT INTO archive_files VALUES (" + ",".join(["?"] * 15) + ")", (
                r["id"], f.get("role"), f.get("path"), f.get("url"), f.get("final_url"), f.get("http_status"),
                f.get("content_type"), f.get("bytes"), f.get("sha256"), f.get("retrieved_at"),
                f.get("last_checked"), f.get("method"), f.get("last_modified"), f.get("warning"),
                f.get("integrity"),
            ))
        for a in lc.get("attempts") or []:
            cur.execute("INSERT INTO archive_attempts VALUES (?, ?, ?, ?, ?, ?, ?)", (
                r["id"], a.get("role"), a.get("url"), a.get("attempted_at"), 1 if a.get("ok") else 0,
                a.get("http_status"), a.get("error"),
            ))
    con.commit()
    con.close()
    tmp.replace(path)


def write_history_md(root=ROOT):
    """HISTORY.md: every event in data/history.jsonl, grouped by run, newest first."""
    events = history.load(root)
    if not events:
        return False
    runs = {}
    for e in events:
        runs.setdefault((e.get("date") or "", e.get("run_id") or "-"), []).append(e)
    lines = ["# Change history", "",
             "Generated by tools/build.py from data/history.jsonl. Every addition, change and re-verification of a record, "
             "and every human check and scope decision, newest first. The evidence for each event (file, SHA-256 and quote) "
             "is in data/history.jsonl; `python3 tools/history.py <ID>` shows one record.", ""]
    for (date, run_id), evs in sorted(runs.items(), key=lambda kv: kv[0], reverse=True):
        report = root / "runs" / run_id / "report.md"
        title = "## %s · %s" % (date, ("[%s](runs/%s/report.md)" % (run_id, run_id)) if report.is_file() else run_id)
        kinds = {}
        for e in evs:
            kinds[e["event"]] = kinds.get(e["event"], 0) + 1
        lines += [title, "", ", ".join("%s %d" % kv for kv in sorted(kinds.items())), ""]
        for e in evs:
            lines.append("- **%s** %s%s" % (e.get("record_id"), history.describe(e),
                                            (" — %s" % e["reason"]) if e.get("reason") else ""))
        lines.append("")
    (root / "HISTORY.md").write_text("\n".join(lines), encoding="utf-8")
    return True


def save(db, root=ROOT):
    """Write records.json atomically and regenerate every derived file."""
    db = normalise(db)
    db.setdefault("meta", {})["record_count"] = len(db["records"])
    tmp = root / "data" / "records.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
        f.write("\n")
    tmp.replace(root / "data" / "records.json")
    write_js(db, root)
    write_csv(db, root)
    write_sqlite(db, root)
    write_history_md(root)
    try:
        import export_xlsx
        export_xlsx.write_xlsx(db, root)
        save.xlsx_written = True
    except ImportError:  # openpyxl is optional; CSV and SQLite are always written
        save.xlsx_written = False


def main():
    db = load()
    errors, _ = validate.run(db)
    if errors:
        print("Not building: fix the %d error(s) above in data/records.json first (or run tools/validate.py)." % len(errors))
        return 1
    save(db)
    counts = {}
    for r in db["records"]:
        s = r["local_copy"]["status"]
        counts[s] = counts.get(s, 0) + 1
    print("Built data/records.js, data/records.csv, data/register.sqlite%s from %d records." % (
        ", data/register.xlsx" if getattr(save, "xlsx_written", False) else " (no register.xlsx: pip install openpyxl)",
        len(db["records"])))
    print("Local copies: " + ", ".join("%s %d" % (k, counts[k]) for k in LOCAL_STATUSES if k in counts))


if __name__ == "__main__":
    sys.exit(main())
