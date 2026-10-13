#!/usr/bin/env python3
"""Publish the register to Hugging Face: a dataset, a gated dataset of source documents, and a Space.

    python3 tools/publish_hf.py                     # build the three folders under dist/hf/ and stop
    python3 tools/publish_hf.py --push              # build and upload (creates the repos if needed)
    python3 tools/publish_hf.py --push --private    # upload as private repos, for a review before going public

Repos (change with --namespace and --name):
  datasets/<namespace>/<name>           records, topics, related links and the source-file manifest as Parquet,
                                        the full JSON, the method (AGENTS.md) and the quality reports
  datasets/<namespace>/<name>-archive   the stored copies of official sources; gated, so a free account is needed
  spaces/<namespace>/<name>             the web app as a static Space

Copies of third-party pages (law firms, newspapers, NGOs, think tanks) are kept out of the archive dataset;
their URLs and hashes stay in the manifest. Edit THIRD_PARTY_HOSTS when new secondary sources are added.

Some official pages embed live access tokens in their scripts (for example a commenting service's
administrator token). The local archive keeps the exact copy; in the published copy each unexpired token is
replaced with REDACTED-ACCESS-TOKEN, and the manifest records both hashes (`sha256` = original,
`published_sha256` = published file). --squash-archive rewrites the archive dataset's history into one commit,
so that earlier revisions holding a token are no longer reachable.

Needs: huggingface_hub and pyarrow (pip install huggingface_hub pyarrow), and `hf auth login`.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import validate  # noqa: E402

ROOT = build.ROOT
AUTHORS = [("Riegler", "Michael"), ("Gautam", "Sushant")]
AFFILIATION = "Simula"
PRETTY_NAME = "Every AI Policy Ever"

# Hosts of secondary copies that are commentary or press rather than official publications.
THIRD_PARTY_HOSTS = {
    "www.transparencycoalition.ai", "www.chinalawtranslate.com", "cset.georgetown.edu", "asociace.ai",
    "basham.com.mx", "naswnv.socialworkers.org", "www.skadden.com", "www.tilleke.com", "www.morogluarseven.com",
    "www.nixonpeabody.com", "www.vietnamplus.vn", "www.ultimahora.com", "www.bta.bg", "gna.org.gh", "qanoon.om",
}


def host_of(f):
    return (urllib.parse.urlsplit(f.get("final_url") or f.get("url") or "").hostname or "").lower()


def is_third_party(f):
    return host_of(f) in THIRD_PARTY_HOSTS


JWT_RE = re.compile(rb"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
PLACEHOLDER = b"REDACTED-ACCESS-TOKEN"
TEXT_SUFFIXES = {".html", ".htm", ".txt", ".json", ".xml", ".js"}


def live_tokens(data, now=None):
    """JWTs in a file that are still valid: unexpired, or without an expiry. Expired tokens are left alone."""
    now = now or dt.datetime.now(dt.timezone.utc).timestamp()
    found = {}
    for m in JWT_RE.finditer(data):
        tok = m.group(0)
        try:
            part = tok.split(b".")[1]
            payload = json.loads(base64.urlsafe_b64decode(part + b"=" * (-len(part) % 4)))
        except Exception:
            continue  # looks like a JWT but is not one
        exp = payload.get("exp") if isinstance(payload, dict) else None
        if isinstance(exp, (int, float)) and exp < now:
            continue
        found[tok] = payload if isinstance(payload, dict) else {}
    return found


def redaction_plan(files):
    """path -> (published bytes, note) for stored text files that carry live tokens."""
    plan = {}
    for f in files:
        if not f["in_archive_dataset"] or Path(f["path"]).suffix.lower() not in TEXT_SUFFIXES:
            continue
        data = (ROOT / f["path"]).read_bytes()
        toks = live_tokens(data)
        if not toks:
            continue
        new = data
        for tok in toks:
            new = new.replace(tok, PLACEHOLDER)
        issuers = sorted({str(p.get("iss") or "unknown issuer") for p in toks.values()})
        note = ("%d access token(s) embedded by the source page (issued by %s) replaced with %s; "
                "the rest of the file is unchanged" % (len(toks), ", ".join(issuers), PLACEHOLDER.decode()))
        plan[f["path"]] = (new, note)
    return plan


# ----------------------------------------------------------------------------- tables

def tables(db, archive_repo_url):
    R = db["records"]
    records, topics, related, files = [], [], [], []
    for r in R:
        flat = build.flat(r)
        flat["safety_topics"] = list(r.get("safety_topics") or [])
        flat["related_ids"] = [x["id"] for x in (r.get("related") or []) if x.get("id")]
        flat.pop("local_files", None)
        flat.pop("local_sha256", None)
        records.append(flat)
        topics += [{"record_id": r["id"], "topic": t} for t in r.get("safety_topics") or []]
        related += [{"record_id": r["id"], "related_id": x["id"]} for x in r.get("related") or [] if x.get("id")]
        for f in (r.get("local_copy") or {}).get("files") or []:
            published = bool(f.get("path")) and (ROOT / f["path"]).is_file() and not is_third_party(f)
            files.append({
                "record_id": r["id"], "role": f.get("label") or f.get("role"), "path": f.get("path"),
                "url": f.get("url"), "final_url": f.get("final_url"), "host": host_of(f),
                "http_status": f.get("http_status"), "content_type": f.get("content_type"), "bytes": f.get("bytes"),
                "sha256": f.get("sha256"), "retrieved_at": f.get("retrieved_at"), "last_checked": f.get("last_checked"),
                "method": f.get("method"), "stale": bool(f.get("stale")), "integrity": f.get("integrity"),
                "in_archive_dataset": published,
                "archive_url": "%s/blob/main/%s" % (archive_repo_url, f["path"]) if published else None,
                "redacted": False, "published_sha256": f.get("sha256") if published else None, "redaction_note": None,
            })
    plan = redaction_plan(files)
    for row in files:
        if row["path"] in plan:
            data, note = plan[row["path"]]
            row.update({"redacted": True, "published_sha256": hashlib.sha256(data).hexdigest(), "redaction_note": note})
    return records, topics, related, files, plan


def write_parquet(rows, path, schema):
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression="zstd")


def schemas():
    import pyarrow as pa
    s, i, b = pa.string(), pa.int64(), pa.bool_()
    rec_fields = []
    for c in build.CSV_COLS:
        if c in ("local_files", "local_sha256"):
            continue
        rec_fields.append(pa.field(c, pa.list_(s) if c in ("safety_topics", "related_ids") else s))
    return {
        "records": pa.schema(rec_fields),
        "topics": pa.schema([("record_id", s), ("topic", s)]),
        "related": pa.schema([("record_id", s), ("related_id", s)]),
        "source_files": pa.schema([("record_id", s), ("role", s), ("path", s), ("url", s), ("final_url", s), ("host", s),
                                   ("http_status", i), ("content_type", s), ("bytes", i), ("sha256", s),
                                   ("retrieved_at", s), ("last_checked", s), ("method", s), ("stale", b),
                                   ("integrity", s), ("in_archive_dataset", b), ("archive_url", s),
                                   ("redacted", b), ("published_sha256", s), ("redaction_note", s)]),
    }


# ----------------------------------------------------------------------------- cards

def stats(db, files):
    R = db["records"]
    lv = Counter(r["verification"]["level"] for r in R)
    force = Counter(r["legal_force"] for r in R)
    countries = {r["country"] for r in R if r["jurisdiction_level"] in ("National", "Sub-national")}
    states = {r["jurisdiction"] for r in R if r["jurisdiction_level"] == "Sub-national" and r["country"] == "United States"}
    intl = sum(1 for r in R if r["jurisdiction_level"] in ("International", "Supranational"))
    pub = [f for f in files if f["in_archive_dataset"]]
    return {
        "n": len(R), "A": lv["A"], "B": lv["B"], "C": lv["C"], "binding": force["Binding"],
        "nonbinding": force["Non-binding"], "proposed": force["Proposed"], "countries": len(countries),
        "states": len(states), "intl": intl, "files": len(files), "pub_files": len(pub),
        "pub_mb": sum(f["bytes"] or 0 for f in pub) / 1e6, "excluded": len(files) - len(pub),
        "redacted": sum(1 for f in files if f.get("redacted")),
        "with_copy": sum(1 for r in R if (r.get("local_copy") or {}).get("status") == "archived"),
        "years": "%s to %s" % (min(r["date_published"][:4] for r in R if r.get("date_published")),
                               max(r["date_published"][:4] for r in R if r.get("date_published"))),
    }


def bibtex(meta, repo_url):
    key = "riegler_gautam_%s_every_ai_policy_ever" % meta.get("snapshot_date", "")[:4]
    authors = " and ".join("%s, %s" % a for a in AUTHORS)
    return ("@dataset{%s,\n  title     = {%s: a register of official AI safety and AI regulation instruments},\n"
            "  author    = {%s},\n  year      = {%s},\n  version   = {%s},\n  publisher = {Hugging Face},\n"
            "  url       = {%s},\n  note      = {AI-assisted extraction, snapshot %s}\n}") % (
        key, PRETTY_NAME, authors, meta.get("snapshot_date", "")[:4], meta.get("version"), repo_url,
        meta.get("snapshot_date"))


def dataset_card(db, st, ns, name, github_url):
    meta = db["meta"]
    repo_url = "https://huggingface.co/datasets/%s/%s" % (ns, name)
    archive_url = repo_url + "-archive"
    space_url = "https://huggingface.co/spaces/%s/%s" % (ns, name)
    authors = ", ".join("%s %s" % (f, l) for l, f in AUTHORS)
    yaml = """---
