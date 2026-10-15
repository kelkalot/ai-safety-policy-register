# Run 2026-10-15-refresh-ids-us-fl-13-us-fl-14

What to look at first. This run tests the loop from a maintainer's decision to a changed record: after flrules.org and fldoe.org were decided official (#44, #45), US-FL-13 and US-FL-14 compute level A from the final rule notices on flrules.org. Both now carry a scope note under the precedent of 15 Oct 2026 on sector-wide rules; AGENTS.md section 10 admits AI-specific sub-national rules with no note, so the precedent's wording may need narrowing to rules where AI is only part of the content. The checker marks date_published as a judgment difference (rule file date rather than the State Board's adoption on 16 Sep 2026); the file date stands. Both rules take effect on 20 and 29 Oct 2026, so a refresh after those dates moves them to In force.

Type: refresh. Scope: ids:US-FL-13,US-FL-14. Started 2026-10-15; report written 2026-10-15.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | - | - | - |
| extract | Claude Code | claude-opus-5-5 | 2026-10-15 |
| blind | Claude Code | claude-opus-5-5 | 2026-10-15 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-15 |

## Summary

- Candidates: 2 (active 2)
- Added: 0; fields changed: 4 in 2 record(s); re-verified without change: 0
- Not added: 0; need a human: 0; not ready: 0

## Added

None.

## Changed

- **US-FL-13** scope_note: - → Borderline as a rule on AI use in one public sector: the St… (precedent of 15 Oct 2026 in pipeline/scope-decisions.md (Institutions and sector-wide rules): a state education department's rule for all school districts is in, with a scope_note)
- **US-FL-13** verification.level: C → A (level computed from the evidence by tools/pipeline.py)
- **US-FL-14** scope_note: - → Borderline as a rule on AI use in one public sector: the St… (precedent of 15 Oct 2026 in pipeline/scope-decisions.md (Institutions and sector-wide rules): a state board's regulation that binds all public colleges is in, with a scope_note)
- **US-FL-14** verification.level: C → A (level computed from the evidence by tools/pipeline.py)

## Re-verified without change

None.

## Needs a human



None.

## Merged with an open question



None.

## Not added

None.

## Repeatability

Blind second extraction of 2 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 2 | 2 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-15-refresh-ids-us-fl-13-us-fl-14 --id US-FL-13 --result ok --note "..."

- [ ] US-FL-13 Florida K-12 AI safety policy rule (6A-1.0957, 2026)
- [ ] US-FL-14 Florida college AI policies rule (6A-14.0719)

## Leads and open questions

- lead from US-FL-13: {"title": "U.S. Department of Education Dear Colleague Letter of 20 Aug 2026 on the responsible use of education technology", "url": null, "note": "Named in the Florida Department of Education press release of 16 Sep 2026; whether it deals with AI is not known; not in the register."}
- lead from US-FL-13: {"title": "Florida Digital Classrooms Plan, update directed by the Commissioner of Education in September 2026", "url": null, "note": "Named in the same press release as an update to come on how educational technology is evaluated and used in schools; not in the register."}
