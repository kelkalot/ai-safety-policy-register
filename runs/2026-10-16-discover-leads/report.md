# Run 2026-10-16-discover-leads

What to look at first. This leads run adds three of the four pre-2023 instruments queued on 15 Oct 2026, all at level A: China's New Generation AI Development Plan (CN-28), the EU Ethics Guidelines for Trustworthy AI (EU-20) and EO 13960 (US-29). EO 13859 (C003) is held for a human: the stored Federal Register text supports its title, number and date, but no stored source shows that it is still in force, and the checker found no revocation either. A maintainer can settle it in its question issue with an official source on its current status. Both executive orders' in-force dates differ between the two extractions (signing date or none); the checker marks it a judgment difference and the signing date stands for US-29.

Type: discover. Scope: refresh queue. Started 2026-10-16; report written 2026-10-16.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| extract | Claude Code | claude-opus-5-5 | 2026-10-16 |
| blind | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-16 |

## Summary

- Candidates: 4 (active 4)
- Added: 3; fields changed: 5 in 5 record(s); re-verified without change: 0
- Not added: 0; need a human: 1; not ready: 0
- Repeatability: 91% field agreement between blind double extractions (4 pair(s))

## Added

- **CN-28** New Generation AI Development Plan; Published (non-binding, current); level A
- **EU-20** HLEG Ethics Guidelines for Trustworthy AI; Published (non-binding, current); level A
- **US-29** EO 13960; In force; level A

## Changed

- **CN-12** related: + CN-28 (two-way link to CN-28 added in run 2026-10-16-discover-leads)
- **US-06** related: + US-29 (two-way link to US-29 added in run 2026-10-16-discover-leads)
- **US-12** related: + US-29 (two-way link to US-29 added in run 2026-10-16-discover-leads)
- **US-17** related: + US-29 (two-way link to US-29 added in run 2026-10-16-discover-leads)
- **US-19** related: + US-29 (two-way link to US-29 added in run 2026-10-16-discover-leads)

## Re-verified without change

None.

## Needs a human

Held back: a value this run changes is not settled. The published record stays as it was.

- C003: checker: Title, number, dates and legal force are supported by the Federal Register print. The status 'In force' has no quote showing that the order is still current; the evidence script passed it only because the Sec. 10(b) quote exists in the file. Option for a human or the next run: store the 13960 text and M-26-04 evidence is not enough, so store the Federal Register disposition or a later official document naming 13859 as current. Not found revoked.; status is unsupported and the checker gave no evidence-backed fix

## Merged with an open question



None.

## Not added

None.

## Repeatability

Blind second extraction of 4 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 4 | 4 |
| title | 4 | 4 |
| original_title | 1 | 1 |
| issuing_body | 4 | 3 |
| official_identifier | 3 | 3 |
| date_published | 4 | 4 |
| date_in_force | 2 | 0 |
| status | 4 | 4 |
| legal_force | 4 | 4 |
| instrument_type | 4 | 4 |
| jurisdiction_level | 4 | 4 |
| region | 4 | 4 |
| country | 4 | 4 |
| safety_topics | 4 | 3 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-16-discover-leads --id CN-28 --result ok --note "..."

- [ ] CN-28 New Generation AI Development Plan
- [ ] EU-20 HLEG Ethics Guidelines for Trustworthy AI
- [ ] US-29 EO 13960

## Search coverage

3 of 3 cells logged (found 3).

## Leads and open questions

- lead from C002: {"title": "Assessment List for Trustworthy Artificial Intelligence (ALTAI) for self-assessment, AI HLEG, made public 17 Jul 2020", "url": "https://ec.europa.eu/newsroom/dae/document.cfm?doc_id=68342", "cell": "EU/executive", "why": "The AI HLEG's final assessment list, published by the Commission; an expert-group report on AI risk self-assessment not in the register."}
- lead from C002: {"title": "Coordinated Plan on Artificial Intelligence, agreed and published by the Commission and Member States in December 2018 (the guidelines cite the Commission Communication of 7 Dec 2018, COM(2018)795)", "cell": "EU/executive", "why": "Cited in footnotes 4, 5 and 37 of the guidelines, footnote 37 for security considerations in its section 2.7; an EU AI plan not in the register."}
- lead from C003: {"title": "OMB memorandum to agency heads on regulatory and non-regulatory approaches to AI applications, required by Sec. 6(a) of EO 13859 (issued in draft for public comment first, Sec. 6(b))", "cell": "US/executive", "why": "Federal guidance for regulating AI applications; not in the register."}
- lead from C003: {"title": "NIST plan for Federal engagement in the development of technical standards and related tools for reliable, robust and trustworthy AI, required by Sec. 6(d) of EO 13859", "cell": "US/executive", "why": "Government plan on AI technical standards; not in the register."}