license: cc-by-4.0
language:
- en
pretty_name: %s
size_categories:
- n<1K
annotations_creators:
- machine-generated
source_datasets:
- original
tags:
- ai-policy
- ai-safety
- ai-regulation
- ai-governance
- law
- legislation
- government
configs:
- config_name: records
  data_files: data/records.parquet
  default: true
- config_name: topics
  data_files: data/topics.parquet
- config_name: related
  data_files: data/related.parquet
- config_name: source_files
  data_files: data/source_files.parquet
---
""" % PRETTY_NAME
    body = """
# {pretty}

A register of {n} official instruments on AI safety and AI regulation, from {countries} countries, including sub-national records for {states} US states, and from intergovernmental bodies such as the UN, the OECD, the G7, the G20 and the Council of Europe. It covers laws, implementing regulations, executive orders, government frameworks and guidelines, AI safety institute mandates, national strategies with safety content, treaties, declarations and pending bills, from {years}. Each record links to its official source and says how it was verified.

Despite the name, it is not every AI policy: scope is limited to official instruments on AI safety and regulation, and the coverage section below lists what is still missing.

- **Browse it:** [{pretty} on Spaces]({space}), with search, filters, a chart, record pages and citations.
- **Source documents:** [{ns}/{name}-archive]({archive}), the stored copies of the official sources with SHA-256 hashes. Open to anyone with a free Hugging Face account.
- **Snapshot:** {snapshot}, data version {version}. Statuses are as of the snapshot.

