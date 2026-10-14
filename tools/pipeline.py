#!/usr/bin/env python3
"""The scripts of the pipeline in AGENTS.md sections 5 to 7. Agents do the reading and judging;
this file does the bookkeeping, so that a run can be repeated and checked.

    python3 tools/pipeline.py new --type discover --scope "region:Europe" [--tool T --model M]
    python3 tools/pipeline.py new --type refresh [--scope "ids:EU-03,US-09"]     # default: the queue
    python3 tools/pipeline.py new --type recheck --scope "region:Oceania"
    python3 tools/pipeline.py status   --run RUN
    python3 tools/pipeline.py stage    --run RUN --stage extract --tool "Claude Code" --model M
    python3 tools/pipeline.py dedupe   --run RUN     # number candidates, drop duplicates, update the frame
    python3 tools/archive.py --run RUN --browser     # (the archiver) store the candidates' sources
    python3 tools/pipeline.py textify  --run RUN     # a .txt with [page N] markers next to every stored file
    python3 tools/pipeline.py evidence --run RUN     # check quotes and hashes, compute levels, flag rule breaches
    python3 tools/pipeline.py sample   --run RUN     # pick the blind double-extraction sample
    python3 tools/pipeline.py compare  --run RUN     # field agreement between the two extractions
    python3 tools/pipeline.py assemble --run RUN     # runs/RUN/pass.json for tools/merge.py
    python3 tools/pipeline.py report   --run RUN     # runs/RUN/report.md
    python3 tools/pipeline.py queue [--days 180] [--limit 25]
    python3 tools/pipeline.py frame --due [--days 180] | --report | --add CODE --name N --level L --region R
    python3 tools/pipeline.py hosts [--code C] [--pending]        # the curated list of official sites
    python3 tools/pipeline.py questions [--sync] [--apply] [--dry-run]   # open questions as GitHub issues
    python3 tools/pipeline.py hosts --add HOST --code C --status official|"not official"|proposed --by NAME
                                    [--operator O --kind K --evidence-url U --quote Q --note N]
    python3 tools/pipeline.py log-human --run RUN --id ID --result ok|problem --note "..." [--by NAME]
    python3 tools/pipeline.py log-scope --id ID --decision in|out --note "..." [--by NAME] [--run RUN]

Files of a run, all under runs/RUN/ (AGENTS.md section 5.1):
  run.json              type, scope, groups of frame cells or record IDs, tool and model per stage
  candidates/<g>.json   collectors' output, one file per group
  search-log.jsonl      one line per frame cell searched
  candidates.json       written by dedupe: every candidate with a status; active ones are C001, C002, ...
  sources.json          written by tools/archive.py --run: the stored files per candidate
  texts.json            written by textify: the text file, hash and page count of every stored file
  extractions/<c>.json, extractions-blind/<c>.json, checks/<c>.json    the agents' output
  evidence.json, sample.json, agreement.json, pass.json, report.md     written here

Standard library only (Python 3.8+). PDFs need pypdf or poppler's pdftotext; scans need tesseract.
"""
import argparse
import datetime as dt
import difflib
import hashlib
import json
import math
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
from collections import Counter, OrderedDict, defaultdict
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import history  # noqa: E402
import publish_hf  # noqa: E402  (its list of third-party hosts)
import validate  # noqa: E402

ROOT = build.ROOT
RUNS = ROOT / "runs"
FRAME = ROOT / "pipeline" / "frame.json"
REQUESTS = ROOT / "pipeline" / "refresh-requests.jsonl"
SITES = ROOT / "pipeline" / "official-sites.json"
SITE_STATUSES = ["official", "not official", "proposed"]
SCOPE_DECISIONS = ROOT / "pipeline" / "scope-decisions.md"

RUN_TYPES = ["discover", "refresh", "recheck"]
FACT_FIELDS = ["title", "original_title", "issuing_body", "official_identifier", "date_published", "date_in_force",
               "date_last_updated", "status", "legal_force"]
LEVEL_FIELDS = ["title", "date_published", "status"]   # date_published only counts when it is not null
SOURCE_KINDS = ["official", "alt-official", "secondary"]
DECISIONS = ["record", "update", "duplicate", "out-of-scope", "needs-human"]
VERDICTS = ["supported", "unsupported", "contradicted", "judgment-differs"]
OVERALL = ["accept", "accept-with-fixes", "needs-human", "reject"]
METHOD_TOKENS = {"A": "official-url-fetched", "B": "alternative-official-url-fetched", "C": "search-confirmed"}
RECORD_FIELDS = ["id", "slug", "title", "original_title", "short_title", "jurisdiction", "country", "jurisdiction_level",
                 "region", "issuing_body", "instrument_type", "legal_force", "status", "date_published", "date_in_force",
                 "date_last_updated", "official_identifier", "official_url", "secondary_url", "language", "summary",
                 "safety_topics", "related", "notes", "scope_note", "english_version", "verification"]
SET_BY_SCRIPT = {"id", "slug"}
IN_FORCE = {"In force", "Partially in force"}
ENDED = {"Superseded", "Revoked / withdrawn", "Lapsed"}
CURRENT = IN_FORCE | ENDED | {"Published (non-binding, current)"}  # statuses a passed in-force date does not contradict
QUOTE_MAX = 300
QUOTE_MIN_ALNUM = 8   # a quote needs at least this many letters or digits to identify a passage ("2026" is not enough)
# Which stored files can count as official evidence. The archiver sets a file's role; an agent only labels its quotes,
# so a label is capped by the role and by the host the file came from.
SECONDARY_ROLES = {"secondary"}
GOV_HOST = re.compile(r"\.(gov|mil|int)$|(^|\.)(gov|gob|gouv|govt|gv|go|gub|mil|admin|gc|leg)\.[a-z]{2,3}$"
                      r"|\.state\.[a-z]{2}\.us$"
                      r"|(^|\.)(europa\.eu|un\.org|unesco\.org|oecd\.org|oecd\.ai|wto\.org|asean\.org)$")
NOT_OFFICIAL_HOSTS = set(publish_hf.THIRD_PARTY_HOSTS)
SUMMARY_MIN, SUMMARY_MAX = 250, 700
TOPICS_MIN, TOPICS_MAX = 2, 6
STALE_DAYS = 180
PROCESS_PATTERNS = [
    r"\bfetch(?:ed|ing)?\b", r"\b(?:could|can) ?not be (?:fetched|confirmed|verified|retrieved|reached|downloaded|found)\b",
    r"\bwas not (?:confirmed|verified|fetched)\b", r"\bnot (?:been )?(?:confirmed|verified) (?:on|from|against)\b",
    r"\bas (?:reported|summari[sz]ed)\b", r"\breported(?:ly)? to (?:include|cover|contain)\b", r"\bHTTP \d{3}\b",
    r"\brobots\.txt\b", r"\bweb search\b", r"\bsearch budget\b", r"\bthe researcher\b", r"\bthis (?:machine|session)\b",
    r"\b(?:law[- ]firm|counsel)'?s? (?:summary|summaries|analysis|note)\b", r"\bbot[- ]check\b",
]
STAGES = ["collect", "extract", "blind", "check"]


# ----------------------------------------------------------------------------- small helpers

def today():
    return dt.date.today().isoformat()


def read_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def rel(p):
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def slugify(s, n=60):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:n].rstrip("-")) or "x"


def norm_title(t):
    return " ".join(re.findall(r"\w+", (t or "").casefold()))


def norm_url(u):
    if not u:
        return ""
    p = urllib.parse.urlsplit(u.strip())
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = urllib.parse.unquote(p.path).rstrip("/")
    return host + path + (("?" + p.query) if p.query else "")


def sha256_file(path, _cache={}):
    path = Path(path)
    key = (str(path), path.stat().st_mtime, path.stat().st_size)
    if key not in _cache:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _cache[key] = h.hexdigest()
    return _cache[key]


def run_path(run_id):
    d = RUNS / run_id
    if not (d / "run.json").is_file():
        raise SystemExit("No run %r: runs/%s/run.json is missing. Create one with: python3 tools/pipeline.py new" % (run_id, run_id))
    return d


def load_run(run_id):
    d = run_path(run_id)
    return d, read_json(d / "run.json")


def save_run(d, run):
    write_json(d / "run.json", run)


def load_db():
    return build.normalise(build.load())


def candidates(d):
    return (read_json(d / "candidates.json", {}) or {}).get("candidates") or []


def active(d):
    return [c for c in candidates(d) if c.get("status") == "active"]


def agent_files(d, sub):
    out = {}
    folder = d / sub
    if folder.is_dir():
        for p in sorted(folder.glob("*.json")):
            try:
                out[p.stem] = read_json(p)
            except ValueError as e:
                out[p.stem] = {"_error": "not valid JSON: %s" % e}
    return out


def parse_date(s):
    try:
        return dt.date.fromisoformat(str(s)) if s and validate.FULL_DATE.match(str(s)) else None
    except ValueError:
        return None


# ----------------------------------------------------------------------------- frame

def load_frame():
    f = read_json(FRAME)
    if not f:
        raise SystemExit("pipeline/frame.json is missing")
    return f


def save_frame(f):
    write_json(FRAME, f)


def strip_www(host):
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def load_sites(path=SITES):
    """pipeline/official-sites.json, the curated list of sites (AGENTS.md section 7.6). Every entry says who runs the
    host, how that was established and who decided; entries are never deleted, so a decision is not undone later."""
    data = read_json(path, None) or {"about": "", "sites": []}
    problems, seen = [], set()
    for i, e in enumerate(data.get("sites") or []):
        key = (e.get("code"), strip_www(e.get("host")))
        if not all(key):
            problems.append("entry %d needs code and host" % (i + 1))
        if e.get("status") not in SITE_STATUSES:
            problems.append("%s %s: status must be one of %s" % (key + (", ".join(SITE_STATUSES),)))
        if e.get("status") in ("official", "not official") and not (e.get("decided_by") and e.get("decided_on")):
            problems.append("%s %s: a decision needs decided_by and decided_on" % key)
        if key in seen:
            problems.append("%s %s is listed twice" % key)
        seen.add(key)
    if problems:
        raise SystemExit("pipeline/official-sites.json: " + "; ".join(problems[:10]))
    return data


def site_hosts(data):
    """(code -> hosts that count as official, hosts that never count as official)."""
    official, rejected = defaultdict(list), set()
    for e in data.get("sites") or []:
        if e["status"] == "official":
            official[e["code"]].append(strip_www(e["host"]))
        elif e["status"] == "not official":
            rejected.add(strip_www(e["host"]))
    return official, rejected


def frame_cells(f):
    for j in f["jurisdictions"]:
        for t, cell in j["cells"].items():
            yield j, t, cell


def frame_names(_cache=[]):
    if not _cache:
        try:
            _cache.append({j["name"] for j in load_frame()["jurisdictions"]})
        except SystemExit:
            _cache.append(set())
    return _cache[0]


def cell_id(j, t):
    return "%s/%s" % (j["code"], t)


def select_frame(f, scope, days):
    """Resolve a discover scope to frame cells. Selectors (space-separated, combined with AND):
    region:<text>  codes:FI,SE  level:National  types:legislature,gazette  due  all"""
    toks = shlex.split(scope or "")
    if not toks:
        raise SystemExit("A discover run needs --scope, e.g. 'region:Europe', 'codes:FI,SE,NO', 'due', 'all'")
    regions, codes, levels, types, due = [], set(), [], set(), False
    for t in toks:
        k, _, v = t.partition(":")
        k = k.lower()
        if k == "region":
            regions.append(v.casefold())
        elif k == "codes":
            codes |= {x.strip().upper() for x in v.split(",") if x.strip()}
        elif k == "level":
            levels.append(v.casefold())
        elif k == "types":
            types |= {x.strip() for x in v.split(",") if x.strip()}
        elif k == "due":
            due = True
        elif k == "all":
            pass
        else:
            raise SystemExit("Unknown scope selector %r; use region:, codes:, level:, types:, due or all" % t)
    known = {j["code"] for j in f["jurisdictions"]}
    unknown = sorted(codes - known)
    if unknown:
        raise SystemExit("Not in pipeline/frame.json: %s. Add them with: pipeline.py frame --add" % ", ".join(unknown))
    out = []
    for j, t, cell in frame_cells(f):
        if regions and not any(r in j["region"].casefold() for r in regions):
            continue
        if codes and j["code"] not in codes:
            continue
        if levels and not any(l in j["level"].casefold() for l in levels):
            continue
        if types and t not in types:
            continue
        if due and not cell_due(cell, days):
            continue
        out.append(cell_id(j, t))
    return out


def cell_due(cell, days):
    d = parse_date(cell.get("last_searched"))
    return d is None or (dt.date.today() - d).days >= days


def group_cells(f, cells, size=10):
    """Groups of about `size` jurisdictions, by region, for parallel collectors."""
    by_j = OrderedDict()
    for c in cells:
        by_j.setdefault(c.split("/")[0], []).append(c)
    region = {j["code"]: j["region"] for j in f["jurisdictions"]}
    by_region = OrderedDict()
    for code, cs in by_j.items():
        by_region.setdefault(region.get(code, "Other"), []).append(cs)
    groups = OrderedDict()
    for reg, lists in by_region.items():
        n = max(1, math.ceil(len(lists) / size))
        for i in range(n):
            chunk = lists[i * size:(i + 1) * size]
            name = slugify(reg, 30) + ("-%d" % (i + 1) if n > 1 else "")
            groups[name] = [c for cs in chunk for c in cs]
    return groups


def cmd_frame(args):
    f = load_frame()
    days = args.days or f.get("stale_days", STALE_DAYS)
    if args.add:
        if any(j["code"] == args.add for j in f["jurisdictions"]):
            raise SystemExit("%s is already in the frame" % args.add)
        if not (args.name and args.level and args.region):
            raise SystemExit("--add needs --name, --level and --region")
        if args.region not in validate.VOCAB["region"] or args.level not in validate.VOCAB["jurisdiction_level"]:
            raise SystemExit("--region and --level must use the register's vocabulary")
        types = {"National": ["legislature", "gazette", "executive", "ministries", "ai-bodies", "elections", "supervisors"],
                 "Supranational": ["legislature", "gazette", "executive", "ai-bodies", "supervisors"],
                 "Sub-national": ["legislature", "gazette", "executive", "ministries", "supervisors"],
                 "International": ["repository"]}[args.level]
        f["jurisdictions"].append({"code": args.add, "name": args.name, "level": args.level, "region": args.region,
                                   "parent": args.parent, "records": 0,
                                   "cells": {t: {"last_searched": None, "outcome": None, "run_id": None,
                                                 "where_to_look": []} for t in types}})
        save_frame(f)
        print("Added %s (%s) with %d cells." % (args.add, args.name, len(types)))
        return 0
    if args.report:
        text = coverage_report(f, days)
        out = ROOT / "pipeline" / "coverage.md"
        out.write_text(text, encoding="utf-8")
        print(text.split("\n\n")[1])
        print("Written to %s" % rel(out))
        return 0
    cells = [cell_id(j, t) for j, t, c in frame_cells(f) if cell_due(c, days)]
    print("%d of %d cells are due (never searched, or not for %d days)." % (
        len(cells), sum(1 for _ in frame_cells(f)), days))
    if args.due:
        by_region = Counter(j["region"] for j, t, c in frame_cells(f) if cell_due(c, days))
        for reg, n in by_region.most_common():
            print("  %-28s %d" % (reg, n))
    return 0


