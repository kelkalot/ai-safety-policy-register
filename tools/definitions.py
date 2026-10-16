#!/usr/bin/env python3
"""The definitions layer of the crosswalk (issue #70): defined terms quoted verbatim from the stored sources of
records, checked by script and compared between two independent extractions.

    python3 tools/definitions.py textify --run RUN   # text of the stored files of the records in RUN/plan.json
    python3 tools/definitions.py check   --run RUN   # every quote in definitions/ and definitions-blind/ against its file
    python3 tools/definitions.py compare --run RUN   # agreement between the two extractions
    python3 tools/definitions.py merge   --run RUN   # add the checked definitions to data/definitions.json
    python3 tools/definitions.py report  --run RUN   # RUN/report.md with the definitions side by side

RUN/plan.json: {"records": ["EU-03", ...], "term_groups": ["AI system", "model"]}
RUN/definitions/<RECORD>.json (and definitions-blind/ for the second extraction):
  {"record_id": "EU-03", "definitions": [{"term": "AI system", "term_group": "AI system",
    "definition": "<verbatim>", "english": "<only when the text is not English>", "english_by": "issuer | agent",
    "file": "archive/...", "sha256": "...", "locator": "Article 3(1)", "language": "English"}],
   "not_found": ["model"], "note": "..."}
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402  (same folder)

ROOT = P.ROOT
DEFS = ROOT / "data" / "definitions.json"
TERM_GROUPS = ["AI system", "artificial intelligence", "model", "AI model", "general-purpose AI model",
               "automated decision system", "generative AI", "high-risk AI system", "provider", "deployer"]
MAX_QUOTE = 1200  # a definition is the data itself, so it may be longer than an evidence quote


def run_dir(run):
    d = ROOT / "runs" / run
    if not (d / "plan.json").is_file():
        raise SystemExit("runs/%s/plan.json is missing" % run)
    return d, P.read_json(d / "plan.json")


def record_files(db, rid):
    rec = {r["id"]: r for r in db["records"]}.get(rid)
    if not rec:
        raise SystemExit("No record %s" % rid)
    out = {}
    for f in (rec.get("local_copy") or {}).get("files") or []:
        for path, digest in ((f.get("path"), f.get("sha256")), (f.get("previous_path"), f.get("previous_sha256"))):
            if path and (ROOT / path).is_file():
                out[path] = digest
    return out


def text_path(d, path):
    return d / "texts" / (path.replace("archive/", "", 1).replace("/", "__") + ".txt")


def cmd_textify(args):
    d, plan = run_dir(args.run)
    db = P.load_db()
    rows = []
    for rid in plan["records"]:
        for path, digest in record_files(db, rid).items():
            src, out = ROOT / path, text_path(d, path)
            ext = src.suffix.lower()
            if ext == ".pdf":
                text = P.pdf_text(src, args.ocr_lang)[0]
            elif ext in (".html", ".xml"):
                text = P.html_text(src)[0]
            elif ext == ".txt":
                text = src.read_text(encoding="utf-8", errors="replace")
            else:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            rows.append({"record_id": rid, "file": path, "sha256": digest, "text": str(out.relative_to(ROOT)),
                         "chars": len(text)})
    P.write_json(d / "texts.json", {"files": rows})
    print("Text for %d file(s) of %d record(s); listed in runs/%s/texts.json" % (len(rows), len(plan["records"]), args.run))
    return 0


def locator_key(loc):
    """The article or section numbers of a locator, so that "Art. 3(1)" and "Article 3(1), page 46" agree."""
    s = P.re.sub(r"\bpages?\s*\d+", " ", (loc or "").lower())
    toks = P.re.findall(r"\d+|\b[ivxlc]+\b", s)
    return tuple(toks[:2]) if toks else (P.loose(s)[:12],)


def load_extractions(d, sub):
    return {p.stem: P.read_json(p) for p in sorted((d / sub).glob("*.json"))}


def check_one(db, d, texts, rid, item):
    problems = []
    files = record_files(db, rid)
    path, quote = item.get("file") or "", item.get("definition") or ""
    if item.get("term_group") not in TERM_GROUPS:
        problems.append("term_group %r is not in the vocabulary" % item.get("term_group"))
    if path not in files:
        problems.append("%s is not a stored file of %s" % (path, rid))
    elif (files[path] or "") != (item.get("sha256") or ""):
        problems.append("the SHA-256 does not match the stored file")
    if not quote or len(quote) > MAX_QUOTE:
        problems.append("the definition is empty or longer than %d characters" % MAX_QUOTE)
    if path in files and quote:
        tp = text_path(d, path)
        body = texts.setdefault(path, P.norm_text(tp.read_text(encoding="utf-8")) if tp.is_file() else "")
        if not body:
            problems.append("no text layer for %s (run textify)" % path)
        elif P.norm_text(quote) not in body and P.loose(quote) not in P.loose(body):
            problems.append("the definition is not found in the stored text")
    if not item.get("locator"):
        problems.append("no locator")
    return problems


def cmd_check(args):
    d, plan = run_dir(args.run)
    db, texts, result, bad = P.load_db(), {}, {}, 0
    for sub in ("definitions", "definitions-blind"):
        for rid, ex in load_extractions(d, sub).items():
            for i, item in enumerate(ex.get("definitions") or []):
                problems = check_one(db, d, texts, rid, item)
                result.setdefault(sub, {}).setdefault(rid, []).append({"index": i, "term": item.get("term"),
                                                                       "ok": not problems, "problems": problems})
                bad += bool(problems)
                if problems:
                    print("%-18s %-8s %-28s %s" % (sub, rid, (item.get("term") or "")[:28], "; ".join(problems)))
    P.write_json(d / "check.json", result)
    n = sum(len(v) for s in result.values() for v in s.values())
    print("%d definition(s) checked, %d with problems. Written runs/%s/check.json" % (n, bad, args.run))
    return 1 if bad else 0


def cmd_compare(args):
    d, plan = run_dir(args.run)
    a, b = load_extractions(d, "definitions"), load_extractions(d, "definitions-blind")
    pairs, rows = 0, []
    agree_text = agree_loc = 0
    for rid in sorted(set(a) & set(b)):
        by_a = {x.get("term_group"): x for x in a[rid].get("definitions") or []}
        by_b = {x.get("term_group"): x for x in b[rid].get("definitions") or []}
        for g in sorted(set(by_a) | set(by_b)):
            x, y = by_a.get(g), by_b.get(g)
            if not (x and y):
                rows.append({"record_id": rid, "term_group": g, "text": "only in %s" % ("first" if x else "blind"),
                             "locator": None})
                pairs += 1
                continue
            lx, ly = P.loose(x["definition"]), P.loose(y["definition"])
            same = lx == ly or (min(len(lx), len(ly)) > 40 and (lx in ly or ly in lx))
            loc = locator_key(x.get("locator")) == locator_key(y.get("locator"))
            pairs += 1
            agree_text += same
            agree_loc += loc
            rows.append({"record_id": rid, "term_group": g, "text": "same" if same else "differs",
                         "locator": "same" if loc else "differs"})
    out = {"pairs": pairs, "same_definition": agree_text, "same_locator": agree_loc, "rows": rows}
    P.write_json(d / "agreement.json", out)
    for r in rows:
        print("%-8s %-26s definition %-14s locator %s" % (r["record_id"], r["term_group"], r["text"], r["locator"]))
    print("Agreement: %d of %d pairs quote the same definition, %d the same locator." % (agree_text, pairs, agree_loc))
    return 0


def cmd_merge(args):
    d, plan = run_dir(args.run)
    check = P.read_json(d / "check.json", {}) or {}
    agreed = {(r["record_id"], r["term_group"]) for r in (P.read_json(d / "agreement.json", {}) or {}).get("rows") or []
              if r.get("text") == "same"}
    reg = P.read_json(DEFS, {}) or {}
    reg.setdefault("about", "Defined terms quoted verbatim from the stored sources of records (issue #70), checked by "
                            "tools/definitions.py. Similar definitions are not legally equivalent; nothing here is "
                            "legal advice.")
    items = reg.setdefault("definitions", [])
    have = {(x["record_id"], x["term_group"]) for x in items}
    n = max([int(x["id"][1:]) for x in items] + [0])
    added = 0
    for rid, ex in load_extractions(d, "definitions").items():
        oks = {c["index"] for c in (check.get("definitions") or {}).get(rid) or [] if c["ok"]}
        for i, item in enumerate(ex.get("definitions") or []):
            if i not in oks or (rid, item["term_group"]) in have or (rid, item["term_group"]) not in agreed:
                continue
            n += 1
            items.append(dict({"id": "D%04d" % n, "record_id": rid}, **{k: item.get(k) for k in (
                "term", "term_group", "definition", "english", "english_by", "language", "locator", "file", "sha256")},
                run_id=args.run))
            added += 1
    if not args.dry_run:
        P.write_json(DEFS, reg)
    print("%d definition(s) added to data/definitions.json%s" % (added, " (dry run)" if args.dry_run else ""))
    return 0


def cmd_report(args):
    d, plan = run_dir(args.run)
    db = P.load_db()
    by = {r["id"]: r for r in db["records"]}
    reg = P.read_json(DEFS, {}) or {}
    agr = P.read_json(d / "agreement.json", {}) or {}
    mine = [x for x in reg.get("definitions") or [] if x.get("run_id") == args.run]
    L = ["# Definitions pilot %s" % args.run, "",
         "Defined terms quoted verbatim from the stored sources of %d records (issue #70). Every quote was checked "
         "against its stored file and SHA-256 by `tools/definitions.py check`. Similar definitions are not legally "
         "equivalent; nothing here is legal advice." % len(plan["records"]), "",
         "**Repeatability:** %s of %s pairs from two independent extractions quote the same definition, %s the same "
         "locator." % (agr.get("same_definition"), agr.get("pairs"), agr.get("same_locator")), ""]
    for g in TERM_GROUPS:
        rows = [x for x in mine if x["term_group"] == g]
        if not rows:
            continue
        L += ["## %s" % g, "", "| Record | Term | Definition | Where |", "|---|---|---|---|"]
        for x in rows:
            text = x["definition"].replace("|", "\\|").replace("\n", " ")
            if x.get("english"):
                text += " *(English%s: %s)*" % (" by the issuer" if x.get("english_by") == "issuer" else
                                               ", agent's rendering", x["english"].replace("|", "\\|"))
            L.append("| %s %s | %s | %s | %s |" % (x["record_id"], (by.get(x["record_id"]) or {}).get("short_title", ""),
                                                   x["term"], text, x["locator"]))
        L.append("")
    review = [r for r in agr.get("rows") or [] if r.get("text") != "same"]
    if review:
        L += ["## For review: found by one extraction only, or quoted differently", "",
              "These are not in `data/definitions.json`; only definitions both extractions found and quoted alike are.", ""]
        L += ["- %s, %s: %s" % (r["record_id"], r["term_group"], r["text"]) for r in review] + [""]
    missing = [(rid, ex.get("not_found")) for rid, ex in load_extractions(d, "definitions").items() if ex.get("not_found")]
    if missing:
        L += ["## Not defined in the stored text", ""] + ["- %s: %s" % (rid, ", ".join(nf)) for rid, nf in missing] + [""]
    (d / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("Written runs/%s/report.md (%d definitions)" % (args.run, len(mine)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Definitions layer of the crosswalk (issue #70).")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("textify", "check", "compare", "merge", "report"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
        if name == "textify":
            s.add_argument("--ocr-lang", default="eng")
        if name == "merge":
            s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1
    return {"textify": cmd_textify, "check": cmd_check, "compare": cmd_compare, "merge": cmd_merge,
            "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