## How it was made

The records are an **AI-based extraction**. AI agents researched each instrument, fetched its official page or document, confirmed the title, date and status there, and wrote the summary, the status notes, the topic tags and a verification level.

| | |
|---|---|
| Agent | Claude Code, Anthropic's agentic coding tool, with its web search and web fetch tools; research passes and quality checks ran as agents following `AGENTS.md` |
| Model | Claude Fable 5.1 (`claude-fable-5-1`), for every research pass and both quality checks |
| Other tools | a Python archiver that stores each source with its SHA-256 hash, headless Chromium for pages that need JavaScript, pypdf and Tesseract OCR for PDF text |
| Research dates | 11 and 12 October 2026, in twelve research passes and two quality checks; `meta.provenance` in `raw/records.json` logs them |
| Human review | Michael Riegler checked 50 randomly chosen records by hand and found no problems |

Agents are what made this register possible: {n} instruments from {countries} countries, each checked against its official source and stored with a hash, in two days. They also make it repeatable. The method is written down in `AGENTS.md`, complete enough for another agent to follow, so anyone can extend the register, re-verify it after laws change, or rerun the method with a different model and compare the results. Every record carries its evidence, so checking a record does not depend on trusting whoever wrote it. A rerun gives comparable records, not identical ones, because language models are not deterministic.

