# Run 2026-10-14-refresh-ids-us-fl-01

What to look at first. US-FL-01 now rests only on stored Senate sources: the notes add the special-session bill SB 2-D (US-FL-04) and the enforcement provisions of the engrossed text, and two claims that only an unstored press report supported (the Governor's backing and the House Speaker's position) are removed. The notes do not call SB 2-D a refiling, because no stored page says so; they give the shared title and description. The secondary URL is still that press report, which refuses the archiver; a human may want to replace it.

Type: refresh. Scope: ids:US-FL-01. Started 2026-10-14; report written 2026-10-14.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | - | - | - |
| extract | Claude Code | claude-opus-5-5 | 2026-10-14 |
| blind | Claude Code | claude-opus-5-5 | 2026-10-14 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-14 |

## Summary

- Candidates: 1 (active 1)
- Added: 0; fields changed: 4 in 1 record(s); re-verified without change: 0
- Not added: 0; need a human: 0; not ready: 0
- Repeatability: 67% field agreement between blind double extractions (1 pair(s)); 100% agreement on the resulting records (12 field values; in a refresh run the first figure counts only fields that an extraction changed)

## Added

None.

## Changed

- **US-FL-01** issuing_body: Florida Senate (2026 Regular Session; sponsor Sen. Tom Leek… → Florida Senate (2026 Regular Session; sponsor Sen. Leek) (No stored source shows the Governor's backing or the sponsor's first name; the bill page names the sponsor as Leek and the analyses as Senator Leek (with the Appropriations Committee for the committee substitute).)
- **US-FL-01** date_last_updated: 2026-03-13 → 2026-03-04 (The last new version is the engrossed text S 482 e1, posted 4 Mar 2026 when the Senate adopted two floor amendments and passed the bill; 13 Mar 2026 is the date the bill died, not a new version.)
- **US-FL-01** summary: Governor-backed omnibus 'Artificial Intelligence Bill of Ri… → Would have created an 'Artificial Intelligence Bill of Righ… (Rewritten from the engrossed text the Senate passed: adds the hourly bot notice, the deidentified-data rule and the school AI-tool rule (s. 1006.1495), which the committee substitute added. Removed 'Governor-backed', which no stored source supports, and moved the legislative history to the notes.)
- **US-FL-01** notes: Filed 22 Dec 2025; favourable in Commerce and Tourism (10-0… → Filed on 22 Dec 2025 and referred to Commerce and Tourism a… (Added SB 2-D of 2026 Special Session D (same title and bill description; passed the Senate 37-1 on 28 Apr 2026, died in a House subcommittee on 29 Apr 2026), as the refresh request asked. Added the committee history, the changes made by the committee substitute, HB 1395, and the enforcement provisions as passed (USD 50,000 civil penalties, 45-day cure period, NIST AI RMF / ISO 42001 controls, USD 10,000 damages for minors). Removed the House Speaker's position and the Governor's campaign, which no stored source supports.)

## Re-verified without change

None.

## Needs a human



None.

## Merged with an open question



None.

## Not added

None.

## Repeatability

Blind second extraction of 1 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 1 | 1 |
| issuing_body | 1 | 1 |
| date_last_updated | 1 | 1 |
| safety_topics | 1 | 0 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-14-refresh-ids-us-fl-01 --id US-FL-01 --result ok --note "..."

- [ ] US-FL-01 Florida AI Bill of Rights (SB 482, 2026)
