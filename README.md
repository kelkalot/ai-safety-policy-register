# AI Safety Policy Register

A database of 214 official governmental and intergovernmental instruments on AI safety and AI regulation: laws, executive orders, safety frameworks, AI safety institute mandates, treaties and declarations. Research snapshot: 11 October 2026.

Every record links to its official source, says how and when it was verified, and can keep a **local copy** of its sources with a SHA-256 hash and a UTC timestamp. Anything that cannot be stored locally is **flagged on the record** with the reason.

Everything runs from this folder. The app makes no requests to other websites, and there is nothing to install to view it.

**The records are an AI-based extraction.** An AI agent researched and wrote them from the official pages it could fetch; no human has reviewed every record. `AGENTS.md` describes how the data was made, its limitations, and the method and commands for extending or re-checking it with another agent pass.

```
ai-safety-policy-register/
├── AGENTS.md               how the data was made, its limits, and the method for agent passes
├── index.html              the app
├── assets/                 app.css, app.js
├── data/
│   ├── records.json        the database (single source of truth)
│   ├── records.js          generated: what the app loads
│   ├── records.csv         generated: for spreadsheets
│   ├── register.sqlite     generated: for SQL queries
│   └── register.xlsx       generated: Excel workbook (when openpyxl is installed)
├── archive/                local copies of sources (filled by tools/archive.py)
├── tools/
│   ├── archive.py          downloads sources, hashes them, flags failures
│   ├── build.py            regenerates records.js / .csv / .sqlite / .xlsx from records.json
│   ├── validate.py         checks records.json before a build
│   ├── export_xlsx.py      writes the Excel workbook (used by build.py)
│   ├── merge.py            merges a research pass into records.json with checks
│   └── package.py          zips everything into one shareable file
├── examples/
│   └── analysis.py         example analysis run straight from register.sqlite
├── deploy/                 nginx.conf, Dockerfile
└── docker-compose.yml
```

## 1. View it

Pick whichever fits.

**Offline, on your own computer.** Double-click `index.html`. It opens in your browser with no server and no internet connection. Links to local copies open the files from the `archive/` folder.

**A quick local web server.**

```bash
cd ai-safety-policy-register
python3 -m http.server 8000
# open http://localhost:8000
```

**Docker (for a server).**

```bash
cd ai-safety-policy-register
docker compose up -d
# open http://<server>:8080
```

Set `REGISTER_PORT` to use another host port, for example `REGISTER_PORT=8090 docker compose up -d`. The folder is mounted read-only, so new data shows up on the next browser reload without restarting the container. To build an image that contains a frozen copy of the data and archive instead:

```bash
docker build -f deploy/Dockerfile -t ai-safety-policy-register .
docker run -d -p 8080:80 --name ai-safety-policy-register ai-safety-policy-register
```

**Any existing web server** (Apache, nginx, IIS, a university web space). Copy the folder and serve it as static files. If you use nginx, `deploy/nginx.conf` has the recommended settings (see section 5).

Search, filters and sort order are kept in the page URL, so a filtered view can be bookmarked or sent to a colleague ("Copy link to this view" next to the result count). A single record is addressed as `index.html#EU-03`.

## 2. Create the local copies

The package ships without the source documents. Run the archiver once on the machine that will host the register. It needs Python 3.8 or later and nothing else.

```bash
cd ai-safety-policy-register
python3 tools/archive.py
```

The archiver identifies itself as `AISafetyPolicyRegister-Archiver` in the User-Agent string and sends nothing about you. With the default politeness settings (one request every 2 seconds per site, 4 sites in parallel) a full run takes roughly 20 to 60 minutes.

For each record the archiver:

1. checks the site's `robots.txt`, then downloads the official URL;
2. if that is an HTML page, also downloads up to 2 PDFs it links to on the same official site, which is usually the legal text itself;
3. downloads the secondary URL as a backup;
4. saves each file under `archive/<ID>/<YYYY-MM-DD>/` and writes `SHA256SUMS` in that folder;
5. records the hash, UTC retrieval time, final URL after redirects, HTTP status, content type and server `Last-Modified` date in the record's `local_copy` block;
6. flags anything that did not work, then regenerates `records.js`, `records.csv` and `register.sqlite`;
7. rewrites `archive/needs-attention.txt`, the list of records that still need a human decision (see below).

It saves progress every 10 records, so an interrupted run (Ctrl+C) loses nothing.

### What the flags mean

