#!/usr/bin/env python3
"""Regenerate the derived data files from data/records.json.

    python3 tools/build.py

Writes:
  data/records.js       the data the web app loads (works from file:// too)
  data/records.csv      one row per record, for spreadsheets
  data/register.sqlite  a relational copy for SQL queries
  data/register.xlsx    an Excel workbook (only when the openpyxl package is installed)
  records/<slug>.html   one static, no-JavaScript page per record, so search engines can index every
                        instrument without running the app (links back to the interactive register)
  sitemap.xml           the site and every record page, for search engines
  HISTORY.md            the change history from data/history.jsonl, newest first, for readers
  README.md             only the numbers between <!--n:key--> and <!--/n--> markers and the BibTeX block
                        between <!-- build:bibtex --> and <!-- /build:bibtex -->, so they follow the data

data/records.json is the single source of truth. Edit it (or let
tools/archive.py update it), then run this script. It first runs the checks in
tools/validate.py and stops if there are errors (unknown vocabulary values,
malformed dates, dangling related IDs, ...), so a bad edit never reaches the app.

Standard library only. Python 3.8+.
"""
import csv
import html as _html
import json
import re
import sqlite3
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import history  # noqa: E402  (same folder)
import validate  # noqa: E402  (same folder)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NAME = "Every AI Policy Ever"
AUTHORS = [("Riegler", "Michael"), ("Gautam", "Sushant")]
DATASET_URL = "https://huggingface.co/datasets/kelkalot/every-ai-policy-ever"
ARCHIVE_URL = "https://huggingface.co/datasets/kelkalot/every-ai-policy-ever-archive"
REPO_URL = "https://github.com/kelkalot/every-ai-policy-ever"
# Where the web app is published; the generated pages and sitemap point here so crawlers
# get absolute URLs even when the folder is served from another host.
SPACE_URL = "https://kelkalot-every-ai-policy-ever.static.hf.space"

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


# ---------- static record pages and sitemap ----------
#
# One page per record, with no JavaScript: search engines that do not render the app
# can still find and read every instrument. The interactive register stays the main
# interface; these pages link back to it.


def _esc(s):
    return _html.escape("" if s is None else str(s), quote=True)


def _when(s):
    return (s or "").replace("T", " ").replace("Z", " UTC").strip()


def _slugmap(db):
    """record ID -> page file name; a collision keeps the record ID as a suffix."""
    out = {}
    for r in db["records"]:
        s = (r.get("slug") or r["id"].lower()).replace("/", "-")
        if s in out.values():
            s = "%s-%s" % (s, r["id"].lower())
        out[r["id"]] = s
    return out


def citation_text(r, meta):
    """The same citation the app's copy button offers."""
    v = r.get("verification") or {}
    f = next((x for x in (r.get("local_copy") or {}).get("files") or [] if not x.get("stale")), None)
    local = "Local copy %s retrieved %s, SHA-256 %s." % (f["path"], _when(f.get("retrieved_at")), f.get("sha256")) if f else ""
    parts = [
        (r.get("issuing_body") or "") + ".",
        (r.get("title") or "") + ((" [%s]" % r["official_identifier"]) if r.get("official_identifier") else "") + ".",
        (r.get("date_published") or "n.d.") + ".",
        r["official_url"] + "." if r.get("official_url") else "",
        "Status: %s; verified %s (level %s)." % (r.get("status"), v.get("verified_on"), v.get("level")),
        local,
        "Every AI Policy Ever, version %s (snapshot %s), record %s." % (meta.get("version"), meta.get("snapshot_date"), r["id"]),
    ]
    return " ".join(p for p in parts if p)


# The same maps and icons assets/app.js uses, so the pages match the drawer exactly.
STATUS_CLASS = {"In force": "s-inforce", "Partially in force": "s-partial",
                "Adopted, not yet in force": "s-adopted", "Published (non-binding, current)": "s-published",
                "Draft / proposed": "s-draft"}