No human has reviewed every record. The hand check of 50 records rules out frequent errors, not occasional ones: with no problems in 50, the error rate is probably below about 6 percent. Two content quality checks, in which a second agent compared the records with their stored sources, are in `docs/`, with what was fixed and what is still open.

| Verification level | Meaning | Records |
|---|---|---:|
| A | The official page or document was fetched and confirmed the title, date and status | {A} |
| B | Another official page confirmed them (a gazette entry, a ministry release, an official translation, the OECD.AI entry) | {B} |
| C | No official page could be fetched; the record rests on at least two independent secondary sources and says CAUTION | {C} |

Check the level before citing a record, and re-check level C records against the original.

## Quick start

```python
from datasets import load_dataset

records = load_dataset("{ns}/{name}", "records", split="train")
binding = records.filter(lambda r: r["legal_force"] == "Binding")
```

```python
import pandas as pd

df = pd.read_parquet("hf://datasets/{ns}/{name}/data/records.parquet")
df.groupby(["region", "legal_force"]).size().unstack(fill_value=0)
```

## Contents

| Config | Rows | One row per |
|---|---:|---|
| `records` (default) | {n} | instrument |
| `topics` | {n_topics} | instrument and safety topic |
| `related` | {n_related} | link between two records |
| `source_files` | {files} | stored copy of a source, with URL, hash, retrieval time and a link into the archive dataset; `redacted` marks the few published copies in which a live access token embedded by the source site was replaced |

`raw/records.json` is the full nested source of truth, with the complete verification and local-copy history of each record. `raw/records.csv` and `raw/register.xlsx` hold the same records for spreadsheets.

### Fields of `records`

| Field | Meaning |
|---|---|
| `id` | Register ID: jurisdiction code plus sequence, e.g. `EU-03`, `US-CA-05` |
| `title`, `short_title`, `original_title` | Official title (official English title where one exists), common short name, title in the original language |
| `jurisdiction`, `country`, `jurisdiction_level`, `region` | Issuing country, bloc or body; International, Supranational, National or Sub-national; world region |
| `issuing_body` | The institution that adopted or issued the instrument |
| `instrument_type` | Law, regulation or implementing rule, executive order or decree, guidelines or framework, voluntary code, technical standard, institutional mandate, declaration, treaty, resolution, bill, strategy or action plan, report |
| `legal_force` | Binding, Non-binding or Proposed |
| `status` | In force, partially in force, adopted but not yet in force, published (non-binding), draft, superseded, revoked or lapsed |
| `date_published`, `date_in_force`, `date_last_updated` | ISO dates; `YYYY-MM` or `YYYY` when the source gives no exact day. `date_published` is the date of the act itself (adoption, signature or issue) |
| `official_identifier` | The citable number: law or decree number, gazette reference, bill number, UN symbol, CELEX |
| `official_url`, `secondary_url` | The official source and, where useful, a second authoritative source |
| `language` | Language(s) of the official text |
| `summary`, `notes` | What the instrument does, with its safety content; status details, phased dates and discrepancies between sources |
| `safety_topics` | List of topics from a fixed vocabulary of 17, e.g. `general-purpose / frontier AI`, `incident reporting`, `child safety` |
| `related_ids` | IDs of related records |
| `verification_level`, `verified_on`, `verification_method`, `verification_note`, `second_check` | How and when the record was checked, and what rests on secondary sources |
| `local_status`, `local_flag`, `local_last_attempt` | Whether the official source is stored in the archive dataset, and why not if it is not |

## Coverage

{binding} binding, {nonbinding} non-binding and {proposed} proposed instruments; {intl} records are international or EU instruments. Every G20 member and 25 of the 27 EU member states have at least one record. Belgium and Estonia had adopted no national AI Act implementing measure at the snapshot.

The "Method & coverage" page of the Space lists what is known to be missing: instruments not adopted yet, instruments reported by secondary sources but not confirmed on an official page, and the records with weaker evidence. A country's absence from the register does not mean it has no AI instruments.

## Limitations

