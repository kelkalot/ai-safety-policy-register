#!/usr/bin/env python3
"""Build one zip file that holds the whole register, ready to share.

    python3 tools/package.py                 # -> dist/every-ai-policy-ever_<snapshot>.zip
    python3 tools/package.py --no-archive    # app and data only (a few MB), without the source documents
    python3 tools/package.py --out /some/folder

The zip unpacks to a single folder containing the app (index.html, assets/), the data in every
form (records.json, records.csv, register.sqlite, register.xlsx), the local copies of every
source with their SHA256SUMS, the tools and the analysis example. Two files are added at the
top: PACKAGE.txt (what is inside and how to open it) and MANIFEST-SHA256.txt (a hash of every
file, so the recipient can check the package with `shasum -a 256 -c MANIFEST-SHA256.txt`).

The data is validated and rebuilt first, so the package always matches records.json.
Standard library only.
"""
import argparse
import datetime as dt
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import validate  # noqa: E402

ROOT = build.ROOT
TOP_FILES = ["index.html", "README.md", "docker-compose.yml"]
DIRS = ["assets", "data", "tools", "deploy", "examples"]
SKIP_NAMES = {".DS_Store", "__pycache__", ".htpasswd", "cron.log", "dist", ".git"}
SKIP_SUFFIXES = {".tmp", ".pyc"}
STORED = {".pdf", ".png", ".jpg", ".zip", ".docx", ".xlsx"}  # already compressed