STATUS_SHORT = {"Published (non-binding, current)": "Published, current",
                "Adopted, not yet in force": "Adopted, not in force"}
VLABEL = {"A": "A · official source fetched", "B": "B · alternative official source",
          "C": "C · not confirmed on an official page"}
LC_LABEL = {"archived": "Archived", "archived-review": "Archived, needs review", "partial": "Partial (secondary only)",
            "failed": "Download failed", "no-url": "No URL", "not-attempted": "Not archived"}
LC_HELP = {
    "archived": "The official source was downloaded and stored locally with a SHA-256 hash and timestamp.",
    "archived-review": "A copy is stored, but something needs a human look: a bot-check or JavaScript-only page, a page that no longer mentions the document, a source that has since disappeared, or a local file that changed.",
    "partial": "The official source could not be downloaded; only the secondary source is stored.",
    "failed": "Nothing could be downloaded. The flag gives the reason (HTTP error, timeout, robots.txt, TLS error).",
    "no-url": "The record has no URL, so there is nothing to archive.",
    "not-attempted": "The archiver has not been run for this record yet."}
LC_ICON = {"archived": "ok", "archived-review": "warn", "partial": "warn", "failed": "bad", "no-url": "bad", "not-attempted": "info"}
LC_FLAGCLASS = {"ok": "flag-ok", "warn": "flag-warn", "bad": "flag-bad", "info": "flag-info"}
ICON = {
    "ok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>',
    "warn": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4l9 16H3z"></path><path d="M12 10v4M12 17v.5"></path></svg>',
    "bad": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"></path></svg>',
    "info": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 11v5M12 8v.5"></path></svg>'}


def _fmt_bytes(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if not n:
        return "0 KB"
    if n < 1048576:
        return "%.1f KB" % (n / 1024.0)
    if n < 1073741824:
        return "%.1f MB" % (n / 1048576.0)
    return "%.2f GB" % (n / 1073741824.0)


# The pages link the app's own stylesheet (assets/app.css) and reuse the record
# drawer's markup, so they look exactly like the interactive register. This small
# sheet only adds the page shell the drawer gets from the app layout.
PAGE_CSS = """
.page { max-width: 620px; margin: 0 auto; }
.d-title { font-size: 22px; line-height: 1.22; letter-spacing: -.01em; margin: 6px 0 0; text-wrap: balance; }
.d-head .mono a { color: var(--ink-2); text-decoration: none; }
.d-head .mono a:hover { text-decoration: underline; }
a.relbtn { text-decoration: none; color: var(--ink); }
.page-foot { padding: 18px 22px 40px; border-top: 1px solid var(--line); color: var(--ink-3); font-size: 13px; display: grid; gap: 4px; }
"""


def _fact(label, value, wide=False, mono=False):
    val = "—" if value in (None, "") else value
    dcls = " class=\"wide\"" if wide else ""
    xcls = " class=\"mono\"" if mono else ""
    return "<div%s><dt>%s</dt><dd%s>%s</dd></div>" % (dcls, _esc(label), xcls, _esc(val))


def _record_page(r, db, hist, questions, reverse_rel, slugmap):
    v = r.get("verification") or {}
    lc = r.get("local_copy") or {}
    ev = r.get("english_version") or {}
    meta = db.get("meta") or {}
    rid = r["id"]
    slug = slugmap[rid]
    page_url = "%s/records/%s.html" % (SPACE_URL, slug)
    title = r.get("title") or rid
    desc = r.get("summary") or "%s: official AI safety and AI regulation instruments." % NAME
    if len(desc) > 155:
        desc = desc[:152].rstrip() + "…"

    status = r.get("status") or ""
    sclass = STATUS_CLASS.get(status, "s-gone")
    body = []
    body.append('    <div><div class="d-kicker"><span class="pill %s">%s</span><span>%s</span><span>·</span><span>%s</span></div>'
                '<h1 class="d-title">%s</h1>%s</div>\n' % (
                    sclass, _esc(STATUS_SHORT.get(status, status)),
                    _esc(r.get("legal_force") or ""), _esc(r.get("instrument_type") or ""),
                    _esc(title),
                    ('<p class="orig">%s</p>' % _esc(r["original_title"])) if r.get("original_title") else ""))

    body.append("    <dl class=\"facts\">%s</dl>\n" % "".join([
        _fact("Issued by", r.get("issuing_body"), wide=True),
        _fact("Jurisdiction", r.get("jurisdiction")),
        _fact("Level · region", ("%s · %s" % (r.get("jurisdiction_level"), r.get("region"))) if r.get("jurisdiction_level") else None),
        _fact("Published / adopted", r.get("date_published"), mono=True),
        _fact("In force", r.get("date_in_force"), mono=True),
        _fact("Last updated", r.get("date_last_updated"), mono=True),
        _fact("Language", r.get("language")),
        _fact("Official identifier", r.get("official_identifier"), wide=True, mono=True)]))

    body.append('    <div class="sec"><h3>Summary</h3><p>%s</p></div>\n' % _esc(r.get("summary") or ""))

    # language note, same rule and wording as assets/app.js
    lang = r.get("language") or ""
    english_original = bool(re.match(r"^All 24 official EU languages", lang)) or \
        any(x.strip().lower() == "english" for x in lang.split(","))
    kind = ev.get("kind")
    if kind != "authentic" and not english_original:
        lang_label = _esc(lang or "original-language")
        link = ' <a href="%s" target="_blank" rel="noopener">Open it</a>.' % _esc(ev["url"]) if ev.get("url") else ""
        if kind == "government translation":
            t = "English translation by %s.%s Translations by public bodies are usually provisional or for reference and have no legal force; the %s text is authoritative." % (
                _esc(ev.get("by") or "a public body"), link, lang_label)
        elif kind == "third-party translation":
            t = "English translation by %s, not by a public body.%s The %s text is authoritative." % (
                _esc(ev.get("by") or "a third party"), link, lang_label)
        elif kind == "none found":
            t = "No English version of this instrument was found. The English title and the summary are the register's own, written by an AI agent from the sources below; for the exact wording use the %s text." % lang_label
        else:
            t = "No English version is recorded for this record yet. The English title may be the register's own rendering, and the summary was written by an AI agent from the sources below; for the exact wording use the %s text." % lang_label
        body.append('    <div class="sec"><h3>Language</h3><p>%s</p></div>\n' % t)

    if r.get("safety_topics"):
        body.append('    <div class="sec"><h3>Safety topics</h3><div class="tags">%s</div></div>\n' %
                    "".join('<span class="tag">%s</span>' % _esc(t) for t in r["safety_topics"]))

    if r.get("scope_note"):
        body.append('    <div class="sec"><h3>Scope</h3><p><span class="scope-flag">Borderline scope</span> %s</p></div>\n' % _esc(r["scope_note"]))

    qs = questions.get(rid) or []
    if qs:
        ps = "".join("<p>%s %s</p>" % (_esc(q.get("why") or ""),
                                       ('<a href="%s" target="_blank" rel="noopener">Issue #%s</a>' % (_esc(q.get("url")), _esc(q.get("issue")))) if q.get("url") else "(not filed yet)")
                     for q in qs)
        body.append('    <div class="sec"><h3>Open question</h3>%s<p class="muted">The record shows its last checked values until a maintainer decides; the decision is recorded in its history.</p></div>\n' % ps)

    if r.get("notes"):
        body.append('    <div class="sec"><h3>Status notes</h3><p>%s</p></div>\n' % _esc(r["notes"]))

    # sources
    if r.get("official_url"):
        srcs = ('<a class="src" href="%s" target="_blank" rel="noopener"><span class="k">Official</span>'
                '<span>Open the official source</span><span class="u">%s</span></a>') % (_esc(r["official_url"]), _esc(r["official_url"]))
    else:
        srcs = ""
    if r.get("secondary_url"):
        srcs += ('<a class="src" href="%s" target="_blank" rel="noopener"><span class="k">Second</span>'
                 '<span>Secondary source</span><span class="u">%s</span></a>') % (_esc(r["secondary_url"]), _esc(r["secondary_url"]))
    if not srcs:
        srcs = '<p style="color:var(--bad)">No official URL could be confirmed for this record.</p>'
    body.append('    <div class="sec"><h3>Sources</h3><div class="sources">%s</div></div>\n' % srcs)

    # local copy
    st = lc.get("status")
    ic = "warn" if (lc.get("integrity_flag") and st == "archived") else LC_ICON.get(st, "info")
    lch = '<div class="flag %s">%s<div><strong>%s.</strong> %s%s</div></div>' % (
        LC_FLAGCLASS.get(ic, "flag-info"), ICON[ic],
        LC_LABEL.get(st, "Local copy"), _esc(lc.get("flag") or LC_HELP.get(st, "")),
        ('<br><span class="mono" style="font-size:12px;color:var(--ink-2)">Last attempt %s</span>' % _when(lc.get("last_attempt"))) if lc.get("last_attempt") else "")
    lcf = ""
    for f in lc.get("files") or []:
        if f.get("in_archive_dataset"):
            top = '<a href="%s/blob/main/%s" target="_blank" rel="noopener">%s</a>' % (
                ARCHIVE_URL, _esc(f.get("path") or ""), _esc(f.get("label") or f.get("role") or "Stored file"))
        else:
            top = '<span>%s <span style="color:var(--ink-3)">(third-party copy, not published; see the original URL)</span></span>' % _esc(f.get("label") or f.get("role") or "Stored file")
        mspan = [x for x in (f.get("content_type"), _fmt_bytes(f.get("bytes")) or None,
                             ("HTTP %s" % f["http_status"]) if f.get("http_status") else None,
                             "saved by headless browser" if f.get("method") == "browser" else None,
                             ("server date %s" % f["last_modified"]) if f.get("last_modified") else None) if x]
        warn = ""
        if f.get("stale"):
            warn += '<div class="warn">This source could not be downloaded on %s (%s). This is the earlier copy.</div>' % (_esc((f.get("last_failed") or "")[:10]), _esc(f.get("last_error") or ""))
        if f.get("changed"):
            prev = (' (earlier version: <a href="%s/blob/main/%s" target="_blank" rel="noopener">%s</a>)' % (ARCHIVE_URL, _esc(f["previous_path"]), _esc(f["previous_path"]))) if f.get("previous_path") else ""
            warn += '<div class="warn">Changed since the previous snapshot%s.</div>' % prev
        if f.get("warning"):
            warn += '<div class="warn">%s</div>' % _esc(f["warning"])
        if f.get("redaction_note"):
            warn += '<div class="warn">Published copy: %s. The SHA-256 above is the original page\'s.</div>' % _esc(f["redaction_note"])
        if f.get("integrity") and f["integrity"] != "ok":
            warn += '<div class="warn" style="color:var(--bad)">Integrity check: file %s.</div>' % _esc(f["integrity"])
        lcf += ('<div class="file%s">'
                '<div class="file-top">%s <span class="mono" style="font-size:12px;color:var(--ink-3)">%s</span></div>'
                '<div class="meta"><span>Retrieved %s</span>%s</div>'
                '<div class="hash"><span>SHA-256 %s</span></div>%s</div>' % (
                    " stale" if f.get("stale") else "", top, _esc(f.get("path") or ""),
                    _when(f.get("retrieved_at")),
                    ('<span>unchanged at %s</span>' % _when(f.get("last_checked"))) if (f.get("last_checked") and f.get("last_checked") != f.get("retrieved_at")) else ""
                    + "".join("<span>%s</span>" % _esc(m) for m in mspan),
                    _esc(f.get("sha256") or ""), warn))
    if st != "no-url":
        body.append('    <div class="sec"><h3>Local copy</h3><div class="files">%s%s</div></div>\n' % (lch, lcf))

    # verification
    sc = v.get("second_check")
    body.append('    <div class="sec"><h3>Verification</h3><div class="verify v-%s"><span class="big">%s</span>'
                '<span class="vt">%s</span><span class="vm">checked %s · %s</span><span class="vn">%s</span>%s</div></div>\n' % (
                    _esc(v.get("level") or "?"), _esc(v.get("level") or "?"),
                    _esc(VLABEL.get(v.get("level"), "").replace("A · ", "").replace("B · ", "").replace("C · ", "")),
                    _esc(v.get("verified_on") or ""), _esc(v.get("method") or ""), _esc(v.get("note") or ""),
                    ('<span class="v2"><strong>Second check%s:</strong> %s</span>' % (
                        (", " + _esc(meta.get("snapshot_date") or "")) if sc and not sc.startswith("Independent check") else "", _esc(sc))) if sc else ""))

    # history, newest first
    he = hist.get(rid) or []
    if he:
        def ht(e):
            s = lambda val: ("–" if val in (None, "") else (val if isinstance(val, str) else json.dumps(val)))[:80]
            kind = e.get("event")
            if kind == "changed":
                return "%s: %s → %s" % (e.get("field"), s(e.get("old")), s(e.get("new")))
            return {"added": "Added to the register", "re-verified": "Re-verified against its sources, no change",
                    "human-checked": "Checked by a human: %s" % s(e.get("new")),
                    "scope-decision": "Scope decision: %s" % s(e.get("new")),
                    "source-changed": "A stored source changed", "human-decision": "Maintainer decision"}.get(kind, kind or "")
        rows = ""
        for e in reversed(he):
            who = e.get("tool") or ""
            if e.get("model"):
                who += " (%s)" % e["model"]
            hm = "%s%s%s" % (_esc(e.get("run_id") or ""),
                             ((" · " + who) if who else ""),
                             (" · " + str(e.get("evidence")) + " evidence item" + ("s" if (e.get("evidence") or 0) > 1 else "")) if e.get("evidence") else "")
            rows += ('<li><span class="hd mono">%s</span><span class="ht">%s</span>'
                     '%s%s<span class="hm">%s</span></li>' % (
                         _esc(e.get("date") or ""), _esc(ht(e)),
                         ('<span class="hr">%s</span>' % _esc(e.get("reason"))) if e.get("reason") else "",
                         ('<span class="hq">“%s”</span>' % _esc(e.get("quote"))) if e.get("quote") else "", hm))
        body.append('    <div class="sec"><h3>History</h3><ol class="hist">%s</ol></div>\n' % rows)

    # related records, both directions, as links to the static pages
    fwd = [x.get("id") for x in (r.get("related") or []) if x.get("id") in slugmap and x.get("id") != rid]
    seen = set(fwd)
    rev = [x for x in (reverse_rel.get(rid) or []) if x not in seen and x in slugmap]
    if fwd or rev:
        byid = {x["id"]: x for x in db["records"]}
        rows = "".join('<a class="relbtn" href="%s.html"><span class="mono">%s</span><span>%s <span style="color:var(--ink-3)">· %s</span></span></a>' % (
            slugmap[i], _esc(i), _esc(byid[i].get("short_title") or byid[i].get("title") or i),
            _esc(byid[i].get("status") or "")) for i in fwd + rev)
        body.append('    <div class="sec"><h3>Related records</h3><div class="related">%s</div></div>\n' % rows)

    # improve this record, same links the app builds
    name = rid + " " + (r.get("short_title") or r.get("title") or "")
    news_q = urllib.parse.urlencode({"template": "suggest-instrument.yml", "title": "News or correction: " + name,
                                     "record": rid, "url": r.get("official_url") or "",
                                     "jurisdiction": re.sub(r"-\d+$", "", rid)})
    doc_q = urllib.parse.urlencode({"template": "provide-document.yml", "title": "Document: " + name,
                                    "record": rid, "url": r.get("official_url") or ""})
    need_doc = st != "archived" or bool(lc.get("integrity_flag"))
    imp = ('<p>Know of an amendment, a status change or an error? <a href="%s" target="_blank" rel="noopener">Report news or an error</a>; '
           'the GitHub form opens with this record filled in.</p>') % _esc(REPO_URL + "/issues/new?" + news_q)
    if need_doc:
        imp += ('<p>The official source is not stored as it should be (see Local copy). If you can download it from the official site, '
                '<a href="%s" target="_blank" rel="noopener">provide the document</a>.</p>') % _esc(REPO_URL + "/issues/new?" + doc_q)
    imp += '<p class="muted">What happens next: <a href="../index.html#contribute">Contribute</a>.</p>'
    body.append('    <div class="sec"><h3>Improve this record</h3>%s</div>\n' % imp)

    body.append('    <div class="sec cite"><h3>Citation</h3><textarea readonly aria-label="Citation text" rows="5">%s</textarea></div>\n' %
                _esc(citation_text(r, meta)))

    # JSON-LD
    ld = {
        "@context": "https://schema.org",
        "@type": "GovernmentDocument",
        "name": title,
        "identifier": r.get("official_identifier") or rid,
        "description": r.get("summary") or "",
        "url": page_url,
        "dateCreated": r.get("date_published"),
        "dateModified": r.get("date_last_updated") or v.get("verified_on"),
        "inLanguage": r.get("language"),
        "isAccessibleForFree": True,
        "about": r.get("safety_topics") or [],
        "creator": {"@type": "Organization", "name": r.get("issuing_body") or NAME},
    }
    if r.get("official_url"):
        ld["sourceUrl"] = r["official_url"]
    ld2 = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Register", "item": SPACE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": title, "item": page_url}]}
    ld_text = json.dumps([ld, ld2], ensure_ascii=False, separators=(",", ":"))

    head = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>%s (%s) · %s</title>" % (_esc(title), _esc(rid), _esc(NAME)),
        '<meta name="description" content="%s">' % _esc(desc),
        '<link rel="canonical" href="%s">' % _esc(page_url),
        '<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">',
        '<link rel="stylesheet" href="../assets/app.css">',
        '<style>%s</style>' % PAGE_CSS,
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="%s">' % _esc(NAME),
        '<meta property="og:title" content="%s">' % _esc("%s (%s)" % (title, rid)),
        '<meta property="og:description" content="%s">' % _esc(desc),
        '<meta property="og:url" content="%s">' % _esc(page_url),
        '<meta property="og:image" content="%s/assets/og-image.png">' % SPACE_URL,
        '<meta name="twitter:card" content="summary">',
        '<meta name="twitter:title" content="%s">' % _esc("%s (%s)" % (title, rid)),
        '<meta name="twitter:description" content="%s">' % _esc(desc),
        '<script type="application/ld+json">%s</script>' % ld_text.replace("</", "<\\/"),
        "</head>",
        "<body>",
        '<div class="page">',
        '  <header class="d-head"><span class="mono"><a href="../index.html">%s</a> · <a href="../index.html#%s">%s</a></span>'
        '<span class="mono"><a href="../index.html#%s">open in the interactive register</a></span></header>\n' % (_esc(NAME), _esc(rid), _esc(rid), _esc(rid)),
        '  <main class="d-body">',
    ]
    tail = [
        "  </main>",
        '  <footer class="page-foot"><span>%s · version %s · snapshot %s</span>'
        '<span>an AI-assisted extraction — verified %s (level %s); the original-language text is the authority</span>'
        '<span><a href="../index.html">the interactive register</a> · <a href="%s" rel="noopener">the GitHub repository</a></span></footer>\n' % (
            _esc(NAME), _esc(meta.get("version") or ""), _esc(meta.get("snapshot_date") or ""),
            _esc(v.get("verified_on") or ""), _esc(v.get("level") or ""), _esc(REPO_URL)),
        "</div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(head) + "\n" + "".join(body) + "\n".join(tail) + "\n"


def _records_index(db, slugmap):
    """records/index.html: every record as drawer-style rows, so /records/ matches the register."""
    meta = db.get("meta") or {}
    page_url = SPACE_URL + "/records/"
    recs = sorted(db["records"], key=lambda r: (r.get("date_published") or "", r["id"]), reverse=True)
    rows = "".join('<a class="relbtn" href="%s.html"><span class="mono">%s</span><span>%s <span style="color:var(--ink-3)">· %s · %s</span></span></a>' % (
        slugmap[r["id"]], _esc(r["id"]), _esc(r.get("short_title") or r.get("title") or r["id"]),
        _esc(r.get("jurisdiction") or ""), _esc(r.get("date_published") or "")) for r in recs)
    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>All records · %s</title>" % _esc(NAME),
        '<meta name="description" content="All %d records in %s: official governmental and intergovernmental AI safety and AI regulation instruments, newest first."' % (len(recs), NAME),
        '<link rel="canonical" href="%s">' % _esc(page_url),
        '<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">',
        '<link rel="stylesheet" href="../assets/app.css">',
        "<style>%s</style>" % PAGE_CSS,
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="%s">' % _esc(NAME),
        '<meta property="og:title" content="All records · %s">' % _esc(NAME),
        '<meta property="og:description" content="All %d records, newest first." % len(recs)',
        '<meta property="og:url" content="%s">' % _esc(page_url),
        '<meta property="og:image" content="%s/assets/og-image.png">' % SPACE_URL,
        "</head>",
        "<body>",
        '<div class="page">',
        '  <header class="d-head"><span class="mono"><a href="../index.html">%s</a> · <a href="../index.html">all records</a></span></header>\n' % _esc(NAME),
        '  <main class="d-body">',
        '    <div><div class="d-kicker"><span>All records</span><span>·</span><span>%d instruments, newest first</span></div><h1 class="d-title">All records</h1></div>\n' % len(recs),
        '    <div class="sec"><p>Snapshot %s · version %s. Use the <a href="../index.html">interactive register</a> to search and filter.</p></div>\n' % (_esc(meta.get("snapshot_date") or ""), _esc(meta.get("version") or "")),
        '    <div class="related">%s</div>\n' % rows,
        "  </main>",
        '  <footer class="page-foot"><span>%s · version %s · snapshot %s</span></footer>\n' % (_esc(NAME), _esc(meta.get("version") or ""), _esc(meta.get("snapshot_date") or "")),
        "</div>",
        "</body>",
        "</html>",
    ]) + "\n"