| Status | Meaning |
|---|---|
| `archived` | The official source was stored. |
| `archived-review` | A copy is stored but needs a human look. The site may have returned a bot-check or a JavaScript-only page, or the page may no longer mention the document's title. A source that was stored before may now be gone (the old copy is kept), or a local file may have changed since download. |
| `partial` | The official source failed; only the secondary source was stored. |
| `failed` | Nothing could be stored. The flag gives the reason: HTTP error, timeout, `robots.txt` block, TLS certificate error, or file too large. |
| `no-url` | The record has no URL to archive. |
| `not-attempted` | The archiver has not run for this record yet. |

In the app, these appear as a badge on every row, as a "Local copy" filter, and in a "Local copy" section on each record, which lists the stored files with their hashes. In the data they are in `local_copy.status` and `local_copy.flag` (and `local_status` / `local_flag` in the CSV and SQLite files).

### The decision log

After every run, and after `--verify`, the archiver rewrites `archive/needs-attention.txt`. It lists every record that is not cleanly archived, grouped by problem: nothing downloaded, only the secondary source saved, saved but needs review, no URL, or a local file that has gone missing or changed. Each entry gives the record, its URLs, the exact reason, the files that were stored, and the folder to put a manual copy in.

The archiver never contacts anyone. Whether to save a document by hand, ask the site operator for a copy, or leave the record flagged is your decision, and this file is where you make it.

### Useful options

```bash
python3 tools/archive.py --status failed,partial,archived-review   # retry only the problem records
python3 tools/archive.py --only EU-01,US-07                        # specific records
python3 tools/archive.py --browser                                 # retry failed or JavaScript-only pages in headless Chromium
python3 tools/archive.py --verify                                  # re-hash every local file; flag missing or modified ones
python3 tools/archive.py --dry-run                                 # list what would be fetched
python3 tools/archive.py --help                                    # all options (delay, timeout, PDFs per page, ...)
```

`--browser` needs Playwright: `pip install playwright && playwright install chromium`. For pages that load their content with JavaScript, it saves the rendered page and a printed PDF of it.

Some government sites block all automated downloads. Those records stay flagged and listed in `archive/needs-attention.txt`, and their official links in the app still work in a normal browser. To fill the gap, you can save the document by hand into the record's dated folder and add it to `local_copy.files` in `data/records.json`. Then run `tools/build.py` and `tools/archive.py --verify`.

## 3. Keep it current

Re-running the archiver is safe:

- an unchanged file is not stored twice; its `last_checked` time is updated. HTML pages are compared by their visible text, so pages whose scripts, session tokens or incident IDs differ on every request do not pile up new snapshots;
- a bot-check page or an empty JavaScript shell never replaces a clean earlier copy; the earlier copy is kept and the record is flagged for review;
- a changed source is stored as a new snapshot, and the record is flagged "changed", with a link to the earlier version;
- a source that has disappeared keeps its last copy, and the record is flagged for review.

To check weekly and keep a dated history in git, add a crontab entry like this one (it runs Mondays at 03:00):

```cron
0 3 * * 1  cd /srv/ai-safety-policy-register && python3 tools/archive.py >> archive/cron.log 2>&1 && python3 tools/archive.py --verify >> archive/cron.log 2>&1; git add -A && git commit -qm "archive run $(date -u +\%F)"
```

To edit or add records, change `data/records.json`, then run `python3 tools/build.py`. The build first runs `tools/validate.py`, which checks required fields, the controlled vocabularies (instrument type, legal force, status, level, region, topics), ISO dates, related IDs and URLs. It stops on errors and summarises warnings; `python3 tools/validate.py --strict` lists every warning. A date may be shortened to `YYYY-MM` or `YYYY` when the source gives no exact day. New records start as `not-attempted` until the next archiver run.

## 4. Check the data independently

```bash
cd archive/EU-01/2026-10-12 && sha256sum -c SHA256SUMS        # hashes of the stored files
sqlite3 data/register.sqlite "SELECT id, short_title, local_status, local_flag FROM records WHERE local_status <> 'archived';"
sqlite3 data/register.sqlite "SELECT record_id, path, sha256, retrieved_at FROM archive_files WHERE record_id LIKE 'US-%';"
```

The SQLite file has the tables `records`, `topics`, `related`, `archive_files`, `archive_attempts` and `meta`.

A few stored PDFs are AES-encrypted by their publishers (some Japanese and Californian documents). `pypdf` needs the `cryptography` package to read them (`python3 -m pip install cryptography`); poppler's `pdftotext` reads them as well.

### Analysis without the app

