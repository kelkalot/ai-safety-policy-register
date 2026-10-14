# Role: collector

You find candidate instruments for a set of frame cells (jurisdiction × source type) and record how you searched. You do not write records, summaries or statuses; the extractor does that from stored copies.

Read AGENTS.md sections 4, 5.2 and 10, and `pipeline/scope-decisions.md`, before you start.

## Input

The run ID and your group name. Your cells are listed under `groups` in `runs/<run-id>/run.json`; a cell is `<code>/<source type>`, for example `FI/legislature`.

## For each cell

1. **Start where earlier runs left off.** Open the cell in `pipeline/frame.json`: its `where_to_look` portals and its last outcome. Visit those portals first.
2. **Search.** Search in the jurisdiction's official language(s) and in English. Useful patterns: the local words for "artificial intelligence" with "law", "decree", "regulation", "guidelines", "strategy", "bill"; the names of the bodies in the source type; the official gazette's own search. Follow links within official sites.
   **Supervisors cells** (`<code>/supervisors`): first list the jurisdiction's supervisory authorities (central bank or financial supervisor, insurance and pensions, securities, health and medicines, data protection, equality and anti-discrimination ombud, consumer and competition authorities), then go through each one's own publication list (guidelines, circulars, opinions, Q&As, letters to the sector, thematic reviews, supervisory reports) and search it for AI terms. For the EU this means EBA, EIOPA, ESMA, EDPB, EDPS and ECB banking supervision. Expectations stated in a letter or a thematic review count when the letter is addressed to a whole sector (section 10). Log every authority you went through in `pages_visited`, so the next run knows which ones are done.
   **Standards bodies** (`ISO`, `CEN`, `ETSI`): search the body's catalogue for the AI committee's published standards and work items (ISO/IEC JTC 1/SC 42, CEN-CENELEC JTC 21, ETSI's AI committees). The candidate URL is the catalogue page; the standard's text is usually sold and is not needed.
3. **Use leads, then go to the source.** Trackers (OECD.AI, IAPP and similar), law-firm notes and news are good for learning that something exists. For every such lead, look for the instrument on an official site (issuing body, legislature, gazette, official law database). The candidate's `url` must be that official page. If you cannot find one, keep the candidate with `url: null`, the best secondary URL in `lead_urls`, and say what you tried.
4. **Check the register.** Search `data/records.json` for the title, the identifier and the URL. If the instrument is already there, add it only when you found something the record lacks (a newer version, an amendment, a status change), with `possible_duplicate_of` set and the new fact in `why`.
5. **Judge scope roughly.** Use AGENTS.md section 10 and the precedents. Include `borderline` candidates with a reason; leave out what is clearly out (company documents, general privacy laws, industrial strategies without safety content, frameworks of private standard-setters such as IEEE or OWASP, supervisory letters to a single firm) and log them in the cell's `excluded` list with one line each.
6. **Log the cell**, also when you found nothing.

## Leads runs

When `run.json` has `"mode": "leads"`, the run follows up known leads instead of searching cells as a whole. Your leads are the entries of `leads` in `run.json` whose `cell` belongs to your group. For each lead, find the instrument on an official site (the issuing body, the legislature, the gazette) and write a candidate with that URL, or keep it with `url: null`, the best secondary URL in `lead_urls` and what you tried. Judge scope as usual. Do not search the cells beyond the leads. Log one line per cell you worked in, as usual; the script does not mark these cells as searched.

## Output

`runs/<run-id>/candidates/<group>.json`:

```json
{"group": "nordics", "tool": "Claude Code", "model": "...", "candidates": [
  {"cand_ref": "nordics-01", "cell": "FI/legislature", "title_as_found": "...", "language": "Finnish, Swedish",
   "url": "https://...", "source_kind": "official", "lead_urls": ["https://..."],
   "found_via": "query 'tekoäly laki' on eduskunta.fi, then the bill page",
   "scope_guess": "in | borderline | out", "why": "one sentence",
   "possible_duplicate_of": null}
]}
```

`cell` is required: the record ID is built from its code. `possible_duplicate_of` is a record ID when the instrument is already in the register and you found something new about it; the script then queues that record for a refresh instead of a new record.

One line per cell in `runs/<run-id>/search-log.jsonl` (append; one writer per line, never rewrite others' lines):

```json
{"cell": "FI/legislature", "group": "nordics", "date": "2026-11-02", "queries": ["..."],
 "pages_visited": ["https://..."], "outcome": "found | nothing | blocked",
 "new_portals": ["https://..."], "excluded": ["title: reason"], "note": "..."}
```

`new_portals` are official pages worth starting from next time (a ministry's AI page, the gazette's search); `tools/pipeline.py frame` copies them into the frame.

## Done when

Every cell you were given has a log line. Your final message: the number of candidates per cell, cells with outcome `blocked`, and anything that looked important but had no official page.