def write_record_pages(db, root=ROOT):
    """One static, no-JavaScript HTML page per record under records/, plus its sitemap."""
    out = root / "records"
    if out.is_dir():
        for f in out.iterdir():  # a record may change its slug; the folder is fully generated
            if f.suffix == ".html":
                f.unlink()
    hist = history_for_app(root)
    questions = open_questions(root)
    slugmap = _slugmap(db)
    ids = set(slugmap)
    reverse = {}
    for r in db["records"]:
        for x in r.get("related") or []:
            if x.get("id") in ids and x["id"] != r["id"]:
                reverse.setdefault(x["id"], []).append(r["id"])
    out.mkdir(parents=True, exist_ok=True)
    for r in db["records"]:
        (out / (slugmap[r["id"]] + ".html")).write_text(
            _record_page(r, db, hist, questions, reverse, slugmap), encoding="utf-8")
    (out / "index.html").write_text(_records_index(db, slugmap), encoding="utf-8")
    return len(db["records"])


def write_sitemap(db, root=ROOT):
    meta = db.get("meta") or {}
    lastmod = meta.get("snapshot_date") or ""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             "  <!-- Generated by tools/build.py. -->"]

    def url(line_loc):
        return "  <url><loc>%s</loc>%s</url>" % (line_loc, ("<lastmod>%s</lastmod>" % lastmod) if lastmod else "")

    lines.append(url(SPACE_URL + "/"))
    lines.append(url(SPACE_URL + "/records/"))
    byid = {r["id"]: r for r in db["records"]}
    slugmap = _slugmap(db)
    for rid in sorted(slugmap, key=lambda i: (byid[i].get("date_published") or "", i)):
        lines.append(url("%s/records/%s.html" % (SPACE_URL, slugmap[rid])))
    lines.append("</urlset>")
    (root / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def bibtex(meta, url=DATASET_URL):
    year = (meta.get("snapshot_date") or "")[:4]
    return ("@dataset{riegler_gautam_%s_every_ai_policy_ever,\n"
            "  title     = {%s: a register of official AI safety and AI regulation instruments},\n"
            "  author    = {%s},\n  year      = {%s},\n  version   = {%s},\n  publisher = {Hugging Face},\n"
            "  url       = {%s},\n  note      = {AI-assisted extraction, snapshot %s}\n}") % (
        year, NAME, " and ".join("%s, %s" % a for a in AUTHORS), year, meta.get("version"), url,
        meta.get("snapshot_date"))


def numbers(db):
    """The figures the README quotes, computed from the data."""
    R = db["records"]
    levels = Counter((r.get("verification") or {}).get("level") for r in R)
    years = [(r.get("date_published") or "")[:4] for r in R if (r.get("date_published") or "")[:4].isdigit()]
    return {"version": db["meta"].get("version"), "records": len(R), "snapshot": db["meta"].get("snapshot_date"),
            "level_A": levels["A"], "level_B": levels["B"], "level_C": levels["C"],
            "countries": len({r.get("country") for r in R if r.get("jurisdiction_level") in ("National", "Sub-national")}),
            "from_2023": sum(1 for y in years if y >= "2023"), "before_2023": sum(1 for y in years if y < "2023"),
            "first_year": min(years) if years else ""}


NUMBER = re.compile(r"<!--n:(\w+)-->.*?<!--/n-->", re.S)
BIBTEX = re.compile(r"(<!-- build:bibtex -->\n).*?(\n<!-- /build:bibtex -->)", re.S)


def write_readme(db, root=ROOT):
    """Put the current figures and citation into README.md, so the documentation does not drift from the data."""
    path = root / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    n = numbers(db)

    def fill(m):
        if m.group(1) not in n:
            raise SystemExit("README.md: no figure called %r (known: %s)" % (m.group(1), ", ".join(sorted(n))))
        return "<!--n:%s-->%s<!--/n-->" % (m.group(1), n[m.group(1)])
    new = NUMBER.sub(fill, text)
    new = BIBTEX.sub(lambda m: m.group(1) + "```bibtex\n" + bibtex(db["meta"]) + "\n```" + m.group(2), new)
    if new != text:
        path.write_text(new, encoding="utf-8")


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
    save.n_pages = write_record_pages(db, root)
    write_sitemap(db, root)
    write_sqlite(db, root)
    write_history_md(root)
    write_readme(db, root)
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
    print("Built records/ (%d static pages) and sitemap.xml." % getattr(save, "n_pages", 0))
    print("Local copies: " + ", ".join("%s %d" % (k, counts[k]) for k in LOCAL_STATUSES if k in counts))


if __name__ == "__main__":
    sys.exit(main())
