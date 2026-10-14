# Run 2026-10-14-discover-codes-us-fl

What to look at first. (1) The three hosts under "Hosts to review" are Florida government sites: flrules.org (Department of State; Florida Administrative Code and Register), fldoe.org (Department of Education) and flbog.edu (Board of Governors). Once a person records who runs them, US-FL-13 and US-FL-14 would compute level A on a rerun of `evidence`. (2) Scope of US-FL-15 and US-FL-16, the Supreme Court rule amendment and the ethics opinion on generative AI for Florida lawyers: whether an integrated state bar counts as a regulator or as a professional association has no precedent in `pipeline/scope-decisions.md`. US-FL-16's scope note refers to the register's own scope rules and should be reworded once that is decided. (3) C015 and the companion order AOSC26-12: the Supreme Court of Florida's site disallows automated downloads, so only a person can store them, and `archive.py --provide` takes record IDs, so an instrument without a record has no route yet. (4) C014, the Board of Governors' amendment on AI disclosure in syllabi, whose adoption is not stored. Leads L001 and L002 became US-FL-02 and US-FL-03; L003 (SB 262) was judged out of scope as a general privacy law. US-FL-01 is queued for a refresh because SB 482 was refiled as SB 2-D (US-FL-04).

Type: discover. Scope: codes:US-FL. Started 2026-10-14; report written 2026-10-14.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | Claude Code | claude-opus-5-5 | 2026-10-14 |
| extract | Claude Code | claude-opus-5-5 | 2026-10-14 |
| blind | Claude Code | claude-opus-5-5 | 2026-10-14 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-14 |

## Summary

- Candidates: 19 (active 17, out-of-scope 1, refresh-request 1)
- Added: 15; fields changed: 4 in 4 record(s); re-verified without change: 0
- Not added: 0; need a human: 2; not ready: 0
- Repeatability: 80% field agreement between blind double extractions (5 pair(s))

## Added

- **US-FL-02** Florida AI political advertising disclaimer law (HB 919, 2024); In force; level A
- **US-FL-03** Florida SB 1680 (2024): AI council and generated CSAM offence; In force; level A
- **US-FL-04** Florida AI Bill of Rights (SB 2-D, 2026 Special Session D); Lapsed; level A
- **US-FL-05** Brooke's Law (Florida HB 1161, 2025); In force; level A
- **US-FL-06** Florida HB 757 (2025): sexual images and deepfake generation; In force; level A
- **US-FL-07** Florida SB 1798 (2022): altered sexual depictions offence; In force; level A
- **US-FL-08** Florida HB 1159 (2026): sexual offences and generated CSAM; In force; level A
- **US-FL-09** Florida HB 527 (2026): human review of AI claim denials; Lapsed; level A
- **US-FL-10** Florida HB 491 (2025): AI concealed-firearm detection ban; Lapsed; level A
- **US-FL-11** Florida HB 369 (2025): provenance of AI-generated content; Lapsed; level A
- **US-FL-12** Florida education act 2024 (HB 1361): AI grants for schools; In force; level A
- **US-FL-13** Florida K-12 AI safety policy rule (6A-1.0957, 2026); Adopted, not yet in force; level C
- **US-FL-14** Florida college AI policies rule (6A-14.0719); Adopted, not yet in force; level C
- **US-FL-15** Florida Bar conduct rules: generative AI comments (2024); In force; level C
- **US-FL-16** Florida Bar Ethics Opinion 24-1 on generative AI; Published (non-binding, current); level C

## Changed

- **US-KY-01** related: + US-FL-02 (two-way link to US-FL-02 added in run 2026-10-14-discover-codes-us-fl)
- **US-FL-01** related: + US-FL-04 (two-way link to US-FL-04 added in run 2026-10-14-discover-codes-us-fl)
- **US-14** related: + US-FL-05 (two-way link to US-FL-05 added in run 2026-10-14-discover-codes-us-fl)
- **US-CA-13** related: + US-FL-08 (two-way link to US-FL-08 added in run 2026-10-14-discover-codes-us-fl)

## Re-verified without change

None.

## Needs a human

Held back: a value this run changes is not settled. The published record stays as it was.

