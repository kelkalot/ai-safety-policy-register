#!/usr/bin/env python3
"""Write data/register.xlsx, an Excel workbook of the whole register (needs openpyxl).

    python3 tools/export_xlsx.py        # tools/build.py also calls this whenever openpyxl is installed

Sheets
  About            what the file is, when it was generated, a glossary of every column
  Records          one row per instrument, the same 33 columns as records.csv, URLs clickable
  Topics           one row per record and safety topic (long format, ready for pivot tables)
  Related          one row per related-record link
  Local copies     one row per locally stored source file, with hash and retrieval time
  Needs attention  the records whose local copy is missing, partial or needs a review

It is a data export: there are no formulas, so every cell shows its value in any viewer.
Dates are ISO text because some are partial (YYYY-MM or YYYY when the source gives no day).
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

FONT = "Arial"

GLOSSARY = [
    ("id", "Register ID: jurisdiction code plus sequence, e.g. EU-01, US-CA-03."),
    ("title / short_title", "Official title (official English title where one exists) and the common short name."),
    ("original_title", "Title in the original language where it is not English."),
    ("jurisdiction / country / jurisdiction_level / region", "Issuing country, bloc or body; International, Supranational, National or Sub-national; world region."),
    ("issuing_body", "The institution that adopted or issued the instrument."),
    ("instrument_type", "Law, regulation, executive order, guidelines, voluntary code, standard, institute mandate, declaration, treaty, resolution, bill, strategy or report."),
    ("legal_force / status", "Binding, Non-binding or Proposed; current status as of the snapshot."),
    ("date_published / date_in_force / date_last_updated", "Adoption or publication date; entry-into-force date; last amendment, new version, delay or status change. ISO text; YYYY-MM or YYYY when the source gives no exact day."),
    ("official_identifier", "The citable number: CELEX or OJ reference, EO number, CETS number, UN symbol, bill number."),
    ("official_url / secondary_url", "Primary official source and, where useful, a second authoritative source."),
    ("language", "Language(s) of the official text, names only."),
    ("english_version", "Is there an English text? authentic (English is one of the official texts), government translation (by the issuer or another public body; usually provisional, no legal force), third-party translation (by anyone else) or none found. Empty: not checked yet."),
    ("english_version_url", "Link to the English translation, where there is one."),
    ("english_version_by", "Who made the English translation."),
    ("summary / notes", "What the instrument does; status notes, phased dates and caveats."),
    ("open_questions", "Links to GitHub issues with open questions about this record. The record shows its last checked values until a maintainer decides."),
    ("scope_note", "Empty for an instrument clearly in scope. Text for a borderline one: why it is included although it is not a core AI safety or regulation instrument."),
    ("safety_topics", "Topics, separated by '; ' (one row per topic on the Topics sheet)."),
    ("related_ids", "IDs of related records, separated by '; ' (one row per link on the Related sheet)."),
    ("verification_level", "A: confirmed on the official page. B: confirmed on an alternative official page. C: not confirmed on an official page; re-check before citing."),
    ("verified_on / verification_method / verification_note / second_check", "When and how the record was checked, what was confirmed, and any second independent check."),
    ("local_status", "archived: official source stored. archived-review: stored but needs a human look. partial: only the secondary source stored. failed: nothing stored. no-url: nothing to archive. not-attempted: archiver not run yet."),
    ("local_flag / local_last_attempt", "Why a record is not cleanly archived, and when the archiver last tried."),
    ("local_files / local_sha256", "Paths of the stored files under archive/ and their SHA-256 hashes, separated by '; '."),
]

WIDTHS = {"id": 10, "title": 48, "original_title": 32, "short_title": 34, "jurisdiction": 24, "country": 16,
          "jurisdiction_level": 14, "region": 20, "issuing_body": 36, "instrument_type": 24, "legal_force": 12,
          "status": 24, "date_published": 13, "date_in_force": 13, "date_last_updated": 13, "official_identifier": 28,
          "official_url": 44, "secondary_url": 44, "language": 16, "english_version": 18, "english_version_url": 30, "english_version_by": 24, "summary": 60, "safety_topics": 36, "related_ids": 20,
          "notes": 60, "verification_level": 10, "verified_on": 12, "verification_method": 36, "verification_note": 50,
          "second_check": 40, "local_status": 14, "local_flag": 50, "local_last_attempt": 20, "local_files": 44,
          "local_sha256": 30}
WRAP = {"summary", "notes", "verification_note", "second_check", "local_flag", "issuing_body", "title", "flag", "meaning"}


def _styles():
    from openpyxl.styles import Alignment, Font, PatternFill
    return {
        "base": Font(name=FONT, size=10), "bold": Font(name=FONT, size=10, bold=True),
        "title": Font(name=FONT, size=14, bold=True), "muted": Font(name=FONT, size=10, color="595959"),
        "link": Font(name=FONT, size=10, color="0563C1", underline="single"),
        "fill": PatternFill("solid", fgColor="E7E6E6"),
        "wrap": Alignment(wrap_text=True, vertical="top"), "top": Alignment(vertical="top"),
    }


def add_table(ws, headers, rows, st, widths=None, link_cols=(), number_cols=()):
    """Header row, frozen and filterable, then the rows; URLs become hyperlinks."""
    from openpyxl.utils import get_column_letter
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = st["bold"]; cell.fill = st["fill"]; cell.alignment = st["top"]
        ws.column_dimensions[get_column_letter(c)].width = (widths or {}).get(h, WIDTHS.get(h, 18))
    for r, row in enumerate(rows, 2):
        for c, (h, v) in enumerate(zip(headers, row), 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = st["base"]
            cell.alignment = st["wrap"] if h in WRAP else st["top"]
            if h in link_cols and isinstance(v, str) and v.startswith(("http://", "https://")):
                cell.hyperlink = v; cell.font = st["link"]
            if h in number_cols and isinstance(v, int):
                cell.number_format = "#,##0"
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(headers)), len(rows) + 1)
    ws.sheet_view.zoomScale = 100


def write_xlsx(db, root=build.ROOT):
    from openpyxl import Workbook
    st = _styles()
    R = db["records"]; meta = db.get("meta") or {}
    by = {r["id"]: r for r in R}
    wb = Workbook(); wb.remove(wb.active)

    # About ---------------------------------------------------------------------------------------
    ws = wb.create_sheet("About")
    ws.column_dimensions["A"].width = 44; ws.column_dimensions["B"].width = 110
    counts = {}
    for r in R:
        s = (r.get("local_copy") or {}).get("status", "not-attempted"); counts[s] = counts.get(s, 0) + 1
    lines = [
        (meta.get("name", "Every AI Policy Ever"), None, "title"),
        ("Data export of the register: every record, its topics and links, and the local copies of its sources.", None, "muted"),
        (None, None, None),
        ("Snapshot date", meta.get("snapshot_date"), None),
        ("Version", meta.get("version"), None),
        ("Records", len(R), None),
        ("Generated (UTC)", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), None),
        ("Source of truth", "data/records.json (this workbook, records.csv and register.sqlite are generated from it by tools/build.py)", None),
        ("Local copies", ", ".join("%s %d" % (k, counts[k]) for k in build.LOCAL_STATUSES if k in counts), None),
        (None, None, None),
        ("Sheets", None, "bold"),
        ("Records", "One row per instrument; the same columns as records.csv. Official and secondary URLs are clickable.", None),
        ("Topics", "One row per record and safety topic, for pivot tables and counts.", None),
        ("Related", "One row per related-record link, in the direction recorded in the data.", None),
        ("Local copies", "One row per stored source file: path under archive/, SHA-256, retrieval time, HTTP status.", None),
        ("Needs attention", "Records whose official source is not cleanly archived, with the reason. The same list is in archive/needs-attention.txt.", None),
        (None, None, None),
        ("Column glossary (Records sheet)", None, "bold"),
    ] + [(f, m, None) for f, m in GLOSSARY] + [
        (None, None, None),
        ("How to cite a record", "Issuing body. Title [identifier]. Date. Official URL. Status; verified <date> (level). Local copy <path> retrieved <time>, SHA-256 <hash>. Every AI Policy Ever, version <version> (snapshot <date>), record <ID>.", None),
        ("Notes", "Dates are ISO text, shortened to YYYY-MM or YYYY when the source gives no exact day. Multi-valued cells use '; ' as the separator. Nothing in this file is computed by formulas.", None),
    ]
    for i, (a, b, kind) in enumerate(lines, 1):
        ca = ws.cell(row=i, column=1, value=a); cb = ws.cell(row=i, column=2, value=b)
        ca.font = st["title"] if kind == "title" else st["muted"] if kind == "muted" else st["bold"] if kind == "bold" or b is not None else st["base"]
        cb.font = st["base"]; cb.alignment = st["wrap"]; ca.alignment = st["top"]

    # Records -------------------------------------------------------------------------------------
    rows = [[build.flat(r).get(c) for c in build.CSV_COLS] for r in R]
    add_table(wb.create_sheet("Records"), build.CSV_COLS, rows, st, link_cols=("official_url", "secondary_url"))

    # Topics / Related ----------------------------------------------------------------------------
    add_table(wb.create_sheet("Topics"), ["record_id", "short_title", "topic"],
              [[r["id"], r.get("short_title"), t] for r in R for t in (r.get("safety_topics") or [])], st,
              widths={"record_id": 12, "short_title": 44, "topic": 32})
    add_table(wb.create_sheet("Related"), ["record_id", "short_title", "related_id", "related_short_title"],
              [[r["id"], r.get("short_title"), x["id"], (by.get(x["id"]) or {}).get("short_title")]
               for r in R for x in (r.get("related") or []) if x.get("id")], st,
              widths={"record_id": 12, "short_title": 44, "related_id": 12, "related_short_title": 44})

    # Local copies --------------------------------------------------------------------------------
    cols = ["record_id", "role", "path", "url", "final_url", "http_status", "content_type", "bytes", "sha256",
            "retrieved_at", "last_checked", "method", "last_modified", "warning", "stale", "integrity"]
    rows = []
    for r in R:
        for f in (r.get("local_copy") or {}).get("files") or []:
            rows.append([r["id"], f.get("label") or f.get("role"), f.get("path"), f.get("url"), f.get("final_url"),
                         f.get("http_status"), f.get("content_type"), f.get("bytes"), f.get("sha256"), f.get("retrieved_at"),
                         f.get("last_checked"), f.get("method"), f.get("last_modified"), f.get("warning"),
                         "yes" if f.get("stale") else "", f.get("integrity")])
    add_table(wb.create_sheet("Local copies"), cols, rows, st,
              widths={"record_id": 12, "role": 26, "path": 46, "url": 44, "final_url": 44, "http_status": 10,
                      "content_type": 18, "bytes": 12, "sha256": 66, "retrieved_at": 20, "last_checked": 20, "method": 9,
                      "last_modified": 30, "warning": 50, "stale": 7, "integrity": 10},
              link_cols=("url", "final_url"), number_cols=("bytes",))

    # Needs attention -----------------------------------------------------------------------------
    cols = ["record_id", "short_title", "jurisdiction", "local_status", "flag", "official_url", "secondary_url", "last_attempt"]
    rows = []
    for r in R:
        lc = r.get("local_copy") or {}
        if lc.get("status", "not-attempted") != "archived" or lc.get("integrity_flag"):
            rows.append([r["id"], r.get("short_title"), r.get("jurisdiction"), lc.get("status"),
                         " ".join(x for x in (lc.get("flag"), lc.get("integrity_flag")) if x), r.get("official_url"),
                         r.get("secondary_url"), lc.get("last_attempt")])
    add_table(wb.create_sheet("Needs attention"), cols, rows, st,
              widths={"record_id": 12, "short_title": 44, "jurisdiction": 24, "local_status": 16, "flag": 70,
                      "official_url": 44, "secondary_url": 44, "last_attempt": 20},
              link_cols=("official_url", "secondary_url"))

    out = root / "data" / "register.xlsx"
    tmp = out.with_suffix(".xlsx.tmp")
    wb.save(tmp); tmp.replace(out)
    return out


def main():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("openpyxl is not installed. Install it with: python3 -m pip install openpyxl"); return 1
    out = write_xlsx(build.normalise(build.load()))
    print("Wrote", out.relative_to(build.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