The web page is only a viewer. `data/register.sqlite`, `data/records.csv` and `data/records.json` carry the same data and can be used directly in SQL, pandas, R or a spreadsheet; `archive/` holds the source documents for text analysis, with `archive_files` giving each file's path and hash. `examples/analysis.py` shows how: it answers seven questions with plain SQL (growth per year, binding share per region, topics and topic pairs, time from publication to entry into force, verification and archive coverage) and writes `examples/output/analysis.md` plus a chart if matplotlib is installed.

```bash
python3 examples/analysis.py
```

Two things to keep in mind: `date_published` can be a partial date (`YYYY-MM` or `YYYY`), so day-level calculations should require full dates, and the multi-valued CSV columns (`safety_topics`, `related_ids`, `local_files`, `local_sha256`) are joined with "; ", whereas the SQLite `topics` and `related` tables hold one row per value.

## 5. Notes for a server

- **Archived pages are untrusted content.** `deploy/nginx.conf` serves `archive/` with `Content-Security-Policy: sandbox`, so scripts inside saved pages never run on your site. If you use another web server, set the same header for `archive/`. The rest of the site gets a strict policy that blocks requests to other sites.
- **Internal access only.** Uncomment the `auth_basic` lines in `deploy/nginx.conf` and create a password file with `htpasswd -c deploy/.htpasswd <user>` (this works with `docker compose`). Alternatively, publish the container only on your internal network.
- **Public hosting.** The records, summaries and links are fine to publish. The `archive/` folder holds copies of other organisations' documents. Most government texts can be reused, but check reuse terms before serving copies publicly. To hold copies back, keep the archive local and add `location /archive/ { deny all; }` to the nginx config, or leave the folder out when you copy the site.
- **"403 Forbidden" from nginx** usually means the web server cannot read the files. Run `chmod -R a+rX .` in the register folder.
- **Size.** Expect a few hundred MB to about 2 GB for the full archive, mostly PDFs. GitHub Pages and similar hosts limit repository and file sizes, so an institutional server or object storage suits the archive better.

## 6. Scope and caveats

The scope, the verification levels (A, B, C), the records to re-check first and the known coverage gaps are explained in the app under **Method & coverage**. In short:

- 198 records were confirmed on the official page, 13 on an alternative official page, and 3 could not be confirmed on an official page. Re-check the last group before citing.
- Some jurisdictions are missing or thin, including the AI Act implementation laws of most EU member states, South Korea's enforcement decree, Saudi Arabia's generative-AI guidelines, South Africa, Egypt, Turkey, Mexico and Argentina. Six gap records were added on 11 October 2026 (DE-01, VN-02, UN-10, INT-16, AE-02, SA-01).
- Record status reflects the research snapshot of 11 October 2026. The archiver detects changes to the source pages, but it does not re-interpret legal status. Update `status` and the date fields in `records.json` when a law's status changes.

## 7. Share it as one file

```bash
python3 tools/package.py                # dist/ai-safety-policy-register_<snapshot>.zip, with all source documents
python3 tools/package.py --no-archive   # a few MB: app and data only
```

The git repository holds the code and the text data (`records.json`, `records.js`, `records.csv`); the source documents in `archive/` and the generated binaries (`register.sqlite`, `register.xlsx`) are not committed and travel in this package instead. The packager validates and rebuilds the data, then zips the app, the data in every form (JSON, CSV, SQLite, Excel), the local copies with their `SHA256SUMS`, the tools and the analysis example into one folder. Two files sit at its top: `PACKAGE.txt` explains what is inside and how to open it, and `MANIFEST-SHA256.txt` lists a hash for every file, so the recipient can run `shasum -a 256 -c MANIFEST-SHA256.txt` (Linux: `sha256sum -c`). A `.sha256` file next to the zip holds the hash of the zip itself. The full package is a few hundred MB, mostly PDFs; the `--no-archive` variant fits in an e-mail.

## 8. Excel workbook

`data/register.xlsx` is written by `tools/build.py` whenever the `openpyxl` package is installed (`python3 -m pip install openpyxl`; `python3 tools/export_xlsx.py` writes it on its own). It has six sheets: **About** (what the file is, a glossary of every column), **Records** (the 33 columns of `records.csv` with clickable URLs, filters and a frozen header), **Topics** and **Related** (one row per topic and per link, ready for pivot tables), **Local copies** (one row per stored file with hash and retrieval time) and **Needs attention** (the records that are not cleanly archived). It contains no formulas, so every viewer shows the same values; dates are ISO text because some are partial.

