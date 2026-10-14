# Role: coordinator

You run one pipeline run from start to finish. You plan, start the other roles, run the scripts and write the summary. You do not collect, extract or check yourself when a subagent can do it, because the point of the pipeline is that each role works from files, not from your memory of the run.

Read AGENTS.md first; it is the contract. If a script fails, stop at that step and tell the human what it reported. Do not imitate a script by hand.

## Arguments

`<type> <scope>`: `discover` with a scope such as "Nordic countries", "Sub-Saharan Africa" or "whatever is due"; `refresh` with no scope (the queue) or record IDs; `recheck` with a region. Translate the user's words into the scope selectors of AGENTS.md section 3: "Nordic countries" is `codes:DK,FI,IS,NO,SE`, "Sub-Saharan Africa" is `region:"Sub-Saharan Africa"`, "whatever is due" is `due`. Look codes up in `pipeline/frame.json`; never guess one. If a run ID is given instead, resume it: `python3 tools/pipeline.py status --run <run-id>` shows where it stopped.

## Steps

0. **Apply decisions.** `python3 tools/pipeline.py intake` applies the maintainers' decisions on suggestions and provided documents, and `python3 tools/pipeline.py questions --apply` those on open questions (AGENTS.md sections 7.7 and 7.8). Queued leads go into a leads run (`new --type discover --leads pipeline/leads.json`). Commit nothing yet; the changes go into the run's commit.
1. **Create the run.** `python3 tools/pipeline.py new --type <type> --scope "<scope>" --tool "<Claude Code or Codex>" --model <the model you run as>`. It prints the run ID on its last line. For a refresh run without a scope, it takes the top of `pipeline.py queue`. Before each stage, record who runs it: `python3 tools/pipeline.py stage --run <run-id> --stage collect|extract|blind|check --tool ... --model ...`.
2. **Collect** (discover only). `run.json` lists the groups of frame cells, about 10 jurisdictions each. Start one collector per group, as parallel subagents where your tool has them. Each collector gets the run ID and its group name and follows `pipeline/roles/collect.md`. Wait for all of them. Refresh and recheck runs skip steps 2 and 3.
3. **Deduplicate.** `python3 tools/pipeline.py dedupe --run <run-id>` merges the groups' candidates, drops duplicates within the run, numbers the rest `C001`, `C002`, ..., and records the searches in `pipeline/frame.json`. It warns about cells with no search-log line; send those back to their collector. Candidates that match an existing record are not extracted; they are listed in the report. If the collector noted something new about that record (an amendment, a new version, a status change), the script adds the record to the refresh queue instead.
4. **Archive.** `python3 tools/archive.py --run <run-id> --browser`, then `python3 tools/pipeline.py textify --run <run-id>`.
5. **Extract.** Start extractors in batches of about 8 candidates, each following `pipeline/roles/extract.md`. When extractions list `extra_urls`, run step 4 again for those candidates and send them back to an extractor once.
6. **Evidence script.** `python3 tools/pipeline.py evidence --run <run-id>`. Send extractions with missing or unmatched quotes back to an extractor once; after that they go to the checker as they are.
7. **Blind sample.** `python3 tools/pipeline.py sample --run <run-id>`. Start a fresh extractor for the sampled candidates with the instruction to write into `extractions-blind/` and not to open `extractions/`. Then `python3 tools/pipeline.py compare --run <run-id>`.
8. **Check.** Start the `checker` subagent (or ask the human to run the check skill in the other tool, if they asked for a cross-tool check; then stop and wait). Give it only the run ID and the candidate IDs, never a summary of what the extractors found.
9. **Assemble and merge.** `python3 tools/pipeline.py assemble --run <run-id>`, then `python3 tools/merge.py runs/<run-id>/pass.json --dry-run`. Fix nothing by hand: a problem the dry run reports goes back to the stage that caused it, or stays as `needs-human`. Then merge without `--dry-run` and run `python3 tools/build.py`.
10. **Report and commit.** `python3 tools/pipeline.py report --run <run-id>`, then `python3 tools/pipeline.py frame --report`, then `python3 tools/pipeline.py questions --sync`, which opens a GitHub issue for each new open question and closes the ones the run settled, and `python3 tools/pipeline.py intake`, which closes the suggestion issues the run included. Read the report; replace the comment at its top with a short paragraph on what a human should look at first (the script keeps it when the report is rewritten). Hosts listed under "Hosts to review" are for the human: never add a site to `pipeline/official-sites.json` yourself. Commit the run folder, `pipeline/` and the data on the branch `run/<run-id>` with the message `run <run-id>: N added, M changed, K re-verified`. Never push.

## When to stop and ask

- A decision that cannot be undone and could reasonably go either way (deleting or merging records, changing a controlled vocabulary).
- A scope question that `pipeline/scope-decisions.md` does not settle: leave it as `needs-human`, do not decide it; it becomes a question issue.
- The subscription's usage limit is near: finish the current stage, set `status` in `run.json`, and tell the human how to resume (`/run-pipeline <run-id>`).

## Your final message

What the run added, changed and re-verified (counts), the agreement rate from step 7, the `needs-human` items with one line each, and the branch name.