- Extraction errors are possible. Dates can be misread, a status can lag behind an amendment, and a summary can over- or under-state an instrument. Non-English documents were read as machine-extracted text and summarised in English.
- Statuses change. The register is a snapshot; it does not follow amendments after {snapshot}.
- For {nocopy} records the official source is either not stored or stored in a form that needs review, such as a bot-check page, mostly because the official site blocks automated downloads. Their `local_flag` says why.
- Nothing here is legal advice.

## License

The records, summaries and notes are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Titles, dates and identifiers of official instruments are facts. The stored source documents in the archive dataset remain under their publishers' terms.

## Citation

```bibtex
{bibtex}
```

Authors: {authors} ({affiliation}). Please say in your own text that the register is an AI-assisted extraction, and name the verification level of the records you rely on.

## Corrections and updates

Open a discussion on this dataset naming the record ID and the official source that contradicts it. Updates follow the method in `AGENTS.md`; the code and the web app are on [GitHub]({github}).
""".format(pretty=PRETTY_NAME, space=space_url, archive=archive_url, ns=ns, name=name,
           snapshot=meta.get("snapshot_date"), version=meta.get("version"), github=github_url,
           bibtex=bibtex(meta, repo_url), authors=authors, affiliation=AFFILIATION,
           nocopy=st["n"] - st["with_copy"], **st)
    return yaml + body


def archive_card(st, ns, name):
    main = "https://huggingface.co/datasets/%s/%s" % (ns, name)
    yaml = """---
license: other
license_name: publishers-terms
license_link: LICENSE.md
pretty_name: %s (source documents)
tags:
- ai-policy
- legislation
- government
extra_gated_heading: Access the stored source documents
extra_gated_prompt: >-
  These files are copies of official publications by governments, legislatures and intergovernmental bodies,
  stored so that each record of the register can be traced to the exact document it was based on. Each file
  remains subject to its publisher's terms. Access needs a Hugging Face account so that automated crawlers do
  not harvest the files; requests are approved automatically.
extra_gated_fields:
  Affiliation: text
  Intended use: text
  I will use the documents for research or verification and respect each publisher's terms: checkbox
extra_gated_button_content: Access the documents
---
""" % PRETTY_NAME
    body = """
# {pretty}: source documents

Stored copies of the official sources behind the records of [{ns}/{name}]({main}): {pub_files} files, about {pub_mb:.0f} MB, mostly PDFs and HTML pages of laws, decrees, gazette entries, guidelines and declarations.

Each file sits at `archive/<record ID>/<retrieval date>/`, next to a `SHA256SUMS` file:

```bash
cd archive/EU-03/2026-10-11 && sha256sum -c SHA256SUMS
```

The `source_files` table of the main dataset lists every stored file with its original URL, retrieval time, HTTP status and hash, and links each file here.

## What is not included

{excluded} copies of third-party pages that served as secondary sources (law-firm alerts, newspaper articles, NGO and think-tank pages) are not published here, because they are not official publications. Their URLs and hashes are in `source_files`, marked `in_archive_dataset = false`.

Some stored files are bot-check pages or empty JavaScript shells that an official site returned instead of the document; the record's `local_flag` in the main dataset says so.

## Redacted access tokens

{redacted} stored page(s) carried live access tokens that the source site embeds in its own scripts, such as a commenting service's login token. In the published copy each such token is replaced with `REDACTED-ACCESS-TOKEN`; nothing else in the file changed. `REDACTIONS.md` lists the files with their original and published hashes, and `SHA256SUMS` lists the published files. Expired tokens are left as they were.

## Terms

The documents remain under their publishers' terms (see `LICENSE.md`). If you hold rights in a file and want it removed, open a discussion on this dataset naming the path.
""".format(pretty=PRETTY_NAME, ns=ns, name=name, main=main, **st)
    lic = """# Terms for the stored source documents

The files in `archive/` are copies of documents published by governments, legislatures, courts, regulators and intergovernmental organisations. They are stored for research and to verify the records of the register. Copyright and reuse terms are those of each publisher; many official texts are in the public domain or under open government licences, and some are not. The register's authors claim no rights in them.

The register's own records, summaries and notes are licensed separately under CC BY 4.0 in the main dataset.
"""
    return yaml + body, lic


def space_card(ns, name):
    return """---