def coverage_report(f, days):
    rows = defaultdict(lambda: [0, 0, 0, 0])  # cells, searched ever, searched recently, jurisdictions with records
    never = []
    for j in f["jurisdictions"]:
        r = rows[j["region"]]
        r[3] += 1 if j.get("records") else 0
        any_search = False
        for t, c in j["cells"].items():
            r[0] += 1
            if c.get("last_searched"):
                r[1] += 1
                any_search = True
                if not cell_due(c, days):
                    r[2] += 1
        if not any_search:
            never.append(j)
    total = [sum(r[i] for r in rows.values()) for i in range(4)]
    lines = ["# Search coverage", "",
             "Written %s by tools/pipeline.py frame --report from pipeline/frame.json: %d jurisdictions, %d cells; "
             "%d cells searched by the pipeline, %d of them within %d days." % (
                 today(), len(f["jurisdictions"]), total[0], total[1], total[2], days), "",
             "| Region | Cells | Searched | Within %d days | Jurisdictions with records |" % days, "|---|---:|---:|---:|---:|"]
    for reg in sorted(rows):
        r = rows[reg]
        lines.append("| %s | %d | %d | %d | %d |" % (reg, r[0], r[1], r[2], r[3]))
    lines += ["", "## Never searched by the pipeline (%d)" % len(never), ""]
    lines += ["- %s %s (%s)%s" % (j["code"], j["name"], j["region"], ", %d record(s) from earlier research" % j["records"]
                                  if j.get("records") else "") for j in never]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- new, status, stage

def select_records(db, scope):
    toks = shlex.split(scope or "")
    R = db["records"]
    ids = None
    for t in toks:
        k, _, v = t.partition(":")
        k = k.lower()
        if k == "ids":
            want = [x.strip() for x in v.split(",") if x.strip()]
            missing = [x for x in want if x not in {r["id"] for r in R}]
            if missing:
                raise SystemExit("No such record(s): %s" % ", ".join(missing))
            ids = want
        elif k == "region":
            R = [r for r in R if v.casefold() in r["region"].casefold()]
        elif k == "codes":
            codes = {x.strip().upper() for x in v.split(",") if x.strip()}
            R = [r for r in R if re.sub(r"-\d+$", "", r["id"]) in codes or r["id"].split("-")[0] in codes]
        elif k == "level":
            R = [r for r in R if v.casefold() in r["jurisdiction_level"].casefold()]
        elif k == "all":
            pass
        else:
            raise SystemExit("Unknown scope selector %r for records; use ids:, region:, codes:, level: or all" % t)
    if ids is not None:
        return ids
    return [r["id"] for r in R]


def cmd_new(args):
    if args.type not in RUN_TYPES:
        raise SystemExit("--type must be one of %s" % ", ".join(RUN_TYPES))
    label = args.label or args.scope or ("leads" if getattr(args, "leads", None) else
                                         "queue" if args.type == "refresh" else "all")
    base = "%s-%s-%s" % (today(), args.type, slugify(label, 32))
    run_id, n = base, 2
    while (RUNS / run_id).exists():
        run_id, n = "%s-%d" % (base, n), n + 1
    d = RUNS / run_id
    run = OrderedDict([("run_id", run_id), ("type", args.type), ("scope", args.scope or None), ("started", today()),
                       ("coordinator", {"tool": args.tool, "model": args.model}),
                       ("stages", {s: {"tool": None, "model": None, "date": None} for s in STAGES}),
                       ("status", None)])
    db = load_db()
    if args.type == "discover" and getattr(args, "leads", None):
        # a leads run follows up known leads only; its cells are where each lead belongs, and they are not marked
        # as searched, because nobody searched them as a whole
        f = load_frame()
        leads = (read_json(Path(args.leads), {}) or {}).get("leads") or []
        known = {cell_id(j, t) for j, t, c in frame_cells(f)}
        bad = [l.get("cell") for l in leads if l.get("cell") not in known]
        if not leads or bad:
            raise SystemExit("--leads needs {\"leads\": [{\"lead\", \"cell\", ...}]} with frame cells; unknown: %s"
                             % ", ".join(map(str, bad[:10])))
        cells = sorted({l["cell"] for l in leads})
        run["mode"] = "leads"
        run["leads"] = leads
        run["cells"] = cells
        run["groups"] = group_cells(f, cells, args.group_size)
    elif args.type == "discover":
        f = load_frame()
        cells = select_frame(f, args.scope, args.days or f.get("stale_days", STALE_DAYS))
        if not cells:
            raise SystemExit("The scope selects no frame cells.")
        run["cells"] = cells
        run["groups"] = group_cells(f, cells, args.group_size)
        run["status"] = "collecting"
    else:
        if args.type == "refresh" and not args.scope:
            due = queue(db, args.days or STALE_DAYS)
            ids = [rid for rid, _ in due][:args.limit]
            reasons = dict(due)
        else:
            ids = select_records(db, args.scope or "all")
            reasons = {}
        if not ids:
            raise SystemExit("The scope selects no records.")
        by = {r["id"]: r for r in db["records"]}
        run["record_ids"] = ids
        run["status"] = "archiving"
        cands = [{"cand_id": rid, "record_id": rid, "status": "active", "title_as_found": by[rid]["title"],
                  "url": by[rid].get("official_url"), "why": "; ".join(reasons.get(rid, [])) or args.type}
                 for rid in ids]
        write_json(d / "candidates.json", {"run_id": run_id, "generated": today(), "candidates": cands})
    for sub in ("candidates", "extractions", "extractions-blind", "checks"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    save_run(d, run)
    print("Created runs/%s" % run_id)
    if args.type == "discover":
        print("%d cells in %d groups: %s" % (len(run["cells"]), len(run["groups"]),
                                             ", ".join("%s (%d)" % (g, len(c)) for g, c in run["groups"].items())))
        print("Next: one collector per group (pipeline/roles/collect.md), then: python3 tools/pipeline.py dedupe --run %s" % run_id)
    else:
        print("%d records. Next: python3 tools/archive.py --run %s --browser" % (len(run["record_ids"]), run_id))
    print(run_id)
    return 0


def cmd_stage(args):
    d, run = load_run(args.run)
    if args.stage not in STAGES:
        raise SystemExit("--stage must be one of %s" % ", ".join(STAGES))
    run["stages"][args.stage] = {"tool": args.tool, "model": args.model, "date": today()}
    save_run(d, run)
    print("Recorded %s: %s, %s" % (args.stage, args.tool, args.model))
    return 0


def cmd_status(args):
    d, run = load_run(args.run)
    cands = candidates(d)
    act = [c for c in cands if c.get("status") == "active"]
    ex, bl, ch = agent_files(d, "extractions"), agent_files(d, "extractions-blind"), agent_files(d, "checks")
    sample = read_json(d / "sample.json", {}) or {}
    ev = read_json(d / "evidence.json", {}) or {}
    texts = read_json(d / "texts.json", {}) or {}
    logs = read_log(d)
    print("Run %s (%s), started %s, status: %s" % (run["run_id"], run["type"], run["started"], run.get("status")))
    for s in STAGES:
        st = run["stages"].get(s) or {}
        print("  %-8s %s" % (s, ("%s, %s, %s" % (st.get("tool"), st.get("model"), st.get("date"))) if st.get("tool") else "-"))
    if run["type"] == "discover":
        print("Cells: %d; logged: %d; group files: %d" % (len(run.get("cells") or []), len({l.get("cell") for l in logs}),
                                                      len(list((d / "candidates").glob("*.json")))))
    print("Candidates: %d (%d active)" % (len(cands), len(act)))
    print("Sources stored: %d; texts: %d" % (len(read_json(d / "sources.json", {}) or {}), len(texts.get("files") or [])))
    todo_ex = [c["cand_id"] for c in act if c["cand_id"] not in ex]
    print("Extractions: %d of %d%s" % (len([c for c in act if c["cand_id"] in ex]), len(act),
                                      ("; missing: " + ", ".join(todo_ex[:30])) if todo_ex else ""))
    if sample.get("blind"):
        print("Blind sample: %d of %d done" % (len([c for c in sample["blind"] if c in bl]), len(sample["blind"])))
    need_check = [c for c, e in ex.items() if (e or {}).get("decision") in ("record", "update")]
    print("Checks: %d of %d" % (len([c for c in need_check if c in ch]), len(need_check)))
    if ev:
        print("Evidence: %d with errors" % len([c for c, r in (ev.get("extractions") or {}).items() if r.get("errors")]))
    print("pass.json: %s; report.md: %s" % ("yes" if (d / "pass.json").is_file() else "no",
                                          "yes" if (d / "report.md").is_file() else "no"))
    return 0


# ----------------------------------------------------------------------------- dedupe

def read_log(d):
    out = []
    p = d / "search-log.jsonl"
    if p.is_file():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    print("WARNING  search-log.jsonl line %d is not valid JSON; skipped" % n)
    return out


def cmd_dedupe(args):
    d, run = load_run(args.run)
    if run["type"] != "discover":
        raise SystemExit("dedupe is for discover runs; refresh and recheck runs start with their records")
    if agent_files(d, "extractions") and not args.force:
        raise SystemExit("Extractions exist already; renumbering would break them. Use --force only if you mean it.")
    db = load_db()
    R = db["records"]
    by_url, by_title = {}, {}
    for r in R:
        for u in (r.get("official_url"), r.get("secondary_url")):
            if u:
                by_url.setdefault(norm_url(u), r["id"])
        for t in (r.get("title"), r.get("short_title"), r.get("original_title")):
            if t and len(norm_title(t)) > 12:
                by_title.setdefault(norm_title(t), r["id"])
    old = {(c.get("group"), c.get("cand_ref")): c.get("cand_id") for c in candidates(d)}
    out, seen_url, seen_title = [], {}, {}
    requests = []
    n = max([int(c[1:]) for c in old.values() if c and re.match(r"^C\d+$", c)] + [0])
    files = sorted((d / "candidates").glob("*.json"))
    if not files:
        raise SystemExit("No collector output in runs/%s/candidates/" % args.run)
    for p in files:
        doc = read_json(p) or {}
        group = doc.get("group") or p.stem
        for i, c in enumerate(doc.get("candidates") or [], 1):
            c = dict(c)
            c["group"] = group
            c.setdefault("cand_ref", "%s-%02d" % (group, i))
            c.setdefault("collector", {"tool": doc.get("tool"), "model": doc.get("model")})
            nu, nt = norm_url(c.get("url")), norm_title(c.get("title_as_found"))
            hit = (by_url.get(nu) if nu else None) or (by_title.get(nt) if len(nt) > 12 else None)
            dup = c.get("possible_duplicate_of")
            if dup and dup in {r["id"] for r in R}:
                c["status"] = "refresh-request"
                c["record_id"] = dup
                requests.append({"date": today(), "run_id": args.run, "record_id": dup, "why": c.get("why"),
                                 "url": c.get("url")})
            elif hit:
                c["status"] = "in-register"
                c["record_id"] = hit
            elif nu and nu in seen_url:
                c["status"], c["duplicate_of"] = "duplicate-in-run", seen_url[nu]
            elif len(nt) > 12 and nt in seen_title:
                c["status"], c["duplicate_of"] = "duplicate-in-run", seen_title[nt]
            elif c.get("scope_guess") == "out":
                c["status"] = "out-of-scope"
            else:
                c["status"] = "active"
            if c["status"] == "active":
                cid = old.get((group, c["cand_ref"]))
                if not cid:
                    n += 1
                    cid = "C%03d" % n
                c["cand_id"] = cid
                if nu:
                    seen_url[nu] = cid
                if len(nt) > 12:
                    seen_title[nt] = cid
            else:
                c["cand_id"] = None
            out.append(c)
    if requests:
        REQUESTS.parent.mkdir(parents=True, exist_ok=True)
        with open(REQUESTS, "a", encoding="utf-8") as fh:
            for r in requests:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    logs = read_log(d)
    logged = {l.get("cell") for l in logs}
    missing = [c for c in run.get("cells") or [] if c not in logged]
    f = load_frame()
    cells = {cell_id(j, t): (j, cell) for j, t, cell in frame_cells(f)}
    unknown = []
    for l in logs:
        hit = cells.get(l.get("cell"))
        if not hit:
            unknown.append(l.get("cell"))
            continue
        j, cell = hit
        if run.get("mode") != "leads":  # a leads run did not search the cell as a whole
            cell.update({"last_searched": l.get("date") or today(), "outcome": l.get("outcome"), "run_id": args.run})
        for u in l.get("new_portals") or []:
            if u not in cell["where_to_look"]:
                cell["where_to_look"].append(u)
    save_frame(f)
    write_json(d / "candidates.json", {"run_id": args.run, "generated": today(), "candidates": out,
                                       "cells_without_log": missing, "unknown_cells": sorted(set(unknown) - {None})})
    run["status"] = "archiving"
    save_run(d, run)
    st = Counter(c["status"] for c in out)
    print("Candidates: %s" % ", ".join("%s %d" % kv for kv in st.most_common()))
    if requests:
        print("%d existing record(s) added to the refresh requests (pipeline/refresh-requests.jsonl)." % len(requests))
    if missing:
        print("WARNING  %d cell(s) in scope have no search-log line: %s" % (len(missing), ", ".join(missing[:20])))
    if unknown:
        print("WARNING  search-log names cells that are not in the frame: %s" % ", ".join(sorted(set(unknown) - {None})[:20]))
    print("Frame updated from %d log line(s). Next: python3 tools/archive.py --run %s --browser" % (len(logs), args.run))
    return 0


# ----------------------------------------------------------------------------- textify

class _Blocks(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "header", "footer", "h1", "h2",
             "h3", "h4", "h5", "h6", "dt", "dd", "blockquote", "pre", "hr", "td", "th", "main", "nav", "aside"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template", "svg"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template", "svg") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(path):
    import archive  # noqa: E402  (same folder; imported late because it is large)
    body = Path(path).read_bytes()
    p = _Blocks()
    try:
        p.feed(archive.decode_html(body, "text/html"))
        p.close()
    except Exception:
        pass
    text = "".join(p.parts)
    lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in text.splitlines()]
    out, blank = [], 0
    for l in lines:
        if l:
            out.append(l)
            blank = 0
        elif not blank:
            out.append("")
            blank = 1
    return "\n".join(out).strip(), None, "html"