def iter_files(include_archive):
    for name in TOP_FILES:
        p = ROOT / name
        if p.is_file():
            yield p
    for d in DIRS + (["archive"] if include_archive else []):
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_NAMES) and p.suffix not in SKIP_SUFFIXES:
                yield p


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def package_text(db, files, total, include_archive, folder):
    R = db["records"]; meta = db.get("meta") or {}
    counts = {}
    for r in R:
        s = (r.get("local_copy") or {}).get("status", "not-attempted"); counts[s] = counts.get(s, 0) + 1
    lv = {}
    for r in R:
        l = (r.get("verification") or {}).get("level"); lv[l] = lv.get(l, 0) + 1
    n_files = sum(1 for p in files if p.relative_to(ROOT).parts[0] == "archive")
    lines = [
        "%s - complete package" % meta.get("name", "Every AI Policy Ever"),
        "=" * 72,
        "Snapshot %s, version %s, %d records. Packaged %s." % (
            meta.get("snapshot_date"), meta.get("version"), len(R), dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        "Verification: %d records confirmed on the official page (A), %d on an alternative official page (B), %d not confirmed (C)." % (
            lv.get("A", 0), lv.get("B", 0), lv.get("C", 0)),
        "Local copies: " + ", ".join("%s %d" % (k, counts[k]) for k in build.LOCAL_STATUSES if k in counts) + ".",
        "Contents: %d files, %.1f MB unpacked%s." % (len(files) + 2, total / 1048576,
                                                       "" if include_archive else " (source documents left out: --no-archive)"),
        "",
        "WHAT IS IN THE FOLDER",
        "  index.html, assets/      the register as a web page; double-click index.html to browse it offline",
        "  data/records.json        the database itself (single source of truth)",
        "  data/records.csv         one row per record, for spreadsheets",
        "  data/register.xlsx       Excel workbook: Records, Topics, Related, Local copies, Needs attention, About",
        "  data/register.sqlite     SQL database: records, topics, related, archive_files, archive_attempts, meta",
    ]
    if include_archive:
        lines += [
            "  archive/<ID>/<date>/     local copies of every source (%d files): the official page or PDF, the legal text" % n_files,
            "                           where linked, and the secondary source; SHA256SUMS in each folder",
            "  archive/manifest.json    every record's local-copy status, files and hashes",
            "  archive/needs-attention.txt  the records that still need a human decision, with the reason",
        ]
    lines += [
        "  tools/                   archive.py (download and hash sources), build.py (regenerate data files),",
        "                           validate.py (check records.json), export_xlsx.py, package.py (this packager)",
        "  examples/                analysis.py and its output: an example analysis run from register.sqlite",
        "  README.md                full documentation: viewing, archiving, updating, serving, scope and caveats",
        "  MANIFEST-SHA256.txt      SHA-256 of every file in this package",
        "",
        "HOW TO USE IT",
        "  Browse:   open index.html in a browser (no server or internet needed), or run",
        "            python3 -m http.server 8000  in this folder and open http://localhost:8000",
        "  Excel:    open data/register.xlsx; each sheet has filters, the About sheet explains every column",
        "  SQL:      sqlite3 data/register.sqlite \"SELECT id, short_title, status FROM records WHERE legal_force='Binding';\"",
        "  Python:   python3 examples/analysis.py   (writes examples/output/analysis.md)",
        "  Verify:   shasum -a 256 -c MANIFEST-SHA256.txt      (Linux: sha256sum -c MANIFEST-SHA256.txt)",
        "  Update:   python3 tools/archive.py  re-downloads changed sources; python3 tools/build.py after editing records.json",
        "",
        "PLEASE NOTE",
        "  Records with verification level C were not confirmed on an official page; re-check them before citing.",
        "  Dates may be partial (YYYY-MM or YYYY) when the source gives no exact day.",
        "  The archive/ folder holds copies of other organisations' documents. Check reuse terms before publishing them.",
        "  Nothing in this package phones home: the web page makes no requests to other sites.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zip the whole register into one shareable file.")
    ap.add_argument("--out", default=str(ROOT / "dist"), help="folder for the zip (default: dist/)")
    ap.add_argument("--no-archive", action="store_true", help="leave out archive/ (source documents)")
    ap.add_argument("--no-rebuild", action="store_true", help="do not validate and rebuild the data files first")
    args = ap.parse_args(argv)

    db = build.normalise(build.load())
    if not args.no_rebuild:
        errors, _ = validate.run(db, quiet=True)
        if errors:
            for _, rid, msg in errors:
                print("ERROR    %-10s %s" % (rid, msg))
            print("Not packaging: fix the %d error(s) in data/records.json first." % len(errors)); return 1
        build.save(db)
    meta = db.get("meta") or {}
    include_archive = not args.no_archive
    folder = "every-ai-policy-ever_%s%s" % (meta.get("snapshot_date", "snapshot"), "" if include_archive else "_data-only")
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / (folder + ".zip")

    files = list(iter_files(include_archive))
    total = sum(p.stat().st_size for p in files)
    print("Packaging %d files (%.1f MB) into %s ..." % (len(files), total / 1048576, zip_path.relative_to(ROOT) if zip_path.is_relative_to(ROOT) else zip_path))
    manifest = []
    tmp = zip_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in files:
            rel = p.relative_to(ROOT).as_posix()
            manifest.append("%s  %s" % (sha256_file(p), rel))
            zf.write(p, folder + "/" + rel,
                     compress_type=zipfile.ZIP_STORED if p.suffix.lower() in STORED else zipfile.ZIP_DEFLATED)
        text = package_text(db, files, total, include_archive, folder)
        zf.writestr(folder + "/PACKAGE.txt", text)
        zf.writestr(folder + "/MANIFEST-SHA256.txt", "\n".join(manifest) + "\n")
    tmp.replace(zip_path)
    digest = sha256_file(zip_path)
    (zip_path.with_suffix(".zip.sha256")).write_text("%s  %s\n" % (digest, zip_path.name), encoding="utf-8")
    print("Wrote %s (%.1f MB)" % (zip_path, zip_path.stat().st_size / 1048576))
    print("SHA-256 %s (also in %s)" % (digest, zip_path.with_suffix(".zip.sha256").name))
    print("Unpacks to the folder %s/ with PACKAGE.txt and MANIFEST-SHA256.txt at its top." % folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