title: Every AI Policy Ever
emoji: 📜
colorFrom: blue
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: cc-by-4.0
short_description: Searchable register of official AI safety rules
datasets:
- {ns}/{name}
- {ns}/{name}-archive
---

# Every AI Policy Ever

A searchable register of official instruments on AI safety and AI regulation: laws, executive orders, frameworks, AI safety institute mandates, declarations and bills from governments and intergovernmental bodies. Each record links to its official source, says how it was verified, and has a ready-made citation.

The records are an AI-based extraction, made by AI agents in Claude Code with the model Claude Fable 5.1 and spot-checked by hand; the [dataset card](https://huggingface.co/datasets/{ns}/{name}) explains the method, why it is repeatable, and its limits. The data can be downloaded from the [dataset](https://huggingface.co/datasets/{ns}/{name}), and the stored source documents from the [archive dataset](https://huggingface.co/datasets/{ns}/{name}-archive).
""".format(ns=ns, name=name)


# ----------------------------------------------------------------------------- build

def build_all(out, ns, name, github_url):
    db = build.normalise(build.load())
    errors, _ = validate.run(db, quiet=True)
    if errors:
        raise SystemExit("records.json has %d validation error(s); run tools/validate.py" % len(errors))
    repo_url = "https://huggingface.co/datasets/%s/%s" % (ns, name)
    records, topics, related, files, plan = tables(db, repo_url + "-archive")
    st = stats(db, files)
    st["n_topics"], st["n_related"] = len(topics), len(related)
    if out.exists():
        shutil.rmtree(out)
    ds, ar, sp = out / "dataset", out / "archive", out / "space"

    # dataset
    (ds / "data").mkdir(parents=True)
    sch = schemas()
    write_parquet(records, ds / "data" / "records.parquet", sch["records"])
    write_parquet(topics, ds / "data" / "topics.parquet", sch["topics"])
    write_parquet(related, ds / "data" / "related.parquet", sch["related"])
    write_parquet(files, ds / "data" / "source_files.parquet", sch["source_files"])
    (ds / "raw").mkdir()
    for f in ("records.json", "records.csv", "register.xlsx"):
        if (ROOT / "data" / f).is_file():
            shutil.copy2(ROOT / "data" / f, ds / "raw" / f)
    shutil.copy2(ROOT / "AGENTS.md", ds / "AGENTS.md")
    if (ROOT / "docs").is_dir():
        shutil.copytree(ROOT / "docs", ds / "docs")
    (ds / "README.md").write_text(dataset_card(db, st, ns, name, github_url), encoding="utf-8")

    # archive: official copies only, with SHA256SUMS rewritten to list what is published
    by_dir = defaultdict(list)
    for f in files:
        if f["in_archive_dataset"]:
            src = ROOT / f["path"]
            dst = ar / f["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if f["path"] in plan:
                dst.write_bytes(plan[f["path"]][0])  # a new file, so the local exact copy is never touched
            else:
                try:
                    dst.hardlink_to(src)
                except (OSError, AttributeError):
                    shutil.copy2(src, dst)
            by_dir[dst.parent].append((f["published_sha256"], dst.name))
    for folder, entries in by_dir.items():
        lines = sorted(set("%s  %s" % e for e in entries), key=lambda l: l.split("  ", 1)[1])
        (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    card, lic = archive_card(st, ns, name)
    if plan:
        rows = ["| File | Original SHA-256 | Published SHA-256 | What was replaced |", "|---|---|---|---|"]
        for f in files:
            if f["redacted"]:
                rows.append("| `%s` | `%s` | `%s` | %s |" % (f["path"], f["sha256"], f["published_sha256"], f["redaction_note"]))
        (ar / "REDACTIONS.md").write_text("# Redacted access tokens\n\nThese stored pages carried live access tokens that the source site embeds in its own scripts. "
                                         "In the published copy each token is replaced with `%s`; nothing else in the file changed. "
                                         "The original hash identifies the exact page as it was served.\n\n%s\n"
                                         % (PLACEHOLDER.decode(), "\n".join(rows)), encoding="utf-8")
    (ar / "README.md").write_text(card, encoding="utf-8")
    (ar / "LICENSE.md").write_text(lic, encoding="utf-8")

    # space
    (sp / "assets").mkdir(parents=True)
    (sp / "data").mkdir()
    shutil.copy2(ROOT / "index.html", sp / "index.html")
    for f in (ROOT / "assets").iterdir():
        if f.is_file() and f.name != "site-config.js" and " 2." not in f.name:  # skip macOS conflict copies
            shutil.copy2(f, sp / "assets" / f.name)
    for f in ("records.js", "records.json", "records.csv"):
        shutil.copy2(ROOT / "data" / f, sp / "data" / f)
    excluded = sorted(f["path"] for f in files if f["path"] and not f["in_archive_dataset"])
    redacted = {f["path"]: f["redaction_note"] for f in files if f["redacted"]}
    config = {"archiveBase": repo_url + "-archive/blob/main/", "archiveExcluded": excluded, "archiveRedacted": redacted,
              "datasetUrl": repo_url, "archiveDatasetUrl": repo_url + "-archive"}
    (sp / "assets" / "site-config.js").write_text(
        "/* Written by tools/publish_hf.py for the Hugging Face Space. */\nwindow.SITE_CONFIG = %s;\n"
        % json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    (sp / "README.md").write_text(space_card(ns, name), encoding="utf-8")
    return st


def push(out, ns, name, private, only=("dataset", "archive", "space"), squash_archive=False):
    from huggingface_hub import HfApi
    api = HfApi()
    ds_id, ar_id, sp_id = "%s/%s" % (ns, name), "%s/%s-archive" % (ns, name), "%s/%s" % (ns, name)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    if "dataset" in only:
        api.create_repo(ds_id, repo_type="dataset", private=private, exist_ok=True)
        api.upload_folder(repo_id=ds_id, repo_type="dataset", folder_path=str(out / "dataset"),
                          commit_message="Publish register data (%s)" % stamp,
                          delete_patterns=["data/*", "raw/*", "docs/*"])
        print("uploaded", ds_id)
    if "archive" in only:
        api.create_repo(ar_id, repo_type="dataset", private=private, exist_ok=True)
        api.upload_folder(repo_id=ar_id, repo_type="dataset", folder_path=str(out / "archive"),
                          commit_message="Publish stored source documents (%s)" % stamp, delete_patterns=["archive/**"])
        api.update_repo_settings(ar_id, repo_type="dataset", gated="auto")
        print("uploaded", ar_id, "(gated, automatic approval)")
        if squash_archive:
            api.super_squash_history(repo_id=ar_id, repo_type="dataset",
                                     commit_message="Stored source documents (history squashed %s)" % stamp)
            print("squashed the history of", ar_id)
    if "space" in only:
        api.create_repo(sp_id, repo_type="space", space_sdk="static", private=private, exist_ok=True)
        api.upload_folder(repo_id=sp_id, repo_type="space", folder_path=str(out / "space"),
                          commit_message="Publish web app (%s)" % stamp, delete_patterns=["assets/*", "data/*"])
        print("uploaded", sp_id)
    return ds_id, ar_id, sp_id


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publish the register to Hugging Face.")
    ap.add_argument("--namespace", default="kelkalot")
    ap.add_argument("--name", default="every-ai-policy-ever")
    ap.add_argument("--github", default="https://github.com/kelkalot/ai-safety-policy-register")
    ap.add_argument("--out", default=str(ROOT / "dist" / "hf"))
    ap.add_argument("--push", action="store_true", help="upload to Hugging Face after building")
    ap.add_argument("--only", default="dataset,archive,space", help="comma-separated subset to upload: dataset, archive, space")
    ap.add_argument("--squash-archive", action="store_true", help="rewrite the archive dataset's history into one commit")
    ap.add_argument("--private", action="store_true", help="create the repos as private (existing repos keep their visibility)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    st = build_all(out, args.namespace, args.name, args.github)
    print("Built %s: %d records; archive %d of %d stored files (%.0f MB), %d third-party copies left out, "
          "%d with access tokens replaced." % (out, st["n"], st["pub_files"], st["files"], st["pub_mb"], st["excluded"], st["redacted"]))
    if args.push:
        push(out, args.namespace, args.name, args.private, [x.strip() for x in args.only.split(",") if x.strip()],
             squash_archive=args.squash_archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
