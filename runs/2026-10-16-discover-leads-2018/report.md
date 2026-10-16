# Run 2026-10-16-discover-leads-2018

What to look at first. The register had no records dated 2018; this leads run adds six. Five are level A: the Commission's Communication on AI for Europe (EU-21), the CEPEJ Ethical Charter (COE-03, whose identifier rests on a secondary copy because coe.int refuses the archiver), the French AI for Humanity strategy (FR-02, from the ministry's press kit and the President's speech, since no single strategy text exists), the G7 Charlevoix Common Vision (G7-07) and India's NITI Aayog strategy (IN-04; its release date is given as 4 June and 27 June 2018 by two NITI sources, both in the notes). The German strategy (DE-02) is level C only because dserver.bundestag.de, ki-strategie-deutschland.de and bundesregierung.de are not listed as official for DE (see Hosts to review). The 2018 Coordinated Plan (C002) is held for a human: its 2021 review may supersede it.

Type: discover. Scope: refresh queue. Started 2026-10-16; report written 2026-10-16.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| extract | Claude Code | claude-opus-5-5 | 2026-10-16 |
| blind | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-16 |

## Summary

- Candidates: 7 (active 7)
- Added: 6; fields changed: 1 in 1 record(s); re-verified without change: 0
- Not added: 0; need a human: 1; not ready: 0
- Repeatability: 91% field agreement between blind double extractions (5 pair(s))

## Added

- **EU-21** EU Communication on AI for Europe (2018); Published (non-binding, current); level A
- **COE-03** CEPEJ Ethical Charter on AI in judicial systems; Published (non-binding, current); level A
- **DE-02** German Federal AI Strategy (2018); Published (non-binding, current); level C
- **FR-02** France AI for Humanity strategy (2018); Published (non-binding, current); level A
- **G7-07** G7 Charlevoix Common Vision on AI (2018); Published (non-binding, current); level A
- **IN-04** India National Strategy for AI (#AIforAll); Published (non-binding, current); level A

## Changed

- **EU-20** related: + EU-21 (two-way link to EU-21 added in run 2026-10-16-discover-leads-2018)

## Re-verified without change

None.

## Needs a human

Held back: a value this run changes is not settled. The published record stays as it was.

- C002: checker: Content, title, number and date are supported by the stored PDFs. A targeted search found the 2021 Review of the plan (COM(2021) 205) on an official Commission site. It is not stored, so the status of the 2018 edition (current or Superseded) goes to a human and a later run should store the 2021 Review.; status is unsupported and the checker gave no evidence-backed fix; the checker found something possibly newer: {'what': 'Coordinated Plan on Artificial Intelligence 2021 Review, annex to COM(2021) 205 of 21 April 2021, published as an updated edition of the plan', 'url': 'https://digital-strategy.ec.europa.eu/en/library/new-coordinated-plan-artificial-intelligence', 'also': 'https://ec.europa.eu/transparency

## Merged with an open question



None.

## Not added

None.

## Repeatability

Blind second extraction of 5 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 5 | 5 |
| title | 5 | 5 |
| original_title | 1 | 0 |
| issuing_body | 5 | 4 |
| official_identifier | 3 | 2 |
| date_published | 5 | 4 |
| status | 5 | 5 |
| legal_force | 5 | 5 |
| instrument_type | 5 | 5 |
| jurisdiction_level | 5 | 5 |
| region | 5 | 5 |
| country | 5 | 5 |
| safety_topics | 5 | 4 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-16-discover-leads-2018 --id COE-03 --result ok --note "..."

- [ ] COE-03 CEPEJ Ethical Charter on AI in judicial systems
- [ ] DE-02 German Federal AI Strategy (2018)
- [ ] EU-21 EU Communication on AI for Europe (2018)
- [ ] FR-02 France AI for Humanity strategy (2018)
- [ ] G7-07 G7 Charlevoix Common Vision on AI (2018)

## Search coverage

6 of 6 cells logged (found 6).

## Hosts to review

Quotes from these hosts counted as secondary because the host is neither a government domain nor listed in `pipeline/official-sites.json`. If the issuing body runs the host, or uses it as its own channel, record it with `python3 tools/pipeline.py hosts --add HOST --code CODE --status official --by NAME --operator ... --evidence-url ...`, and run `evidence` again.

- bundesregierung.de: C004
- dserver.bundestag.de: C004
- elysee.fr: C005
- ki-strategie-deutschland.de: C004

## Leads and open questions

- lead from C003: {"title": "CEPEJ assessment tool for the operationalisation of the European Ethical Charter on the use of AI in judicial systems, CEPEJ(2023)16", "url": "https://rm.coe.int/cepej-2023-16final-operationalisation-ai-ethical-charter-en-ita/1680b6d03b", "note": "Adopted December 2023 (a revised version CEPEJ(2023)16rev also exists); not in the register and not checked."}
- lead from C004: {"title": "Opinion of the Data Ethics Commission (Gutachten der Datenethikkommission), Germany, 2019", "url": null, "note": "The 2018 strategy says it will take up the commission's recommendations; not in the register and not checked."}
- lead from C004: {"title": "Final report of the Bundestag Enquete Commission on Artificial Intelligence (set up 27 September 2018)", "url": null, "note": "Named in the strategy as a body to coordinate with; not in the register and not checked."}
- lead from C005: {"title": "Donner un sens à l'intelligence artificielle : pour une stratégie nationale et européenne (Villani report, made public 28 March 2018)", "url": "https://www.enseignementsup-recherche.gouv.fr/fr/rapport-de-cedric-villani-donner-un-sens-l-intelligence-artificielle-ia-49194", "note": "Government-commissioned report on which the strategy is based; not in the register."}
- lead from C006: {"title": "G7 Montreal Ministerial Statement on Artificial Intelligence (2018)", "url": null, "note": "Named in the Charlevoix Common Vision; not in the register and not checked."}
- lead from C006: {"title": "G7 ICT and Industry Ministers' Torino Declaration (2017)", "url": null, "note": "Named in the Charlevoix Common Vision; not in the register and not checked."}
- lead from C007: {"title": "Responsible AI #AIForAll: Approach Document for India, Part 1 - Principles for Responsible AI (NITI Aayog, February 2021)", "url": "https://www.niti.gov.in/sites/default/files/2021-02/Responsible-AI-22022021.pdf", "note": "NITI's follow-up to the 2018 discussion paper on responsible AI; not in the register."}
- C002: The lead for this candidate (L009) says the plan was reviewed in 2021. No later edition is stored, so the status stays Published (non-binding, current); a later run should check whether the 2021 review superseded this first edition.
- C003: official_identifier CEPEJ(2018)14 has only secondary evidence: the official PDF on rm.coe.int answers 403 to the archiver. A browser retry or a provided document (AGENTS.md section 7.8) would give official evidence for it and for the wording of the principles.
- C004: Host review: dserver.bundestag.de, ki-strategie-deutschland.de and bundesregierung.de are not in pipeline/official-sites.json; until a person records them as official for DE, every quote for this record counts as secondary and the computed level is C.
- C005: Host review: elysee.fr is not listed as official for FR in pipeline/official-sites.json (it is for G7 and INT); until a person records it, the speech's quotes count as secondary. Title, date and status also have official evidence from the gouv.fr press kit.
- C005: The 1.5 billion euros were planned over the five-year term to 2022; a later run should check whether a later phase of the national AI strategy superseded this one.
- C007: Two NITI Aayog sources give different days: the AIRAWAT approach paper says the strategy was released on 4 June 2018, NITI's publication page shows 27 June 2018. The record uses 4 June; a person may confirm.