def garbled_share(pages):
    """Share of non-space characters that are control, unassigned or private-use code points: near 0 for real text,
    high when a PDF's font encoding defeats the extractor (pypdf then returns shifted or random characters)."""
    import unicodedata
    chars = [ch for ch in "".join(pages) if not ch.isspace()]
    bad = sum(1 for ch in chars if unicodedata.category(ch) in ("Cc", "Cn", "Co") or ch == "\ufffd")
    return bad / len(chars) if chars else 0.0


def pdf_text(path, ocr_lang, ocr_pages=60):
    """Text of a PDF with [page N] markers: pypdf, else pdftotext (also when pypdf's text is garbled);
    OCR with tesseract when it is a scan."""
    pages, method, warning, n_pages = [], None, None, 0
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        if reader.is_encrypted:
            reader.decrypt("")
        pages = [(pg.extract_text() or "") for pg in reader.pages]
        n_pages, method = len(pages), "pypdf"
    except Exception:
        pages = []
    garbled = pages and garbled_share(pages) > 0.05
    if (not pages or garbled) and shutil.which("pdftotext"):
        try:
            out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=300)
            alt = out.stdout.decode("utf-8", "replace").split("\f")
            if alt and not alt[-1].strip():
                alt = alt[:-1]
            if alt and (not pages or garbled_share(alt) < garbled_share(pages)):
                pages, n_pages = alt, len(alt)
                method = "pdftotext (pypdf's text was garbled)" if garbled else "pdftotext"
        except Exception:
            pass
    if not pages:
        return "", 0, None, "no PDF text extractor worked (install pypdf, or poppler's pdftotext)"
    chars = sum(len(p.strip()) for p in pages)
    if chars < 80 * len(pages):
        if shutil.which("tesseract") and shutil.which("pdftoppm"):
            ocr = []
            with tempfile.TemporaryDirectory() as tmp:
                for i in range(1, min(n_pages, ocr_pages) + 1):
                    base = Path(tmp) / ("p%d" % i)
                    subprocess.run(["pdftoppm", "-r", "200", "-png", "-f", str(i), "-l", str(i), "-singlefile",
                                    str(path), str(base)], capture_output=True, timeout=300)
                    img = base.with_suffix(".png")
                    res = subprocess.run(["tesseract", str(img), "-", "-l", ocr_lang], capture_output=True,
                                         timeout=300) if img.is_file() else None
                    ocr.append(res.stdout.decode("utf-8", "replace") if res else "")
            if sum(len(p.strip()) for p in ocr) > chars:
                pages, method = ocr, "ocr (tesseract, %s)" % ocr_lang
                if n_pages > ocr_pages:
                    warning = "OCR covers the first %d of %d pages" % (ocr_pages, n_pages)
            else:
                warning = "little text, and OCR found no more"
        else:
            warning = "the PDF has little text (probably a scan) and tesseract or pdftoppm is not installed"
    text = "\n".join("[page %d]\n%s" % (i, p.strip()) for i, p in enumerate(pages, 1))
    return text, len(pages), method, warning


def stored_files(sources, cid):
    """All stored files for a candidate: [(path, sha256, role, url)]."""
    e = sources.get(cid) or {}
    out = []
    lcs = [("main", e.get("main"))] + [("extra", lc) for lc in (e.get("extras") or {}).values()]
    for kind, lc in lcs:
        for f in (lc or {}).get("files") or []:
            role = f.get("role") if kind == "main" else "extra"
            if f.get("path"):
                out.append((f["path"], f.get("sha256"), role, f.get("url")))
            # the snapshot this one replaced is still a stored copy with its hash, and may be what an agent quoted
            if f.get("previous_path") and (ROOT / f["previous_path"]).is_file():
                out.append((f["previous_path"], f.get("previous_sha256"), role, f.get("url")))
    return out


def cmd_textify(args):
    d, run = load_run(args.run)
    sources = read_json(d / "sources.json", {}) or {}
    if not sources:
        raise SystemExit("runs/%s/sources.json is missing; run: python3 tools/archive.py --run %s" % (args.run, args.run))
    old = {t["file"]: t for t in (read_json(d / "texts.json", {}) or {}).get("files") or []}
    rows, done = [], 0
    for cid in sorted(sources):
        for path, digest, role, url in stored_files(sources, cid):
            src = ROOT / path
            if not src.is_file():
                rows.append({"cand_id": cid, "file": path, "sha256": digest, "txt": None, "warning": "file missing"})
                continue
            txt = Path(str(src) + ".txt")
            prev = old.get(path)
            if prev and prev.get("sha256") == digest and txt.is_file() and not args.force:
                rows.append(dict(prev, cand_id=cid))
                continue
            ext = src.suffix.lower()
            pages, method, warning = None, None, None
            try:
                if ext == ".pdf":
                    text, pages, method, warning = pdf_text(src, args.ocr_lang)
                elif ext in (".html", ".xml"):
                    text, _, method = html_text(src)
                elif ext in (".txt", ".json"):
                    text, method = src.read_text(encoding="utf-8", errors="replace"), "copy"
                else:
                    text, warning = "", "no text extraction for %s files" % ext
            except Exception as e:
                text, warning = "", "text extraction failed: %s" % e
            header = "# Text of %s (sha256 %s), made by tools/pipeline.py textify (%s)\n\n" % (path, digest, method or "-")
            txt.write_text(header + text + "\n", encoding="utf-8")
            done += 1
            rows.append({"cand_id": cid, "file": path, "sha256": digest, "role": role, "url": url, "txt": rel(txt),
                         "pages": pages, "chars": len(text), "method": method, "warning": warning})
    write_json(d / "texts.json", {"run_id": args.run, "generated": today(), "files": rows})
    run["status"] = "extracting"
    save_run(d, run)
    warn = [r for r in rows if r.get("warning")]
    print("Text for %d file(s) (%d new); %d with warnings." % (len(rows), done, len(warn)))
    for r in warn[:30]:
        print("  %-6s %s: %s" % (r["cand_id"], r["file"], r["warning"]))
    print("Extractors read runs/%s/texts.json for the files, hashes and text paths of each candidate." % args.run)
    return 0


# ----------------------------------------------------------------------------- evidence

