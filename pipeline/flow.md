# How the pipeline fits together

These charts show what an agent session can do, what each run kicks off, and how the runs feed each other. Solid boxes exist today. Dashed boxes are planned and tracked in the issues named in them. AGENTS.md is the contract; when a chart and AGENTS.md disagree, AGENTS.md is right and the chart needs fixing.

## 1. Where a session starts

```mermaid
flowchart TD
    start(["New clone or new agent session"]) --> menu["python3 tools/pipeline.py menu<br/>what is ready now"]
    menu --> setup{"setup missing?<br/>no archive, pypdf, playwright"}
    setup -- yes --> fix["archive.py --browser, or the archive<br/>from Hugging Face; pip install"]
    fix --> menu
    setup -- no --> pick{"pick one item,<br/>one run per session"}
    pick --> dec["decisions<br/>intake, questions --apply"]
    pick --> ref["refresh run<br/>pipeline.py queue"]
    pick --> lead["leads run<br/>pipeline/leads.json"]
    pick --> disc["discover run<br/>frame cells due, one group of countries"]
    pick --> comp["compare run<br/>definitions.py queue"]
    menu -.-> people["for people only: open questions,<br/>hosts, human samples, documents to provide"]
    classDef human fill:#fff4e5,stroke:#b26b00
    class people human
```

Every run is created with `pipeline.py new`. It refuses a run larger than 120 frame cells or 40 records (15 for compare) unless a person adds `--large`. It writes the run's steps into `run.json` and prints them, and `pipeline.py status` ticks them off.

## 2. What a run kicks off

```mermaid
flowchart TD
    subgraph FIND["find and add: discover, refresh, recheck"]
        direction TB
        f1["collect<br/>collectors, discover only"] --> f2["dedupe<br/>script"]
        f2 --> f3["archive + textify<br/>scripts"]
        f3 --> f4["extract<br/>extractors"]
        f4 -- extra_urls --> f3
        f4 --> f5["evidence<br/>script"]
        f5 --> f6["blind sample + agreement<br/>fresh extractor, script"]
        f6 --> f7["check<br/>checker, fresh context"]
        f7 --> f8["assemble + merge + build<br/>scripts"]
        f8 --> f9["report, questions --sync, intake<br/>scripts"]
    end
    subgraph COMPARE["compare"]
        direction TB
        c1["textify<br/>script"] --> c2["extract + blind extract<br/>two extractors"]
        c2 --> c3["quote check + agreement<br/>scripts"]
        c3 --> c4["check<br/>checker, fresh context"]
        c4 --> c5["merge + build<br/>scripts"]
        c5 --> c6["report<br/>script"]
    end
    f8 --> rec[("data/records.json<br/>data/history.jsonl")]
    c5 --> defs[("data/definitions.json<br/>data/history.jsonl")]
```

Refresh and recheck runs start at "archive + textify": their candidates are the records. A compare run never changes a record, and a find-and-add run never writes `data/definitions.json`. Each run ends with one commit on `run/<run-id>`, which a person reviews and merges.

## 3. How the runs feed each other

```mermaid
flowchart TD
    rec[("records and their stored sources")]
    arch["weekly archiver<br/>archive.py"] -- "a source changed" --> rq
    rec -- "due: news, passed dates, level C, 180 days" --> rq["refresh queue<br/>pipeline.py queue"]
    rq --> FIND["refresh run"]
    FIND --> rec
    rec -- "new record, or its stored files changed" --> cq["comparison queue<br/>definitions.py queue"]
    cq --> COMP["compare run"]
    COMP --> defs[("definitions")]
    rec -. "source changed" .-> mark["definition marked<br/>source_changed"]
    mark --> cq
    FIND -- "open questions, samples, hosts" --> gh["GitHub issues"]
    COMP -- "held definitions" --> rep["run report"]
    gh -- "a maintainer comments decide: ..." --> apply["questions --apply, intake"]
    users["issue forms: suggest an instrument,<br/>provide a document"] --> gh
    apply -- "leads, refresh requests,<br/>provided documents" --> lq["leads and refresh requests"]
    lq --> rq
    lq --> leads["leads run / discover run"]
    leads --> rec
    classDef human fill:#fff4e5,stroke:#b26b00
    class gh,apply,users human
```

## 4. The crosswalk (issue #70)

```mermaid
flowchart LR
    d["layer 1: definitions<br/>compare runs, data/definitions.json"] --> r["layer 2: requirements<br/>duty, addressee, dates, quote<br/>#59 phase 2"]
    r --> m["layer 3: mapping<br/>control themes, similar requirements<br/>two mappings + human sample"]
    sup["supervisory model-risk instruments<br/>#30: SR 11-7, PRA SS1/23, EBA"] --> d
    classDef planned stroke-dasharray: 5 5
    class r,m,sup planned
```

The tracker at the top of issue #70 lists what is done, what is next and what is parked.
