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

Needs: huggingface_hub and pyarrow (pip install huggingface_hub pyarrow), and `hf auth login`.
"""
import argparse
import datetime as dt
import hashlib
import json
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
            })
    return records, topics, related, files


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
                                   ("integrity", s), ("in_archive_dataset", b), ("archive_url", s)]),
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

The records are an **AI-based extraction**. AI agents (Claude, by Anthropic) researched each instrument, fetched its official page or document, confirmed the title, date and status there, and wrote the summary, the status notes, the topic tags and a verification level. Using agents is what made a register of this breadth possible in a short time; it also means errors are possible, and no human has reviewed every record.

The method is written down in `AGENTS.md` in this repository, so that anyone can extend or re-check the register with another agent pass. Two content quality checks, in which a second agent compared the records with their stored sources, are in `docs/`, with what was fixed and what is still open. Every stored source carries its retrieval time and SHA-256 hash, so a record can be traced to the exact document it was based on.

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
| `source_files` | {files} | stored copy of a source, with URL, hash, retrieval time and a link into the archive dataset |

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

The records are an AI-based extraction; the [dataset card](https://huggingface.co/datasets/{ns}/{name}) explains the method and its limits. The data can be downloaded from the [dataset](https://huggingface.co/datasets/{ns}/{name}), and the stored source documents from the [archive dataset](https://huggingface.co/datasets/{ns}/{name}-archive).
""".format(ns=ns, name=name)


# ----------------------------------------------------------------------------- build

def build_all(out, ns, name, github_url):
    db = build.normalise(build.load())
    errors, _ = validate.run(db, quiet=True)
    if errors:
        raise SystemExit("records.json has %d validation error(s); run tools/validate.py" % len(errors))
    repo_url = "https://huggingface.co/datasets/%s/%s" % (ns, name)
    records, topics, related, files = tables(db, repo_url + "-archive")
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
            try:
                dst.hardlink_to(src)
            except (OSError, AttributeError):
                shutil.copy2(src, dst)
            by_dir[dst.parent].append((f["sha256"], dst.name))
    for folder, entries in by_dir.items():
        lines = sorted(set("%s  %s" % e for e in entries), key=lambda l: l.split("  ", 1)[1])
        (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    card, lic = archive_card(st, ns, name)
    (ar / "README.md").write_text(card, encoding="utf-8")
    (ar / "LICENSE.md").write_text(lic, encoding="utf-8")

    # space
    (sp / "assets").mkdir(parents=True)
    (sp / "data").mkdir()
    shutil.copy2(ROOT / "index.html", sp / "index.html")
    for f in ("app.css", "app.js"):
        shutil.copy2(ROOT / "assets" / f, sp / "assets" / f)
    for f in ("records.js", "records.json", "records.csv"):
        shutil.copy2(ROOT / "data" / f, sp / "data" / f)
    excluded = sorted(f["path"] for f in files if f["path"] and not f["in_archive_dataset"])
    config = {"archiveBase": repo_url + "-archive/blob/main/", "archiveExcluded": excluded,
              "datasetUrl": repo_url, "archiveDatasetUrl": repo_url + "-archive"}
    (sp / "assets" / "site-config.js").write_text(
        "/* Written by tools/publish_hf.py for the Hugging Face Space. */\nwindow.SITE_CONFIG = %s;\n"
        % json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    (sp / "README.md").write_text(space_card(ns, name), encoding="utf-8")
    return st


def push(out, ns, name, private):
    from huggingface_hub import HfApi
    api = HfApi()
    ds_id, ar_id, sp_id = "%s/%s" % (ns, name), "%s/%s-archive" % (ns, name), "%s/%s" % (ns, name)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    api.create_repo(ds_id, repo_type="dataset", private=private, exist_ok=True)
    api.create_repo(ar_id, repo_type="dataset", private=private, exist_ok=True)
    api.create_repo(sp_id, repo_type="space", space_sdk="static", private=private, exist_ok=True)
    api.upload_folder(repo_id=ds_id, repo_type="dataset", folder_path=str(out / "dataset"),
                      commit_message="Publish register data (%s)" % stamp,
                      delete_patterns=["data/*", "raw/*", "docs/*"])
    print("uploaded", ds_id)
    api.upload_folder(repo_id=ar_id, repo_type="dataset", folder_path=str(out / "archive"),
                      commit_message="Publish stored source documents (%s)" % stamp, delete_patterns=["archive/**"])
    api.update_repo_settings(ar_id, repo_type="dataset", gated="auto")
    print("uploaded", ar_id, "(gated, automatic approval)")
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
    ap.add_argument("--private", action="store_true", help="create the repos as private (existing repos keep their visibility)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    st = build_all(out, args.namespace, args.name, args.github)
    print("Built %s: %d records; archive %d of %d stored files (%.0f MB), %d third-party copies left out."
          % (out, st["n"], st["pub_files"], st["files"], st["pub_mb"], st["excluded"]))
    if args.push:
        push(out, args.namespace, args.name, args.private)
    return 0


if __name__ == "__main__":
    sys.exit(main())