def norm_text(s):
    s = unicodedata.normalize("NFKC", s or "").replace("­", "")
    s = re.sub(r"[‘’‚‛′`´]", "'", s)
    s = re.sub(r"[“”„‟″«»]", '"', s)
    s = re.sub(r"[‐-―−]", "-", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def loose(s):
    return "".join(ch for ch in norm_text(s) if ch.isalnum())


class TextIndex:
    """The stored files of one run, with their texts, for quote matching."""

    def __init__(self, d, db):
        self.d = d
        self.sources = read_json(d / "sources.json", {}) or {}
        self.texts = {t["file"]: t for t in (read_json(d / "texts.json", {}) or {}).get("files") or []}
        self.records = {r["id"]: r for r in db["records"]}
        self._cache = {}
        self.cells = {c["cand_id"]: c.get("cell") for c in candidates(d)}
        self.frame_hosts, self.rejected_hosts = site_hosts(load_sites())

    def file_info(self, cid, record_id=None):
        """path -> (archive role, URL it came from) for every file a candidate may quote."""
        out = {p: (role, url) for p, _, role, url in stored_files(self.sources, cid)}
        rid = record_id or (self.sources.get(cid) or {}).get("record_id")
        if rid and rid in self.records:
            for f in (self.records[rid].get("local_copy") or {}).get("files") or []:
                for path in (f.get("path"), f.get("previous_path")):
                    if path:
                        out.setdefault(path, (f.get("role"), f.get("final_url") or f.get("url")))
        return out

    def code_for(self, cid, record_id=None):
        cell = self.cells.get(cid) or ""
        if "/" in cell:
            return cell.split("/")[0]
        rid = record_id or (self.sources.get(cid) or {}).get("record_id") or cid
        return re.sub(r"-\d+$", "", rid or "")

    def files_for(self, cid, record_id=None):
        out = {p: digest for p, digest, _, _ in stored_files(self.sources, cid)}
        rid = record_id or (self.sources.get(cid) or {}).get("record_id")
        if rid and rid in self.records:  # a refresh may quote the record's own stored copies, and the ones they replaced
            for f in (self.records[rid].get("local_copy") or {}).get("files") or []:
                if f.get("path"):
                    out.setdefault(f["path"], f.get("sha256"))
                if f.get("previous_path") and (ROOT / f["previous_path"]).is_file():
                    out.setdefault(f["previous_path"], f.get("previous_sha256"))
        return out

    def pages(self, path):
        if path not in self._cache:
            t = self.texts.get(path)
            p = ROOT / (t["txt"] if t and t.get("txt") else path + ".txt")
            if not p.is_file():
                self._cache[path] = None
            else:
                raw = p.read_text(encoding="utf-8", errors="replace")
                raw = raw.split("\n\n", 1)[1] if raw.startswith("# Text of ") and "\n\n" in raw else raw
                parts = re.split(r"^\[page (\d+)\]$", raw, flags=re.M)
                pages = {}
                if len(parts) > 1:
                    for i in range(1, len(parts), 2):
                        pages[int(parts[i])] = parts[i + 1]
                else:
                    pages[0] = raw
                self._cache[path] = {k: (norm_text(v), loose(v)) for k, v in pages.items()}
        return self._cache[path]


def url_host(url):
    return (urllib.parse.urlsplit(url or "").hostname or "").lower()


def official_host(host, code, frame_hosts, rejected=()):
    """A host counts as official when it is a government domain, or listed as official for the jurisdiction in
    pipeline/official-sites.json, and is neither a known third-party site nor listed there as not official.
    A human records each decision with `pipeline.py hosts --add`."""
    if not host or host in NOT_OFFICIAL_HOSTS or ("www." + host) in NOT_OFFICIAL_HOSTS or strip_www(host) in rejected:
        return False
    if GOV_HOST.search(host):
        return True
    for h in frame_hosts.get(code) or []:
        h = h.lower()
        if host == h or host.endswith("." + h) or h.endswith("." + host.replace("www.", "", 1)):
            return True
    return False


def check_item(index, cid, item, record_id=None):
    """Check one evidence item. Returns (ok, kind, problems, warnings)."""
    problems, warnings = [], []
    if not isinstance(item, dict):
        return False, None, ["evidence item is not an object"], []
    path = (item.get("file") or "").strip()
    if path.endswith(".txt"):
        path = path[:-4]
    path = path[len(str(ROOT)) + 1:] if path.startswith(str(ROOT)) else path
    kind = item.get("source_kind")
    if kind not in SOURCE_KINDS:
        problems.append("source_kind %r is not one of %s" % (kind, ", ".join(SOURCE_KINDS)))
    allowed = index.files_for(cid, record_id)
    if path not in allowed:
        problems.append("file %r is not a stored source of %s" % (path, cid))
        return False, kind, problems, warnings
    if not (ROOT / path).is_file():
        problems.append("file %s is missing on disk" % path)
        return False, kind, problems, warnings
    actual = sha256_file(ROOT / path)
    if not item.get("sha256"):
        problems.append("sha256 is missing (it is in texts.json)")
    elif item["sha256"] != actual:
        problems.append("sha256 does not match %s" % path)
    quote = item.get("quote") or ""
    if not quote.strip():
        problems.append("quote is empty")
        return False, kind, problems, warnings
    if len(quote) > QUOTE_MAX:
        warnings.append("quote is %d characters (limit %d)" % (len(quote), QUOTE_MAX))
    if len(loose(quote)) < QUOTE_MIN_ALNUM:
        problems.append("quote %r is too short to identify a passage (at least %d letters or digits)" % (quote, QUOTE_MIN_ALNUM))
        return False, kind, problems, warnings
    pages = index.pages(path)
    if pages is None:
        problems.append("no text for %s; run textify" % path)
        return False, kind, problems, warnings
    nq, lq = norm_text(quote), loose(quote)
    found = [k for k, (n, l) in pages.items() if nq in n]
    how = "exact"
    if not found and len(lq) >= 20:
        found = [k for k, (n, l) in pages.items() if lq in l]
        how = "loose"
    if not found:
        problems.append("quote not found in %s: %r" % (path, quote[:80]))
        return False, kind, problems, warnings
    if how == "loose":
        warnings.append("quote matches only when spacing and punctuation are ignored")
    m = re.search(r"\bp(?:age|\.|p\.)?\s*(\d+)", item.get("locator") or "", re.I)
    if m and 0 not in pages and int(m.group(1)) not in found:
        warnings.append("quote is on page %s, not %s" % (", ".join(map(str, found[:3])), m.group(1)))
    if kind in ("official", "alt-official"):
        role, url = index.file_info(cid, record_id).get(path, (None, None))
        host = url_host(url)
        is_official = official_host(host, index.code_for(cid, record_id), index.frame_hosts, index.rejected_hosts)
        if role in SECONDARY_ROLES and is_official and kind == "official":
            warnings.append("%s was stored as the record's secondary source; from an official host it counts as "
                            "another official source (alt-official), not as the official one" % path)
            kind = "alt-official"
        elif role in SECONDARY_ROLES and not is_official:
            warnings.append("%s was stored as a secondary source, so it counts as secondary, not %s" % (path, kind))
            kind = "secondary"
        elif not is_official:
            warnings.append("host %s is not recognised as official, so this quote counts as secondary; if the host is "
                            "official, a human records it with tools/pipeline.py hosts --add" % (host or "(unknown)"))
            kind = "secondary"
    return not problems, kind, problems, warnings


MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                         "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9


JP_ERAS = {"令和": 2018, "平成": 1988}  # Reiwa 1 = 2019, Heisei 1 = 1989


def dates_in(text):
    """Full dates written in a quote, as ISO strings (English month names and numeric forms)."""
    t = norm_text(text)
    out = set()

    def add(y, m, d):
        try:
            out.add(dt.date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            pass
    for y, m, d in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        add(y, m, d)
    mon = "|".join(sorted(MONTHS, key=len, reverse=True))
    for d, m, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\.? (%s)\.?,? (\d{4})\b" % mon, t):
        add(y, MONTHS[m], d)
    for m, d, y in re.findall(r"\b(%s)\.? (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})\b" % mon, t):
        add(y, MONTHS[m], d)
    for d, m, y in re.findall(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", t):
        add(y, m, d)
    for d, m, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)? day of (%s),? (?:in the year )?(\d{4})\b" % mon, t):
        add(y, MONTHS[m], d)  # executive orders: "this 30th day of March 2026"
    for a, b, y in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t):  # day/month or month/day: accept both
        add(y, b, a)
        add(y, a, b)
    for y, m, d in re.findall(r"(\d{4})\s*[年년]\s*(\d{1,2})\s*[月월]\s*(\d{1,2})\s*[日일]", t):  # Chinese, Japanese, Korean
        add(y, m, d)
    for era, y, m, d in re.findall(r"(令和|平成)\s*(\d{1,2}|元)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", t):  # Japanese eras
        add(JP_ERAS[era] + (1 if y == "元" else int(y)), m, d)
    for y, m, d in re.findall(r"\b(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?(?!\d)", t):  # Korean 2026. 1. 20.
        add(y, m, d)
    for d, m, y in re.findall(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", t):  # Vietnamese
        add(y, m, d)
    return out


def months_in(text):
    """Year-months written in a quote without a day (April 2025, 2025年4月, 2025년 4월, tháng 4 năm 2025, 2025-04)."""
    t = norm_text(text)
    out = set()

    def add(y, m):
        if 1 <= int(m) <= 12:
            out.add("%04d-%02d" % (int(y), int(m)))
    mon = "|".join(sorted(MONTHS, key=len, reverse=True))
    for m, y in re.findall(r"(?<![\d.] )(?<!\d)\b(%s)\.?,? (\d{4})\b" % mon, t):
        add(y, MONTHS[m])
    for y, m in re.findall(r"(\d{4})\s*[年년]\s*(\d{1,2})\s*[月월](?!\s*\d{1,2}\s*[日일])", t):
        add(y, m)
    for era, y, m in re.findall(r"(令和|平成)\s*(\d{1,2}|元)\s*年\s*(\d{1,2})\s*月(?!\s*\d{1,2}\s*日)", t):
        add(JP_ERAS[era] + (1 if y == "元" else int(y)), m)
    for mt in re.finditer(r"tháng\s*(\d{1,2})\s*năm\s*(\d{4})", t):  # not when a day number precedes it
        if not re.search(r"ngày\s*\d{1,2}\s*$", t[:mt.start()]):
            add(mt.group(2), mt.group(1))
    for y, m in re.findall(r"\b(\d{4})-(\d{2})\b(?!-\d)", t):
        add(y, m)
    return out


def date_support(value, quote):
    """How one quote supports a date value: 'full', 'partial' (it shows only the year-month of a full date) or
    'unknown' (no date form the script can read)."""
    v = str(value or "")
    if not validate.FULL_DATE.match(v):
        return "full" if v and v[:4] in norm_text(quote) else "unknown"
    if v in dates_in(quote):
        return "full"
    if v[:7] in months_in(quote):
        return "partial"
    return "unknown"


def value_hint(field, value, quotes):
    """Cheap consistency checks between a value and its quotes."""
    if value in (None, "", []):
        return None
    hay = norm_text(" ".join(quotes))
    if field.startswith("date_") and re.match(r"^\d{4}", str(value)):
        year = str(value)[:4]
        y = int(year)
        eras = [("令和%s年" % ("元" if y == 2019 else y - 2018)) if y > 2018 else "",
                ("平成%s年" % ("元" if y == 1989 else y - 1988)) if 1988 < y < 2020 else ""]
        if year not in hay and str(int(year) + 543) not in hay and not any(e and e in hay.replace(" ", "") for e in eras):
            # Buddhist-era years appear in Thai sources, Japanese era years in Japanese ones
            return "warning", "no quote for %s shows the year %s" % (field, year)
        found = dates_in(" ".join(quotes))
        if found and not any(x.startswith(str(value)) for x in found):
            return "error", "the quotes for %s show %s, not %s" % (field, ", ".join(sorted(found)), value)
    if field == "official_identifier":
        nums = [n for n in re.findall(r"\d+", str(value)) if len(n) >= 2]
        if nums and not any(n in hay for n in nums):
            return "warning", "no quote for official_identifier shows its number"
    return None


def record_problems(rec, db, update=False):
    """Schema and convention checks on an extracted record (or on the fields an update changes)."""
    errors, warnings = [], []
    present = lambda k: rec.get(k) not in (None, "", [])  # noqa: E731
    if not update:
        for k in validate.REQUIRED:
            if k in SET_BY_SCRIPT or k == "verification":
                continue
            if not present(k):
                errors.append("required field %r is missing" % k)
    for k, allowed in validate.VOCAB.items():
        if present(k) and rec[k] not in allowed:
            errors.append("%s %r is not in the vocabulary" % (k, rec[k]))
    for k in ("date_published", "date_in_force", "date_last_updated"):
        v = rec.get(k)
        if v and not (validate.FULL_DATE.match(str(v)) or validate.PARTIAL_DATE.match(str(v))):
            errors.append("%s %r is not an ISO date" % (k, v))
    if "summary" in rec and rec.get("summary") is not None:
        n = len(rec["summary"])
        if n < SUMMARY_MIN or n > SUMMARY_MAX:
            errors.append("summary is %d characters (%d to %d)" % (n, SUMMARY_MIN, SUMMARY_MAX))
    if "safety_topics" in rec and rec.get("safety_topics") is not None:
        t = rec["safety_topics"]
        if not isinstance(t, list) or not (TOPICS_MIN <= len(t) <= TOPICS_MAX):
            errors.append("safety_topics needs %d to %d values" % (TOPICS_MIN, TOPICS_MAX))
        else:
            bad = [x for x in t if x not in validate.TOPICS]
            if bad:
                errors.append("topics not in the vocabulary: %s" % ", ".join(bad))
    for k in ("summary", "notes", "scope_note"):
        txt = rec.get(k) or ""
        hits = [m.group(0) for pat in PROCESS_PATTERNS for m in [re.search(pat, txt, re.I)] if m]
        if hits:
            errors.append("%s contains research-process language (%s); move it to verification.note" % (k, ", ".join(hits[:3])))
    for k in ("official_url", "secondary_url"):
        u = rec.get(k)
        if u and not re.match(r"^https?://\S+$", u):
            errors.append("%s is not an http(s) URL" % k)
    dp, di = str(rec.get("date_published") or ""), str(rec.get("date_in_force") or "")
    if validate.FULL_DATE.match(dp) and validate.FULL_DATE.match(di) and di < dp:
        warnings.append("date_in_force is before date_published")
    if rec.get("status") in IN_FORCE and "date_in_force" in rec and not rec.get("date_in_force"):
        warnings.append("status is in force but date_in_force is empty")
    if rec.get("legal_force") == "Proposed" and rec.get("status") in IN_FORCE:
        errors.append("legal_force Proposed with an in-force status")
    di_d = parse_date(rec.get("date_in_force"))
    if di_d and di_d <= dt.date.today() and rec.get("status") not in CURRENT and rec.get("status"):
        warnings.append("date_in_force %s has passed but the status is %r" % (di_d, rec["status"]))
    known_countries = {r["country"] for r in db["records"]}
    if present("country") and rec["country"] not in known_countries:
        if rec["country"] not in frame_names() and rec["country"] != "International":
            warnings.append("country %r is spelled differently from the register and the frame" % rec["country"])
    if present("official_identifier") and re.search(r"(?i)\bversion\b|^v\d|not confirmed|unknown", rec["official_identifier"]):
        warnings.append("official_identifier looks like a version label or a remark")
    if present("language") and validate.LANGUAGE_REMARK.search(validate.LANGUAGE_VARIANT.sub("", rec["language"])):
        errors.append("language %r holds a remark; give language names only and put an English translation in "
                      "english_version" % rec["language"])
    ev = rec.get("english_version")
    if ev is not None:
        if not isinstance(ev, dict) or ev.get("kind") not in validate.ENGLISH_VERSION_KINDS:
            errors.append("english_version must be {kind, url, by} with kind one of %s"
                          % ", ".join(validate.ENGLISH_VERSION_KINDS))
        elif ev["kind"] in validate.TRANSLATION_KINDS and not (ev.get("url") and ev.get("by")):
            errors.append("english_version is a translation: give its url and who made it ('by')")
    elif not update and present("language") and not validate.has_english_text(rec):
        errors.append("the official text is not in English: record english_version (none found, if none was found)")
    return errors, warnings


def evaluate(index, cid, ex, db):
    """Evidence check of one extraction. Returns a result dict with errors, warnings, level and per-field support."""
    res = {"decision": ex.get("decision"), "errors": [], "warnings": [], "fields": {}, "level": None}
    if ex.get("_error"):
        res["errors"].append(ex["_error"])
        return res
    if ex.get("decision") not in DECISIONS:
        res["errors"].append("decision %r is not one of %s" % (ex.get("decision"), ", ".join(DECISIONS)))
        return res
    if ex["decision"] not in ("record", "update"):
        return res
    rec = ex.get("record") or {}
    evidence = ex.get("evidence") or {}
    update = ex["decision"] == "update"
    target = ex.get("target_id") or (index.sources.get(cid) or {}).get("record_id")
    if update and target not in index.records:
        res["errors"].append("an update needs target_id of an existing record")
        return res
    for k in SET_BY_SCRIPT:
        if rec.get(k):
            res["warnings"].append("%s is set by the scripts; the extractor's value is ignored" % k)
    errs, warns = record_problems(rec, db, update=update)
    res["errors"] += errs
    res["warnings"] += warns
    base = dict(index.records[target]) if update else {}
    merged = dict(base, **{k: v for k, v in rec.items() if k in RECORD_FIELDS})
    ev = rec.get("english_version")
    if isinstance(ev, dict) and ev.get("kind") in validate.TRANSLATION_KINDS and ev.get("url"):
        stored = {u for _, u in index.file_info(cid, target if update else None).values() if u}
        if ev["url"] not in stored:
            res["errors"].append("english_version.url is not a stored source of %s; add it to extra_urls so the "
                                 "archiver stores it" % cid)
    if update and merged.get("english_version") is None and merged.get("language") and not validate.has_english_text(merged):
        res["warnings"].append("the official text is not in English and english_version is not recorded yet")
    confirmed = ((ex.get("judgment") or {}).get("confirmed") or []) if update else []
    fields = [k for k in FACT_FIELDS if (k in rec and rec.get(k) is not None) or k in confirmed]
    if update:
        fields += [k for k in LEVEL_FIELDS if k not in fields and merged.get(k) is not None]
    for k in fields:
        items = evidence.get(k) or []
        if isinstance(items, dict):
            items = [items]
        fr = {"items": [], "supported": False, "best_kind": None}
        kinds, level_kinds = [], []
        for it in items:
            ok, kind, probs, warns = check_item(index, cid, it, target)
            if ok and k.startswith("date_") and isinstance(it, dict) and \
                    date_support(merged.get(k), it.get("quote") or "") == "partial":
                # the quote shows only the month of a full date: it supports the field, not the level
                warns = warns + ["the quote shows only the month of %s, so it does not count for the level" % merged.get(k)]
            elif ok:
                level_kinds.append(kind)
            fr["items"].append({"ok": ok, "problems": probs, "warnings": warns})
            if ok:
                kinds.append(kind)
        fr["supported"] = bool(kinds)
        fr["best_kind"] = next((k2 for k2 in SOURCE_KINDS if k2 in level_kinds), None)
        if not items:
            msg = "%s has no evidence" % k
            (res["errors"] if (k in rec or k in LEVEL_FIELDS) else res["warnings"]).append(msg)
        elif not kinds:
            res["errors"].append("%s: no evidence item passed (%s)" % (
                k, "; ".join(p for it in fr["items"] for p in it["problems"])[:300]))
        hint = value_hint(k, merged.get(k), [it.get("quote") or "" for it in items if isinstance(it, dict)])
        if hint:
            res["errors" if hint[0] == "error" else "warnings"].append(hint[1])
        for it in fr["items"]:
            res["warnings"] += ["%s: %s" % (k, w) for w in it["warnings"]]
        res["fields"][k] = fr
    res["level"] = compute_level(res["fields"], merged)
    return res


def compute_level(fields, merged):
    need = [k for k in LEVEL_FIELDS if not (k == "date_published" and merged.get(k) is None)]
    kinds = []
    for k in need:
        fr = fields.get(k)
        kinds.append(fr["best_kind"] if fr and fr.get("supported") else None)
    if all(k == "official" for k in kinds):
        return "A"
    if all(k in ("official", "alt-official") for k in kinds):
        return "B"
    return "C"


def cmd_evidence(args):
    d, run = load_run(args.run)
    db = load_db()
    index = TextIndex(d, db)
    out = {"run_id": args.run, "generated": today(), "extractions": {}, "blind": {}}
    for sub, key in (("extractions", "extractions"), ("extractions-blind", "blind")):
        for cid, ex in agent_files(d, sub).items():
            out[key][cid] = evaluate(index, cid, ex, db)
    write_json(d / "evidence.json", out)
    bad = 0
    for cid, r in sorted(out["extractions"].items()):
        flag = "ERRORS" if r["errors"] else "ok"
        bad += 1 if r["errors"] else 0
        print("%-8s %-13s level %-4s %-6s %s" % (cid, r["decision"], r["level"] or "-", flag,
                                                 "; ".join(r["errors"][:2])[:160]))
    print("%d extraction(s), %d with errors; blind: %d. Written runs/%s/evidence.json" % (
        len(out["extractions"]), bad, len(out["blind"]), args.run))
    return 1 if bad else 0


# ----------------------------------------------------------------------------- sample and compare

def cmd_sample(args):
    d, run = load_run(args.run)
    ex = agent_files(d, "extractions")
    eligible = sorted(c for c, e in ex.items() if (e or {}).get("decision") in ("record", "update"))
    if not eligible:
        raise SystemExit("No extractions with decision record or update yet")
    n = min(len(eligible), max(args.min, math.ceil(len(eligible) * args.share)))
    rng = random.Random("blind:" + args.run)
    picked = sorted(rng.sample(eligible, n))
    sample = read_json(d / "sample.json", {}) or {}
    if sample.get("blind") and not args.force:
        print("Keeping the existing blind sample (use --force to draw again): %s" % ", ".join(sample["blind"]))
        return 0
    sample.update({"run_id": args.run, "seed": "blind:" + args.run, "blind": picked, "drawn": today()})
    write_json(d / "sample.json", sample)
    print("Blind sample: %d of %d: %s" % (n, len(eligible), ", ".join(picked)))
    print("Give these to a fresh extractor that writes into runs/%s/extractions-blind/ and does not open extractions/." % args.run)
    return 0


EXACT_FIELDS = ["date_published", "date_in_force", "date_last_updated", "status", "legal_force", "instrument_type",
                "jurisdiction_level", "region", "country"]


def same(field, a, b):
    if a in (None, "", []) and b in (None, "", []):
        return True
    if field in ("title", "original_title", "issuing_body", "short_title"):
        x, y = norm_title(a), norm_title(b)
        return difflib.SequenceMatcher(None, x, y).ratio() >= (0.9 if field != "issuing_body" else 0.75)
    if field == "official_identifier":
        return loose(a or "") == loose(b or "")
    if field in ("safety_topics", "related"):
        def ids(v):
            return {x.get("id") if isinstance(x, dict) else x for x in (v or [])}
        sa, sb = ids(a), ids(b)
        return len(sa & sb) / max(1, len(sa | sb)) >= 0.5
    return a == b


def cmd_compare(args):
    d, run = load_run(args.run)
    sample = read_json(d / "sample.json", {}) or {}
    ex, bl = agent_files(d, "extractions"), agent_files(d, "extractions-blind")
    fields = ["decision", "title", "original_title", "issuing_body", "official_identifier"] + EXACT_FIELDS + ["safety_topics"]
    stats = OrderedDict((f, [0, 0]) for f in fields)
    result = [0, 0]  # refresh runs: agreement on the resulting record (current record plus each extraction's changes)
    records = {r["id"]: r for r in load_db()["records"]}
    per, pending = {}, []
    for cid in sample.get("blind") or []:
        a, b = ex.get(cid), bl.get(cid)
        if not a or not b:
            pending.append(cid)
            continue
        base = records.get(a.get("target_id") or cid) if a.get("decision") == "update" else None
        if base and b.get("decision") == "update":
            for f in fields[1:]:
                ra = (a.get("record") or {}).get(f, base.get(f)) if f in (a.get("record") or {}) else base.get(f)
                rb = (b.get("record") or {}).get(f, base.get(f)) if f in (b.get("record") or {}) else base.get(f)
                if ra in (None, "", []) and rb in (None, "", []):
                    continue
                result[0] += 1
                result[1] += 1 if same(f, ra, rb) else 0
        diffs = []
        for f in fields:
            va = a.get("decision") if f == "decision" else (a.get("record") or {}).get(f)
            vb = b.get("decision") if f == "decision" else (b.get("record") or {}).get(f)
            if f != "decision" and va in (None, "", []) and vb in (None, "", []):
                continue
            stats[f][0] += 1
            if same(f, va, vb):
                stats[f][1] += 1
            else:
                diffs.append({"field": f, "first": va, "blind": vb})
        per[cid] = diffs
    n_all = sum(s[0] for f, s in stats.items() if f != "decision")
    a_all = sum(s[1] for f, s in stats.items() if f != "decision")
    table = OrderedDict((f, {"compared": s[0], "agree": s[1], "rate": round(s[1] / s[0], 3) if s[0] else None})
                        for f, s in stats.items())
    out = {"run_id": args.run, "generated": today(), "compared": len(per), "pending": pending,
           "overall_field_agreement": round(a_all / n_all, 3) if n_all else None, "fields": table, "disagreements": per,
           "resulting_record_agreement": round(result[1] / result[0], 3) if result[0] else None,
           "resulting_record_fields": result[0]}
    write_json(d / "agreement.json", out)
    print("Compared %d pair(s); pending: %s" % (len(per), ", ".join(pending) or "-"))
    for f, t in table.items():
        if t["compared"]:
            print("  %-20s %d/%d" % (f, t["agree"], t["compared"]))
    if out["overall_field_agreement"] is not None:
        print("Overall field agreement: %.0f%%" % (100 * out["overall_field_agreement"]))
    if out["resulting_record_agreement"] is not None:
        print("Agreement on the resulting records (refresh runs; %d field values): %.0f%%"
              % (result[0], 100 * out["resulting_record_agreement"]))
    return 0


# ----------------------------------------------------------------------------- queue

def queue(db, days, root=ROOT):
    """Records due for a refresh run, most urgent first: [(id, [reasons])]."""
    now = dt.date.today()
    reasons = defaultdict(list)
    prio = {}
    events = history.load(root)
    last_check = {}
    for e in events:
        if e.get("event") in ("changed", "re-verified", "added"):
            last_check[e["record_id"]] = max(last_check.get(e["record_id"], ""), e.get("date") or "")
    if REQUESTS.is_file():
        for line in REQUESTS.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if last_check.get(r.get("record_id"), "") < (r.get("date") or ""):
                reasons[r["record_id"]].append("requested in run %s: %s" % (r.get("run_id"), (r.get("why") or "")[:80]))
                prio[r["record_id"]] = min(prio.get(r["record_id"], 9), 0)
    for r in db["records"]:
        rid = r["id"]
        v = r.get("verification") or {}
        vd = parse_date(v.get("verified_on"))
        lc = r.get("local_copy") or {}
        add = lambda p, msg: (reasons[rid].append(msg), prio.__setitem__(rid, min(prio.get(rid, 9), p)))  # noqa: E731
        di = parse_date(r.get("date_in_force"))
        if di and di <= now and r.get("status") not in CURRENT:
            add(1, "date_in_force %s has passed but the status is %s" % (di, r.get("status")))
        if r.get("status") == "Adopted, not yet in force" and not r.get("date_in_force"):
            add(2, "adopted, not yet in force, and no in-force date")
        changed = [f for f in lc.get("files") or [] if not f.get("stale") and f.get("previous_sha256")
                   and vd and (f.get("retrieved_at") or "")[:10] > vd.isoformat()]
        if changed:
            add(3, "source changed since verification (%s)" % ", ".join(f.get("role_key") or f.get("role") for f in changed))
        if v.get("level") == "C":
            add(4, "level C")
        if lc.get("status") in ("failed", "partial", "archived-review") or lc.get("integrity_flag"):
            add(5, "local copy needs attention (%s)" % lc.get("status"))
        if not vd or (now - vd).days >= days:
            add(6, "verified %s, more than %d days ago" % (v.get("verified_on"), days))
    return sorted(((rid, rs) for rid, rs in reasons.items()), key=lambda x: (prio.get(x[0], 9), x[0]))


def cmd_queue(args):
    db = load_db()
    q = queue(db, args.days)
    if args.json:
        print(json.dumps([{"id": rid, "reasons": rs} for rid, rs in q], ensure_ascii=False, indent=1))
        return 0
    print("%d record(s) due for a refresh run:" % len(q))
    for rid, rs in q[:args.limit]:
        print("  %-10s %s" % (rid, "; ".join(rs)[:150]))
    if len(q) > args.limit:
        print("  ... and %d more (--limit)" % (len(q) - args.limit))
    return 0


# ----------------------------------------------------------------------------- assemble

def jurisdiction_code(c, rec, db):
    cell = c.get("cell") or ""
    if "/" in cell:
        return cell.split("/")[0]
    prefixes = Counter(re.sub(r"-\d+$", "", r["id"]) for r in db["records"] if r.get("jurisdiction") == rec.get("jurisdiction"))
    return prefixes.most_common(1)[0][0] if prefixes else None


def next_id(code, taken):
    nums = [int(i.rsplit("-", 1)[1]) for i in taken if re.sub(r"-\d+$", "", i) == code]
    nid = "%s-%02d" % (code, (max(nums) + 1) if nums else 1)
    taken.add(nid)
    return nid


def unique_slug(base, taken):
    s, n = base, 2
    while s in taken:
        s, n = "%s-%d" % (base, n), n + 1
    taken.add(s)
    return s


def norm_related(v, ids):
    out, bad = [], []
    for x in v or []:
        rid = x.get("id") if isinstance(x, dict) else x
        if rid in ids:
            if rid not in [o["id"] for o in out]:
                out.append({"id": rid, "slug": ids[rid]})
        elif rid:
            bad.append(rid)
    return out, bad


def short_evidence(fields_ev):
    """A compact evidence list for the history: one item per field."""
    out = []
    for k, items in fields_ev.items():
        for it in items if isinstance(items, list) else [items]:
            if isinstance(it, dict) and it.get("quote"):
                out.append({"field": k, "file": it.get("file"), "sha256": it.get("sha256"),
                            "locator": it.get("locator"), "quote": it.get("quote")})
                break
    return out


def error_field(msg):
    """The record field an evidence-script error is about, or None."""
    for f in sorted(RECORD_FIELDS, key=len, reverse=True):
        if re.search(r"(?<![a-z_])%s(?![a-z_])" % re.escape(f), msg):
            return f
    return None


def cmd_assemble(args):
    d, run = load_run(args.run)
    db = load_db()
    index = TextIndex(d, db)
    by = {r["id"]: r for r in db["records"]}
    slugs = {r["id"]: r["slug"] for r in db["records"]}
    taken_ids, taken_slugs = set(by), set(slugs.values())
    ex_all, ch_all = agent_files(d, "extractions"), agent_files(d, "checks")
    stages = run.get("stages") or {}
    new_records, updates, ctx = [], [], {}
    not_added, needs_human, unchecked, questions = [], [], [], []
    assigned = {}
    pending_related = []
    for c in candidates(d):
        if c.get("status") != "active":
            continue
        cid = c["cand_id"]
        ex = ex_all.get(cid)
        if not ex:
            unchecked.append({"cand_id": cid, "why": "no extraction"})
            continue
        dec = ex.get("decision")
        if dec in ("duplicate", "out-of-scope"):
            not_added.append({"cand_id": cid, "decision": dec, "target_id": ex.get("target_id"),
                              "title": (ex.get("record") or {}).get("title") or c.get("title_as_found"),
                              "why": (ex.get("judgment") or {}).get("scope_reasoning") or (ex.get("open_questions") or [""])[0]})
            continue
        if dec == "needs-human":
            needs_human.append({"cand_id": cid, "why": "extractor: " + ((ex.get("judgment") or {}).get("scope_reasoning") or
                                                                       "; ".join(ex.get("open_questions") or []))})
            continue
        ch = ch_all.get(cid)
        if not ch:
            unchecked.append({"cand_id": cid, "why": "not checked yet"})
            continue
        overall = ch.get("overall")
        if overall == "reject":
            not_added.append({"cand_id": cid, "decision": "rejected by the checker", "title": (ex.get("record") or {}).get("title"),
                              "why": ch.get("note")})
            continue
        rec = {k: v for k, v in (ex.get("record") or {}).items() if k in RECORD_FIELDS and k not in SET_BY_SCRIPT}
        evidence = {k: (v if isinstance(v, list) else [v]) for k, v in (ex.get("evidence") or {}).items()}
        target = ex.get("target_id") or c.get("record_id")
        is_update = dec == "update" or bool(c.get("record_id"))
        cur = by.get(target) if is_update else None
        # the values this run proposes to change; for a new record, every value is new
        proposed = {k for k, v in rec.items() if k != "verification" and (cur is None or cur.get(k) != v)}
        blockers, standing, applied = [], [], []

        def problem(field, msg, open_question=False):
            # A problem with a value the run changes, or with a new record, holds the record back. A problem with a
            # value the run leaves as published (an old claim, a source that cannot be stored) becomes an open
            # question and does not hold back the run's checked corrections; so does a possible newer version,
            # also for a new record, which is right as recorded until the newer one is stored.
            if open_question:
                standing.append(msg)
            else:
                (blockers if cur is None or (field is not None and field in proposed) else standing).append(msg)
        if overall not in ("accept", "accept-with-fixes"):
            problem(None, "checker: %s" % (ch.get("note") or overall))
        for field, fv in (ch.get("fields") or {}).items():
            verdict = (fv or {}).get("verdict")
            fix = (fv or {}).get("fix")
            if verdict in ("contradicted", "unsupported"):
                if fix and isinstance(fix, dict) and fix.get("evidence"):
                    oks = [check_item(index, cid, it, target)[0] for it in fix["evidence"]]
                    if all(oks):
                        rec[field] = fix.get("value")
                        evidence[field] = fix["evidence"]
                        applied.append(field)
                        continue
                    problem(field, "the checker's fix for %s did not pass the evidence check" % field)
                else:
                    problem(field, "%s is %s and the checker gave no evidence-backed fix" % (field, verdict))
        for claim in ch.get("summary_claims") or []:
            # a claim of the old summary no longer blocks once the checker's evidence-backed summary fix replaced it
            if claim.get("verdict") in ("unsupported", "contradicted") and "summary" not in applied:
                problem("summary", "summary claim %s: %r" % (claim["verdict"], (claim.get("claim") or "")[:80]))
        # something newer counts unless it already has its own record ("already recorded as CN-17")
        newer = [x for x in (ch.get("newer_versions") or []) + (ch.get("extra_urls") or [])
                 if not any(t in by and t != target for t in re.findall(r"\b[A-Z0-9]{2,6}(?:-[A-Z]{2})?-\d{2}\b", str(x)))]
        if newer:
            problem(None, "the checker found something possibly newer: %s" % "; ".join(str(x) for x in newer)[:300],
                    open_question=True)
        # a check counts only when it covers every factual field the record sets or confirms
        need = [k for k in FACT_FIELDS if (ex.get("record") or {}).get(k) is not None]
        if is_update:
            need += [k for k in ((ex.get("judgment") or {}).get("confirmed") or []) if k in FACT_FIELDS]
            need += [k for k in LEVEL_FIELDS if (by.get(target) or {}).get(k) is not None]
        verdicts = ch.get("fields") or {}
        missing = [k for k in dict.fromkeys(need) if (verdicts.get(k) or {}).get("verdict") not in VERDICTS]
        for k in missing:
            problem(k, "the checker gave no verdict for %s" % k)
        scope = ch.get("scope") or {}
        if scope.get("assessment") == "out":
            problem(None, "the checker judges it out of scope: %s" % (scope.get("note") or "no reason given"))
        elif scope.get("assessment") == "borderline" and scope.get("note") and not rec.get("scope_note"):
            rec["scope_note"] = scope["note"]  # the checker flags a borderline case the extractor did not
            applied.append("scope_note")
        new_summary = (ex.get("record") or {}).get("summary") is not None
        if new_summary and not [x for x in ch.get("summary_claims") or [] if x.get("verdict") in VERDICTS]:
            problem("summary", "the checker checked no claim of the summary")
        ev = evaluate(index, cid, dict(ex, record=rec, evidence=evidence), db)
        for e in ev["errors"]:
            problem(error_field(e), e)
        if blockers:
            needs_human.append({"cand_id": cid, "record_id": target if is_update else None,
                                "why": "; ".join(blockers + standing)[:800]})
            continue
        if standing:
            questions.append({"cand_id": cid, "record_id": target, "why": "; ".join(standing)[:800]})
        level = ev["level"]
        v_in = (ex.get("record") or {}).get("verification") or {}
        note = (v_in.get("note") or "").strip()
        if not note and target in by and dec == "update":  # a re-verification keeps the record's own note ...
            note = ((by[target].get("verification") or {}).get("note") or "").strip()
            if level != "C" and "CAUTION" in note:  # ... unless it warns about a level the evidence no longer has
                note = ""
        if level == "C" and "CAUTION" not in note:
            note = ("CAUTION: no official source confirms the title, date and status; the record rests on secondary sources. "
                    + note).strip()
        checked = "%s (%s), %s" % (ch.get("tool") or (stages.get("check") or {}).get("tool"),
                                    ch.get("model") or (stages.get("check") or {}).get("model"), ch.get("checked_on") or today())
        n_sup = len([1 for fv in (ch.get("fields") or {}).values() if (fv or {}).get("verdict") == "supported"])
        verification = {"level": level, "verified_on": today(), "method": METHOD_TOKENS[level],
                        "note": note or "Pipeline run %s; evidence in runs/%s/extractions/%s.json." % (args.run, args.run, cid),
                        "second_check": "Independent check by %s: %d field(s) supported%s." % (
                            checked, n_sup, (", fixes applied to " + ", ".join(applied)) if applied else "")}
        fields_ctx = {}
        if dec == "update" or (c.get("record_id") and dec == "record"):
            if target not in by:
                needs_human.append({"cand_id": cid, "why": "update target %r does not exist" % target})
                continue
            cur = by[target]
            changes = {k: v for k, v in rec.items() if k != "verification" and cur.get(k) != v}
            if "related" in changes:
                changes["related"], bad = norm_related(changes["related"], slugs)
                if changes["related"] == cur.get("related"):
                    changes.pop("related")
            reasons = (ex.get("judgment") or {}).get("changes") or {}
            for k in changes:
                fields_ctx[k] = {"reason": reasons.get(k) if isinstance(reasons, dict) else None,
                                 "evidence": short_evidence({k: evidence.get(k) or []})}
            if cur.get("verification", {}).get("level") != level:
                fields_ctx["verification.level"] = {"reason": "level computed from the evidence by tools/pipeline.py",
                                                    "evidence": []}
            upd = dict(changes, id=target, verification=verification)
            updates.append(upd)
            confirmed = (ex.get("judgment") or {}).get("confirmed") or []
            ctx[target] = {"reason": "pipeline run %s (%s), candidate %s" % (args.run, run["type"], cid), "fields": fields_ctx,
                           "confirmed": confirmed, "evidence": short_evidence({k: evidence.get(k) or [] for k in confirmed}),
                           "cand_id": cid}
            assigned[cid] = target
            continue
        code = jurisdiction_code(c, rec, db)
        if not code:
            needs_human.append({"cand_id": cid, "why": "no jurisdiction code (the candidate has no frame cell)"})
            continue
        nid = next_id(code, taken_ids)
        if not validate.ID_FORMAT.match(nid):
            needs_human.append({"cand_id": cid, "why": "the next ID %s does not fit the ID format" % nid})
            continue
        slug = unique_slug(slugify(rec.get("short_title") or rec.get("title")), taken_slugs)
        slugs[nid] = slug
        full = OrderedDict((k, rec.get(k)) for k in RECORD_FIELDS)
        full.update({"id": nid, "slug": slug, "verification": verification})
        full["safety_topics"] = full.get("safety_topics") or []
        pending_related.append((full, rec.get("related")))
        lc = ((index.sources.get(cid) or {}).get("main"))
        if lc and lc.get("files"):
            full["local_copy"] = lc
        new_records.append(full)
        ctx[nid] = {"reason": "found in pipeline run %s, candidate %s (%s)" % (args.run, cid, c.get("cell") or "-"),
                    "evidence": short_evidence(evidence), "cand_id": cid}
        assigned[cid] = nid
    # related links: resolve now that new IDs exist; make every link two-way
    rev = defaultdict(list)
    for full, wanted in pending_related:
        full["related"], bad = norm_related(wanted, slugs)
        if bad:
            print("WARNING  %s: related IDs that do not exist were dropped: %s" % (full["id"], ", ".join(bad)))
        for x in full["related"]:
            rev[x["id"]].append(full["id"])
    new_by = {r["id"]: r for r in new_records}
    upd_by = {u["id"]: u for u in updates}
    for tid, sources_ in rev.items():
        if tid in new_by:
            have = {x["id"] for x in new_by[tid]["related"]}
            for s in sources_:
                if s not in have:
                    new_by[tid]["related"].append({"id": s, "slug": slugs[s]})
            continue
        cur_rel = list((upd_by.get(tid) or {}).get("related") or by[tid].get("related") or [])
        have = {x.get("id") for x in cur_rel}
        add = [s for s in sources_ if s not in have]
        if not add:
            continue
        cur_rel += [{"id": s, "slug": slugs[s]} for s in add]
        if tid in upd_by:
            upd_by[tid]["related"] = cur_rel
        else:
            upd_by[tid] = {"id": tid, "related": cur_rel}
            updates.append(upd_by[tid])
        ctx.setdefault(tid, {}).setdefault("fields", {})["related"] = {
            "reason": "two-way link to %s added in run %s" % (", ".join(add), args.run), "evidence": []}
    for q in questions:  # a new record's question names the ID it was given
        if not q.get("record_id") and q.get("cand_id") in assigned:
            q["record_id"] = assigned[q["cand_id"]]
    ex_stage = stages.get("extract") or {}
    prov = {"date": today(), "agent": ex_stage.get("tool") or (run.get("coordinator") or {}).get("tool"),
            "model": ex_stage.get("model") or (run.get("coordinator") or {}).get("model"),
            "scope": "pipeline run %s (%s: %s)" % (args.run, run["type"], run.get("scope") or "queue"),
            "run_id": args.run, "stages": stages}
    out = {"provenance": prov, "records": new_records, "updates": updates, "history_context": ctx,
           "assigned": assigned, "not_added": not_added, "needs_human": needs_human, "questions": questions,
           "unchecked": unchecked,
           "summary": "%d new, %d update(s), %d not added, %d need a human, %d merged with an open question, %d not ready" % (
               len(new_records), len(updates), len(not_added), len(needs_human), len(questions), len(unchecked))}
    write_json(d / "pass.json", out)
    run["status"] = "assembled"
    save_run(d, run)
    print(out["summary"])
    for x in needs_human:
        print("  needs-human %-6s %s" % (x["cand_id"], x["why"][:140]))
    for x in questions:
        print("  question    %-6s %s" % (x["cand_id"], x["why"][:140]))
    for x in unchecked:
        print("  not ready   %-6s %s" % (x["cand_id"], x["why"]))
    print("Next: python3 tools/merge.py runs/%s/pass.json --dry-run" % args.run)
    return 0


# ----------------------------------------------------------------------------- report

def cmd_report(args):
    d, run = load_run(args.run)
    db = load_db()
    by = {r["id"]: r for r in db["records"]}
    p = read_json(d / "pass.json", {}) or {}
    events = [e for e in history.load() if e.get("run_id") == args.run]
    merged = bool(events)
    agr = read_json(d / "agreement.json", {}) or {}
    cands = candidates(d)
    logs = read_log(d)
    ex = agent_files(d, "extractions")
    sample = read_json(d / "sample.json", {}) or {}
    st = run.get("stages") or {}
    added = [e for e in events if e["event"] == "added"]
    changed = [e for e in events if e["event"] == "changed"]
    rever = [e for e in events if e["event"] == "re-verified"]
    accepted = sorted(set((p.get("assigned") or {}).values()) & {e["record_id"] for e in added + changed + rever})
    if accepted and not sample.get("human"):
        rng = random.Random("human:" + args.run)
        sample["human"] = sorted(rng.sample(accepted, min(5, len(accepted))))
        write_json(d / "sample.json", sample)
    L = ["# Run %s" % args.run, "",
         "<!-- coordinator: one paragraph here on what a human should look at first -->", "",
         "Type: %s. Scope: %s. Started %s; report written %s.%s" % (
             run["type"], run.get("scope") or "refresh queue", run["started"], today(),
             "" if merged else " **Not merged yet**: the lists below come from pass.json."), "",
         "| Stage | Tool | Model | Date |", "|---|---|---|---|"]
    for s in STAGES:
        x = st.get(s) or {}
        L.append("| %s | %s | %s | %s |" % (s, x.get("tool") or "-", x.get("model") or "-", x.get("date") or "-"))
    sc = Counter(c.get("status") for c in cands)
    L += ["", "## Summary", "",
          "- Candidates: %d (%s)" % (len(cands), ", ".join("%s %d" % kv for kv in sc.most_common())),
          "- Added: %d; fields changed: %d in %d record(s); re-verified without change: %d" % (
              len(added) if merged else len(p.get("records") or []), len(changed), len({e["record_id"] for e in changed}),
              len(rever)),
          "- Not added: %d; need a human: %d; not ready: %d" % (
              len(p.get("not_added") or []), len(p.get("needs_human") or []), len(p.get("unchecked") or []))]
    if agr.get("overall_field_agreement") is not None:
        L.append("- Repeatability: %.0f%% field agreement between blind double extractions (%d pair(s))" % (
            100 * agr["overall_field_agreement"], agr.get("compared") or 0)
            + ("; %.0f%% agreement on the resulting records (%d field values; in a refresh run the first figure counts "
               "only fields that an extraction changed)" % (100 * agr["resulting_record_agreement"],
                                                            agr.get("resulting_record_fields") or 0)
               if agr.get("resulting_record_agreement") is not None else ""))
    L += ["", "## Added", ""]
    rows = added if merged else [{"record_id": r["id"], "new": "%s; %s; level %s" % (
        r.get("short_title"), r.get("status"), r["verification"]["level"])} for r in p.get("records") or []]
    L += ["- **%s** %s" % (e["record_id"], e.get("new") or "") for e in rows] or ["None."]
    L += ["", "## Changed", ""]
    L += ["- **%s** %s%s" % (e["record_id"], history.describe(e), (" (%s)" % e["reason"]) if e.get("reason") else "")
          for e in changed] or ["None."]
    L += ["", "## Re-verified without change", ""]
    L += [", ".join(e["record_id"] for e in rever) or "None."]
    L += ["", "## Needs a human", "", "Held back: a value this run changes is not settled. The published record stays as it was."
          if p.get("needs_human") else "", ""]
    L += ["- %s: %s" % (x["cand_id"], x["why"]) for x in p.get("needs_human") or []] or ["None."]
    L += ["", "## Merged with an open question", "", "The run's checked corrections are merged; these points about values "
          "it left as published are open questions (GitHub issues, `pipeline.py questions --sync`)." if p.get("questions")
          else "", ""]
    L += ["- %s: %s" % (x["cand_id"], x["why"]) for x in p.get("questions") or []] or ["None."]
    L += ["", "## Not added", ""]
    L += ["- %s %s: %s%s" % (x["cand_id"], x.get("title") or "", x.get("decision"),
                             (" (%s)" % x["why"]) if x.get("why") else "") for x in p.get("not_added") or []] or ["None."]
    dropped = [c for c in cands if c.get("status") in ("in-register", "duplicate-in-run", "out-of-scope", "refresh-request")]
    if dropped:
        L += ["", "Dropped before extraction:", ""]
        L += ["- %s (%s): %s" % (c.get("title_as_found"), c.get("cell") or "-", c["status"] +
                                 (" " + (c.get("record_id") or c.get("duplicate_of") or "") if c.get("record_id") or c.get("duplicate_of") else ""))
              for c in dropped]
    if agr.get("fields"):
        L += ["", "## Repeatability", "", "Blind second extraction of %d candidate(s) (AGENTS.md section 7.4)." % agr.get("compared", 0), "",
              "| Field | Compared | Agree |", "|---|---:|---:|"]
        for f, t in agr["fields"].items():
            if t["compared"]:
                L.append("| %s | %d | %d |" % (f, t["compared"], t["agree"]))
    L += ["", "## Human sample", ""]
    if sample.get("human"):
        L += ["Check these records against their stored sources, then log the result, for example:", "",
              "    python3 tools/pipeline.py log-human --run %s --id %s --result ok --note \"...\"" % (args.run, sample["human"][0]), ""]
        L += ["- [ ] %s %s" % (rid, (by.get(rid) or {}).get("short_title") or "") for rid in sample["human"]]
    else:
        L.append("Drawn after the merge.")
    humans = [e for e in events if e["event"] in ("human-checked", "scope-decision")]
    if humans:
        L += ["", "Logged:", ""] + ["- %s %s (%s)" % (e["record_id"], history.describe(e), e.get("model") or "human")
                                    for e in humans]
    if run["type"] == "discover":
        oc = Counter(l.get("outcome") for l in logs)
        L += ["", "## Search coverage", "",
              "%d of %d cells logged (%s)." % (len({l.get('cell') for l in logs}), len(run.get("cells") or []),
                                                ", ".join("%s %d" % kv for kv in oc.most_common()))]
        blocked = [l for l in logs if l.get("outcome") == "blocked"]
        L += ["- blocked: %s: %s" % (l.get("cell"), (l.get("note") or "")[:120]) for l in blocked]
        missing = (read_json(d / "candidates.json", {}) or {}).get("cells_without_log") or []
        if missing:
            L.append("- not searched: %s" % ", ".join(missing))
    review = defaultdict(set)
    for cid, res in ((read_json(d / "evidence.json", {}) or {}).get("extractions") or {}).items():
        for w in res.get("warnings") or []:
            m = re.search(r"host (\S+) is not recognised as official", w)
            if m and m.group(1) != "(unknown)":
                review[strip_www(m.group(1))].add(cid)
    if review:
        L += ["", "## Hosts to review", "",
              "Quotes from these hosts counted as secondary because the host is neither a government domain nor listed in "
              "`pipeline/official-sites.json`. If the issuing body runs the host, or uses it as its own channel, record it "
              "with `python3 tools/pipeline.py hosts --add HOST --code CODE --status official --by NAME --operator ... "
              "--evidence-url ...`, and run `evidence` again.", ""]
        L += ["- %s: %s" % (h, ", ".join(sorted(c))) for h, c in sorted(review.items())]
    leads = [(cid, x) for cid, e in ex.items() for x in (e or {}).get("leads") or []]
    oq = [(cid, x) for cid, e in ex.items() for x in (e or {}).get("open_questions") or []]
    if leads or oq:
        L += ["", "## Leads and open questions", ""]
        L += ["- lead from %s: %s" % (cid, x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)) for cid, x in leads]
        L += ["- %s: %s" % (cid, x) for cid, x in oq]
    text = "\n".join(L) + "\n"
    old = (d / "report.md").read_text(encoding="utf-8") if (d / "report.md").is_file() else ""
    m = re.search(r"<!-- coordinator: .*?-->\n(.*?)\n\nType:", old, re.S)
    if m and m.group(1).strip():
        text = text.replace("<!-- coordinator: one paragraph here on what a human should look at first -->",
                            "<!-- coordinator: one paragraph here on what a human should look at first -->\n" + m.group(1).strip())
    (d / "report.md").write_text(text, encoding="utf-8")
    if merged:
        run["status"] = "merged"
        save_run(d, run)
        build.write_history_md()  # HISTORY.md links each run to its report, which exists only from now on
    print("Written runs/%s/report.md (%s)" % (args.run, "merged" if merged else "before merge"))
    return 0


# ----------------------------------------------------------------------------- human and scope events

def cmd_log_human(args):
    db = load_db()
    if args.id not in {r["id"] for r in db["records"]}:
        raise SystemExit("No record %s" % args.id)
    if args.result not in ("ok", "problem"):
        raise SystemExit("--result is ok or problem")
    history.append([history.event(args.id, "human-checked", run_id=args.run, new="%s: %s" % (args.result, args.note or ""),
                                  tool="human", model=args.by)])
    build.write_js(build.normalise(db))
    build.write_history_md()
    print("Logged a human check of %s (%s)." % (args.id, args.result))
    if args.result == "problem":
        print("Fix it with a refresh run: python3 tools/pipeline.py new --type refresh --scope ids:%s" % args.id)
    return 0


def cmd_log_scope(args):
    db = load_db()
    rec = {r["id"]: r for r in db["records"]}.get(args.id)
    if not rec:
        raise SystemExit("No record %s" % args.id)
    history.append([history.event(args.id, "scope-decision", run_id=args.run, new="%s: %s" % (args.decision, args.note),
                                  tool="human", model=args.by)])
    line = "- **%s** (%s): %s. %s *%s, %s.*\n" % (rec.get("short_title") or rec["title"], args.id, args.decision,
                                                   args.note.rstrip(".") + ".", args.by or "Maintainer", today())
    with open(SCOPE_DECISIONS, "a", encoding="utf-8") as f:
        f.write(line)
    build.write_js(build.normalise(db))
    build.write_history_md()
    print("Logged the scope decision and added it to pipeline/scope-decisions.md.")
    if args.decision == "out":
        print("Records are never deleted: give the record a status and a note in a refresh run, or keep it with a scope note.")
    return 0


# ----------------------------------------------------------------------------- official sites

def cmd_hosts(args):
    data = load_sites()
    sites = data.setdefault("sites", [])
    if args.add:
        host = strip_www(args.add)
        if not (args.code and args.status and args.by):
            raise SystemExit("--add needs --code, --status and --by")
        if args.status not in SITE_STATUSES:
            raise SystemExit("--status must be one of %s" % ", ".join(SITE_STATUSES))
        codes = {j["code"] for j in load_frame().get("jurisdictions") or []}
        if args.code not in codes:
            raise SystemExit("%s is not a jurisdiction in pipeline/frame.json" % args.code)
        if args.status != "proposed" and not (args.evidence_url or args.note):
            raise SystemExit("a decision needs --evidence-url (the page that shows who runs the host) or --note")
        entry = OrderedDict([("code", args.code), ("host", host), ("status", args.status), ("operator", args.operator),
                             ("kind", args.kind),
                             ("evidence", {"url": args.evidence_url, "quote": args.quote, "checked_on": today()}
                              if args.evidence_url else None),
                             ("decided_by", args.by), ("decided_on", today()), ("note", args.note)])
        old = next((e for e in sites if e.get("code") == args.code and strip_www(e.get("host")) == host), None)
        if old:
            entry["previous"] = {k: old.get(k) for k in ("status", "decided_by", "decided_on", "note")}
            sites[sites.index(old)] = entry
        else:
            sites.append(entry)
        sites.sort(key=lambda e: (e["code"], e["host"]))
        write_json(SITES, data)
        print("%s %s: %s (%s)%s" % (args.code, host, args.status, args.by, ", replacing %s" % old["status"] if old else ""))
        return 0
    if args.code or args.pending:
        rows = [e for e in sites if (not args.code or e["code"] == args.code)
                and (not args.pending or e["status"] == "proposed" or e.get("decided_by") == "seed")]
        for e in rows:
            print("%-7s %-40s %-13s %-10s %s" % (e["code"], e["host"], e["status"], e.get("decided_by") or "-",
                                                (e.get("operator") or e.get("note") or "")[:70]))
        print("%d entr%s" % (len(rows), "y" if len(rows) == 1 else "ies"))
        return 0
    st = Counter(e["status"] for e in sites)
    seeds = sum(1 for e in sites if e.get("decided_by") == "seed")
    print("pipeline/official-sites.json: %d sites; %s." % (len(sites), ", ".join("%s %d" % kv for kv in st.most_common())))
    print("%d official entries are seeds from records' official_url, not yet reviewed by a person; %d proposed entries "
          "wait for a decision. List them with --pending." % (seeds, st.get("proposed", 0)))
    return 0


# ----------------------------------------------------------------------------- questions for humans

QUESTIONS = ROOT / "pipeline" / "questions.json"
DECIDERS = {"OWNER", "MEMBER", "COLLABORATOR"}
ID_TOKEN = re.compile(r"\b[A-Z0-9]{2,6}(?:-[A-Z]{2})?-\d{2}\b")
HOST_WARNING = re.compile(r"host (\S+) is not recognised as official")


def github_repo():
    """owner/name of the GitHub repository, from questions.json or the origin remote."""
    q = read_json(QUESTIONS, {}) or {}
    if q.get("repo"):
        return q["repo"]
    url = subprocess.run(["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"], capture_output=True,
                         text=True).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if not m:
        raise SystemExit("Cannot tell the GitHub repository; set \"repo\" in pipeline/questions.json")
    return m.group(1)


def gh(*args, input_text=None):
    if not shutil.which("gh"):
        raise SystemExit("The GitHub CLI (gh) is needed for questions --sync and --apply")
    res = subprocess.run(["gh"] + list(args), capture_output=True, text=True, input=input_text)
    if res.returncode:
        raise SystemExit("gh %s failed: %s" % (" ".join(args[:2]), res.stderr.strip()[:300]))
    return res.stdout


def run_order():
    """Run IDs in the order their events entered the history; runs without events after them, by start date."""
    order = []
    for e in history.load():
        if e.get("run_id") and e["run_id"] not in order:
            order.append(e["run_id"])
    rest = sorted((read_json(p / "run.json", {}) or {}).get("started", "") + " " + p.name
                  for p in RUNS.iterdir() if (p / "run.json").is_file() and p.name not in order) if RUNS.is_dir() else []
    return [r for r in order if (RUNS / r / "run.json").is_file()] + [x.split(" ", 1)[1] for x in rest]


def collect_questions(db):
    """Every open question the pipeline's files imply, keyed: record questions from the runs' pass.json (the latest
    run that touched a record decides), hosts waiting for a decision, and human samples not yet logged."""
    by = {r["id"]: r for r in db["records"]}
    events = history.load()
    out = OrderedDict()
    state = {}  # record ID -> open question from the latest run that raised one, or None once a later run settled it
    for run_id in run_order():
        p = read_json(RUNS / run_id / "pass.json", {}) or {}
        # a record counts as checked again only when the run changed or re-verified it, not when it only gained links
        touched = {u.get("id") for u in p.get("updates") or [] if set(u) - {"id", "related"}} | \
                  {r.get("id") for r in p.get("records") or []}
        raised = {}
        for x, held in [(x, True) for x in p.get("needs_human") or []] + [(x, False) for x in p.get("questions") or []]:
            rid = x.get("record_id") or (x.get("cand_id") if x.get("cand_id") in by else None)
            key = "record:%s@%s" % (rid, run_id) if rid else "candidate:%s@%s" % (x.get("cand_id"), run_id)
            title = None
            if not rid:  # a candidate has no record yet: name it from its extraction or the collector's candidate
                ex = read_json(RUNS / run_id / "extractions" / ("%s.json" % x.get("cand_id")), {}) or {}
                cand = next((c for c in (read_json(RUNS / run_id / "candidates.json", {}) or {}).get("candidates") or []
                             if c.get("cand_id") == x.get("cand_id")), {})
                title = (ex.get("record") or {}).get("title") or cand.get("title_as_found")
            raised[rid or key] = {"key": key, "kind": "record" if rid else "candidate", "subject": rid or x.get("cand_id"),
                                  "run_id": run_id, "held_back": held, "why": x.get("why"), "records": [rid] if rid else [],
                                  "title": title}
        for rid in touched:
            if rid not in raised:
                state[rid] = None  # a later run checked the record without raising anything
        state.update(raised)
    decided = {(e["record_id"], e.get("run_id")) for e in events if e.get("event") == "human-decision"}
    for subj, q in state.items():
        if q and (q["subject"], q["key"]) not in decided:
            out[q["key"]] = q
    sites = load_sites()
    known = {strip_www(e["host"]) for e in sites.get("sites") or []}
    for e in sites.get("sites") or []:
        if e["status"] == "proposed":
            out["host:%s" % strip_www(e["host"])] = {"key": "host:%s" % strip_www(e["host"]), "kind": "host",
                                                     "subject": strip_www(e["host"]), "code": e["code"],
                                                     "why": e.get("note"), "operator": e.get("operator"),
                                                     "evidence": e.get("evidence"), "records": []}
    for run_id in run_order():
        for cid, res in ((read_json(RUNS / run_id / "evidence.json", {}) or {}).get("extractions") or {}).items():
            for w in res.get("warnings") or []:
                m = HOST_WARNING.search(w)
                h = strip_www(m.group(1)) if m else None
                if not h or h == "(unknown)" or h in known:
                    continue
                q = out.setdefault("host:%s" % h, {"key": "host:%s" % h, "kind": "host", "subject": h,
                                                   "code": re.sub(r"-\d+$", "", cid), "records": [],
                                                   "why": "Quotes from this host counted as secondary because it is "
                                                          "neither a government domain nor in pipeline/official-sites.json."})
                if cid not in q["records"]:
                    q["records"].append(cid)
    logged = {(e.get("run_id"), e["record_id"]) for e in events if e.get("event") == "human-checked"}
    for run_id in run_order():
        todo = [rid for rid in (read_json(RUNS / run_id / "sample.json", {}) or {}).get("human") or []
                if (run_id, rid) not in logged and rid in by]
        if todo:
            out["sample:%s" % run_id] = {"key": "sample:%s" % run_id, "kind": "sample", "subject": run_id,
                                         "run_id": run_id, "records": todo,
                                         "why": "Human sample of run %s: check each record against its stored sources." % run_id}
    return out


def question_title(q, by):
    if q["kind"] == "candidate":
        return "Candidate %s, %s: not added, open question from run %s" % (q["subject"], (q.get("title") or "")[:90], q["run_id"])
    if q["kind"] == "record":
        r = by.get(q["subject"]) or {}
        return "%s %s: open question from run %s" % (q["subject"], r.get("short_title") or r.get("title") or "", q["run_id"])
    if q["kind"] == "host":
        return "Is %s an official site for %s?" % (q["subject"], q.get("code"))
    return "Human sample of run %s (%d records)" % (q["subject"], len(q["records"]))


def question_body(q, by, repo):
    blob = "https://github.com/%s/blob/main/" % repo
    L = []
    if q["kind"] in ("record", "candidate"):
        r = by.get(q["subject"]) or {}
        run = q["run_id"]
        L += [("**Record:** %s, %s" % (q["subject"], r.get("title") or "")) if q["kind"] == "record" else
              ("**Candidate:** %s, %s (not in the register)" % (q["subject"], q.get("title") or "")),
              "**Run:** [%s](%sruns/%s/report.md)" % (run, blob, run),
              "**Now:** " + ("the run's change is held back; the published record is unchanged." if q.get("held_back")
                             else "the run's checked corrections are merged; this point about a published value is open."),
              "", "### Question", "", q.get("why") or "", "",
              "If nobody decides, the published record stays as it is and the record shows this question.", "",
              "### Evidence", ""]
        for k in ("official_url", "secondary_url"):
            if r.get(k):
                L.append("- %s: %s" % (k, r[k]))
        for sub in ("extractions", "checks", "extractions-blind"):
            if (RUNS / run / sub / ("%s.json" % q["subject"])).is_file():
                L.append("- %s: %sruns/%s/%s/%s.json" % (sub, blob, run, sub, q["subject"]))
        L += ["", "### How to decide", "",
              "A maintainer comments one decision; it is applied at the start of the next pipeline run "
              "(`python3 tools/pipeline.py questions --apply`), recorded in `data/history.jsonl` and linked here.", "",
              "- `decide: keep`: the published values stay.",
              "- `decide: accept`: apply the run's extraction for this record (when its change was held back and the "
              "record has not changed since).",
              "- `decide: set <field> = <value>`, one line per field, with `source: <URL>`: set values yourself.",
              "- `decide: in` or `decide: out`, with a reason: a scope decision.", "",
              "Anyone can add evidence in the comments."]
    elif q["kind"] == "host":
        ev = q.get("evidence") or {}
        L += ["**Host:** %s (jurisdiction %s)" % (q["subject"], q.get("code")), "", "### Question", "",
              "Does a public body run this host, or use it as its own channel (AGENTS.md section 7.6)? %s" % (q.get("why") or ""), ""]
        if q.get("operator"):
            L.append("Operator check: %s" % q["operator"])
        if ev.get("url"):
            L.append("Checked page: %s%s" % (ev["url"], (' ("%s")' % ev["quote"]) if ev.get("quote") else ""))
        if q.get("records"):
            L.append("Quoted for: %s" % ", ".join(q["records"]))
        L += ["", "Until decided, quotes from this host count as secondary.", "", "### How to decide", "",
              "- `decide: official`, optionally with `operator: <who runs it>`",
              "- `decide: not official`"]
    else:
        L += ["**Run:** [%s](%sruns/%s/report.md)" % (q["subject"], blob, q["subject"]), "",
              "Check each record against its stored sources (the run report and the record page link them):", ""]
        L += ["- [ ] %s %s" % (rid, (by.get(rid) or {}).get("short_title") or "") for rid in q["records"]]
        L += ["", "### How to report", "", "One line per record in a comment: `ok <ID> <note>` or `problem <ID> <note>`. "
              "Each line becomes a `human-checked` event in the record's history; a problem queues the record for a refresh run."]
    L += ["", "<!-- question-key: %s -->" % q["key"]]
    return "\n".join(L)


def ensure_labels(repo):
    for name, color, desc in (("question", "d876e3", "A question for a maintainer from the pipeline"),
                              ("question:record", "c5def5", "A record's open question"),
                              ("question:host", "c5def5", "Is this host an official site?"),
                              ("question:sample", "c5def5", "Human sample of a run")):
        gh("label", "create", name, "--repo", repo, "--color", color, "--description", desc, "--force")


def parse_decisions(comments, kind):
    """The latest decision by a maintainer, as (comment, [parsed lines]); None when there is none."""
    for c in reversed(comments):
        if c.get("author_association") not in DECIDERS:
            continue
        body = c.get("body") or ""
        if kind == "sample":
            lines = re.findall(r"(?im)^\s*(ok|problem)\s+(\S+)\s*:?\s*(.*)$", body)
        else:
            lines = re.findall(r"(?im)^\s*(decide|source|operator)\s*:\s*(.+?)\s*$", body)
        if lines and (kind == "sample" or any(k.lower() == "decide" for k, _ in lines)):
            return c, lines
    return None


def apply_record_decision(q, comment, lines, db, dry):
    rid, run_id = q["subject"], q["run_id"]
    num = q.get("issue")
    who = (comment.get("user") or {}).get("login") or "maintainer"
    decides = [v for k, v in lines if k.lower() == "decide"]
    source = next((v for k, v in lines if k.lower() == "source"), None)
    note = "decided in issue #%s by %s: %s" % (num, who, comment.get("html_url"))
    first = decides[0].strip()
    if first.lower() in ("keep",) or (first.lower() == "accept" and not q.get("held_back")):
        if not dry:
            history.append([history.event(rid, "human-decision", run_id=q["key"], new="keep", reason=note,
                                          tool="GitHub issue #%s" % num, model=who)])
        return "kept the published values"
    if first.lower() in ("in", "out") or re.match(r"(?i)^(in|out)\b", first):
        dec = first.split()[0].lower()
        reason = first[len(dec):].strip(" :,-") or "see issue #%s" % num
        if not dry:
            cmd_log_scope(argparse.Namespace(run=None, id=rid, decision=dec, note="%s (issue #%s)" % (reason, num), by=who))
            history.append([history.event(rid, "human-decision", run_id=q["key"], new="scope %s" % dec, reason=note,
                                          tool="GitHub issue #%s" % num, model=who)])
        return "scope decision: %s" % dec
    updates = {}
    if first.lower() == "accept":
        later = [e for e in history.load() if e["record_id"] == rid and e.get("run_id") not in (run_id, q["key"])]
        order = run_order()
        if any(e.get("run_id") in order and order.index(e["run_id"]) > order.index(run_id) for e in later):
            return "not applied: the record changed after run %s; decide with `set` instead" % run_id
        ex = read_json(RUNS / run_id / "extractions" / ("%s.json" % rid), {}) or {}
        updates = {k: v for k, v in (ex.get("record") or {}).items() if k in RECORD_FIELDS and k not in SET_BY_SCRIPT
                   and k != "verification"}
    else:
        for d in decides:
            m = re.match(r"(?i)^set\s+([a-z_]+)\s*=\s*(.+)$", d)
            if not m or m.group(1) not in RECORD_FIELDS or m.group(1) in SET_BY_SCRIPT or m.group(1) == "verification":
                return "not applied: cannot read %r (use keep, accept, in, out, or set <field> = <value>)" % d
            val = m.group(2).strip()
            try:
                val = json.loads(val)
            except ValueError:
                val = None if val.lower() == "null" else val
            updates[m.group(1)] = val
    if not updates:
        return "not applied: nothing to change"
    if dry:
        return "would set %s" % ", ".join(sorted(updates))
    cur = {r["id"]: r for r in db["records"]}[rid]
    vnote = ((cur.get("verification") or {}).get("note") or "").rstrip()
    upd = dict(updates, id=rid, verification={"verified_on": today(), "note": (vnote + " Human decision in issue #%s (%s)%s."
                                                                                % (num, who, ": source " + source if source else "")).strip()})
    src = {"provenance": {"date": today(), "agent": "GitHub issue #%s" % num, "model": who, "scope": note,
                          "run_id": q["key"]},
           "records": [], "updates": [upd],
           "history_context": {rid: {"reason": note, "evidence": [{"url": source}] if source else [],
                                     "fields": {k: {"reason": note, "evidence": [{"url": source}] if source else []}
                                                for k in updates}}}}
    tmp = Path(tempfile.mkstemp(suffix=".json")[1])
    tmp.write_text(json.dumps(src, ensure_ascii=False), encoding="utf-8")
    import merge  # noqa: E402  (same folder)
    rc = merge.main([str(tmp)])
    tmp.unlink()
    if rc:
        return "not applied: merge.py refused it (see its output)"
    history.append([history.event(rid, "human-decision", run_id=q["key"], new="set %s" % ", ".join(sorted(updates)),
                                  reason=note, tool="GitHub issue #%s" % num, model=who)])
    return "set %s" % ", ".join(sorted(updates))


def cmd_questions(args):
    db = load_db()
    by = {r["id"]: r for r in db["records"]}
    reg = read_json(QUESTIONS, {}) or {}
    reg.setdefault("about", "Open questions the pipeline cannot settle, each a GitHub issue (AGENTS.md section 7.7). "
                            "Written by tools/pipeline.py questions; decisions are applied with --apply and recorded "
                            "in data/history.jsonl.")
    items = OrderedDict((q["key"], q) for q in reg.get("questions") or [])
    found = collect_questions(db)
    repo = None
    if args.apply:
        repo = github_repo()
        applied = 0
        for key, q in items.items():
            if q.get("state") != "open" or not q.get("issue"):
                continue
            comments = json.loads(gh("api", "repos/%s/issues/%s/comments" % (repo, q["issue"]), "--paginate") or "[]")
            got = parse_decisions(comments, q["kind"])
            if not got:
                continue
            comment, lines = got
            who = (comment.get("user") or {}).get("login") or "maintainer"
            if q["kind"] in ("record", "candidate"):
                result = apply_record_decision(q, comment, lines, db, args.dry_run)
            elif q["kind"] == "host":
                dec = next(v for k, v in lines if k.lower() == "decide").strip().lower()
                op = next((v for k, v in lines if k.lower() == "operator"), None) or q.get("operator")
                if dec not in ("official", "not official"):
                    result = "not applied: use `decide: official` or `decide: not official`"
                else:
                    result = "host %s" % dec
                    if not args.dry_run:
                        cmd_hosts(argparse.Namespace(add=q["subject"], code=q.get("code"), status=dec, by=who, operator=op,
                                                     kind=None, evidence_url=comment.get("html_url"), quote=None,
                                                     note="decided in issue #%s" % q["issue"], pending=False))
            else:
                done = []
                for res, rid, note in lines:
                    if rid in q["records"] and not args.dry_run:
                        cmd_log_human(argparse.Namespace(run=q["subject"], id=rid, result=res.lower(),
                                                         note="%s (issue #%s)" % (note, q["issue"]), by=who))
                    done.append("%s %s" % (rid, res.lower()))
                result = "logged " + ", ".join(done)
            print("#%-5s %-40s %s" % (q["issue"], key, result))
            if result.startswith("not applied"):
                if not args.dry_run:
                    gh("issue", "comment", str(q["issue"]), "--repo", repo, "--body", "Not applied: %s" % result[13:])
                continue
            applied += 1
            if not args.dry_run and q["kind"] != "sample":
                q.update(state="decided", closed=today(), resolution=result)
                gh("issue", "close", str(q["issue"]), "--repo", repo, "--comment",
                   "Applied by `pipeline.py questions --apply`: %s. Recorded in data/history.jsonl." % result)
        if not args.dry_run:
            db = load_db()
            found = collect_questions(db)  # decisions may have settled samples and hosts
        print("%d decision(s) %s." % (applied, "found (dry run)" if args.dry_run else "applied"))
    for key, q in found.items():  # new questions, and new facts about open ones
        old = items.get(key)
        if old and old.get("state") == "open":
            old.update({k: v for k, v in q.items() if k not in ("issue", "url", "opened", "state")})
        elif not old:
            items[key] = dict(q, state="open", issue=None, url=None, opened=today(), closed=None, resolution=None)
    for key, q in items.items():  # open questions nothing implies any more are settled
        if q.get("state") == "open" and key not in found:
            q.update(state="settled", closed=today(), resolution=q.get("resolution") or "settled by a later run or decision")
    if args.sync:
        repo = repo or github_repo()
        if not args.dry_run:
            ensure_labels(repo)
        for key, q in items.items():
            if q["state"] == "open" and not q.get("issue"):
                title, body = question_title(q, by), question_body(q, by, repo)
                if args.dry_run:
                    print("would open: %s" % title)
                    continue
                url = gh("issue", "create", "--repo", repo, "--title", title, "--body-file", "-", "--label", "question",
                         "--label", "question:%s" % ("record" if q["kind"] == "candidate" else q["kind"]),
                         input_text=body).strip().splitlines()[-1]
                q.update(issue=int(url.rstrip("/").rsplit("/", 1)[1]), url=url)
                print("opened #%s %s" % (q["issue"], title))
            elif q["state"] == "settled" and q.get("issue") and not q.get("closed_on_github"):
                if args.dry_run:
                    print("would close #%s (%s)" % (q["issue"], q["resolution"]))
                    continue
                gh("issue", "close", str(q["issue"]), "--repo", repo, "--comment",
                   "Closed by `pipeline.py questions --sync`: %s." % q["resolution"])
                q["closed_on_github"] = True
    if (args.sync or args.apply) and not args.dry_run:  # listing only reads
        reg["questions"] = list(items.values())
        write_json(QUESTIONS, reg)
        build.write_js(build.normalise(load_db()))
    st = Counter(q["state"] for q in items.values())
    kinds = Counter(q["kind"] for q in items.values() if q["state"] == "open")
    print("Questions: %s; open by kind: %s%s" % (", ".join("%s %d" % kv for kv in st.most_common()) or "none",
                                                 ", ".join("%s %d" % kv for kv in kinds.most_common()) or "-",
                                                 " (dry run: nothing written)" if args.dry_run else ""))
    if not args.sync and not args.apply:
        for q in items.values():
            if q["state"] == "open":
                print("  %-7s %-34s %s" % ("#%s" % q["issue"] if q.get("issue") else "-", q["key"][:34],
                                           (q.get("why") or "")[:90]))
    return 0


# ----------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Pipeline scripts (AGENTS.md sections 5 to 7).")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("new", help="create a run")
    s.add_argument("--type", required=True)
    s.add_argument("--scope")
    s.add_argument("--label", help="short name for the run ID")
    s.add_argument("--tool")
    s.add_argument("--model")
    s.add_argument("--days", type=int)
    s.add_argument("--limit", type=int, default=25, help="refresh: records taken from the queue")
    s.add_argument("--group-size", type=int, default=10)
    s.add_argument("--leads", help="discover: follow up only these leads, a JSON file {\"leads\": [{\"lead\", \"cell\", \"seen_in\", \"url\"}]}")
    s = sub.add_parser("status")
    s.add_argument("--run", required=True)
    s = sub.add_parser("stage", help="record the tool and model of a stage")
    s.add_argument("--run", required=True)
    s.add_argument("--stage", required=True)
    s.add_argument("--tool", required=True)
    s.add_argument("--model", required=True)
    s = sub.add_parser("dedupe")
    s.add_argument("--run", required=True)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("textify")
    s.add_argument("--run", required=True)
    s.add_argument("--force", action="store_true")
    s.add_argument("--ocr-lang", default="eng")
    for name in ("evidence", "compare", "assemble", "report"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--run", required=True)
    s.add_argument("--share", type=float, default=0.10)
    s.add_argument("--min", type=int, default=5)
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("queue")
    s.add_argument("--days", type=int, default=STALE_DAYS)
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("frame")
    s.add_argument("--due", action="store_true")
    s.add_argument("--report", action="store_true")
    s.add_argument("--days", type=int)
    s.add_argument("--add")
    s.add_argument("--name")
    s.add_argument("--level")
    s.add_argument("--region")
    s.add_argument("--parent")
    s = sub.add_parser("hosts", help="the curated list of official sites")
    s.add_argument("--code")
    s.add_argument("--pending", action="store_true", help="proposed entries and unreviewed seeds")
    s.add_argument("--add", metavar="HOST")
    s.add_argument("--status")
    s.add_argument("--by")
    s.add_argument("--operator")
    s.add_argument("--kind")
    s.add_argument("--evidence-url")
    s.add_argument("--quote")
    s.add_argument("--note")
    s = sub.add_parser("questions", help="open questions for humans, as GitHub issues")
    s.add_argument("--sync", action="store_true", help="open issues for new questions and close settled ones")
    s.add_argument("--apply", action="store_true", help="apply maintainers' decisions from the issues")
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("log-human")
    s.add_argument("--run")
    s.add_argument("--id", required=True)
    s.add_argument("--result", required=True)
    s.add_argument("--note", default="")
    s.add_argument("--by")
    s = sub.add_parser("log-scope")
    s.add_argument("--run")
    s.add_argument("--id", required=True)
    s.add_argument("--decision", required=True, choices=["in", "out", "kept with a scope note"])
    s.add_argument("--note", required=True)
    s.add_argument("--by")
    args = ap.parse_args(argv)
    cmds = {"new": cmd_new, "status": cmd_status, "stage": cmd_stage, "dedupe": cmd_dedupe, "textify": cmd_textify,
            "evidence": cmd_evidence, "sample": cmd_sample, "compare": cmd_compare, "queue": cmd_queue,
            "assemble": cmd_assemble, "report": cmd_report, "frame": cmd_frame, "log-human": cmd_log_human,
            "log-scope": cmd_log_scope, "hosts": cmd_hosts, "questions": cmd_questions}
    if not args.cmd:
        ap.print_help()
        return 2
    return cmds[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