- C014: checker: Quotes verified and the summary matches the agenda item, but the status as of today cannot be supported: the Board met on 3 Sep 2026 and the outcome is not stored. A secondary university document hints that the amendment moved forward. A later run should store the Board minutes or the regulation page; a human can settle status meanwhile. Level C because flbog.edu is not a listed host.; status is unsupported and the checker gave no evidence-backed fix; the checker found something possibly newer: Possible progress of the amendment after the 3 Sep 2026 Board meeting; FAU minutes https://www.fau.edu/ufsgov/documents/steeringcommitteemeetingminutesseptember32026.pdf (not stored); https://www.fau.edu/ufsgov/documents/steeringcommitteemeetingminutesseptember32026.pdf
- C015: extractor: Probably in scope with a scope_note under the include-and-flag rules: per the candidate entry, a statewide court rule amendment (rule 2.515(d)(2), Florida Rules of General Practice and Judicial Administration) adopted in response to inaccurate citations generated by generative AI in court filings, with a rule text that does not mention AI. It would be the operative instrument for an AI-safety question (accuracy of AI-assisted filings), which the rules admit with a scope_note. Nothing about it can be extracted until a copy is stored.

## Merged with an open question



None.

## Not added

None.

Dropped before extraction:

- CS/CS/SB 262 (2023): Technology Transparency, creating the Florida Digital Bill of Rights (Laws of Florida ch. 2023-201) (US-FL/legislature): out-of-scope
- CS/SB 482 (2026): Artificial Intelligence Bill of Rights, refiled as SB 2-D in Special Session D (US-FL/legislature): refresh-request US-FL-01

## Repeatability

Blind second extraction of 5 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 5 | 5 |
| title | 5 | 0 |
| issuing_body | 5 | 3 |
| official_identifier | 5 | 1 |
| date_published | 5 | 4 |
| date_in_force | 4 | 4 |
| date_last_updated | 1 | 1 |
| status | 5 | 5 |
| legal_force | 5 | 5 |
| instrument_type | 5 | 5 |
| jurisdiction_level | 5 | 5 |
| region | 5 | 5 |
| country | 5 | 5 |
| safety_topics | 5 | 5 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-14-discover-codes-us-fl --id US-FL-06 --result ok --note "..."

- [ ] US-FL-06 Florida HB 757 (2025): sexual images and deepfake generation
- [ ] US-FL-07 Florida SB 1798 (2022): altered sexual depictions offence
- [ ] US-FL-10 Florida HB 491 (2025): AI concealed-firearm detection ban
- [ ] US-FL-13 Florida K-12 AI safety policy rule (6A-1.0957, 2026)
- [ ] US-FL-14 Florida college AI policies rule (6A-14.0719)

## Search coverage

5 of 5 cells logged (found 4, nothing 1).

## Hosts to review

Quotes from these hosts counted as secondary because the host is neither a government domain nor listed in `pipeline/official-sites.json`. If the issuing body runs the host, or uses it as its own channel, record it with `python3 tools/pipeline.py hosts --add HOST --code CODE --status official --by NAME --operator ... --evidence-url ...`, and run `evidence` again.

- flbog.edu: C014
- fldoe.org: C012, C013
- flrules.org: C012, C013

## Leads and open questions

- lead from C015: Supreme Court of Florida, Administrative Order AOSC26-12, In re: Representations by Signers of Filings (2026), https://flcourts-media.flcourts.gov/content/download/2489379/29182858 — per the candidate entry, the companion order to SC2026-0673 replacing circuit-court AI disclosure and certification orders; flcourts.gov disallows automated downloads, so only a person can store it.
- C014: The amended text of Regulation 1.001 and the outcome of the Board of Governors' vote of 3 Sep 2026 on the notice of intent are not stored; flbog.edu regulation pages refuse automated requests. Did the Board approve the notice and, after the 14-day comment period, adopt the amendment at a later meeting? If adopted, status, date_published and date_in_force change.
- C015: No stored copy of In re: Amendments to Florida Rule of General Practice and Judicial Administration 2.515, No. SC2026-0673 (Supreme Court of Florida): the official PDF on flcourts-media.flcourts.gov is disallowed by robots.txt, and the FindLaw copy returned HTTP 403 (browser retry timed out). Title, issuing body, identifier, dates, status and legal force stay null. A person can download the official PDF (and AOSC26-12) and store it with archive.py --provide; a later run can then extract the record, which looks in scope with a scope_note (an AI-neutral court rule on accurate citations adopted in response to generative-AI errors in filings).
- C017: Scope: is an advisory ethics opinion of The Florida Bar in scope? The Florida Bar administers the professional conduct rules for lawyers (like a supervisory authority, whose AI guidance AGENTS.md section 10 admits) but is also the lawyers' professional association (whose documents section 10 excludes). The record is included with a scope_note under the inclusive default; a scope decision for integrated state bars would settle this and similar opinions of other state bars.
- C017: The Florida Bar's own page for Opinion 24-1 refuses automated requests (403, also in the browser); the record rests on a university's copy of the text and stays at level C until a person provides the official page (archive.py --provide).
