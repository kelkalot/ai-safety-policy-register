# Run 2026-10-16-refresh-ids-us-04-us-ca-05-us-tx-01-ca-0

<!-- coordinator: one paragraph here on what a human should look at first -->
This run stored the instruments' own texts for six records whose local copies held only press releases, status pages or bot-check pages. US-04, CA-02, JP-04 and KZ-01 now point their official_url (and, for CA-02 and KZ-01, secondary_url) at the stored text, so their local copies hold it. Two texts still need a person: the chaptered SB 53 for US-CA-05 (leginfo refuses automated downloads, also in a browser) and the enrolled HB 149 for US-TX-01 (capitol.texas.gov's robots.txt disallows /TLODOCS/; the archiver now compares robots rules without letter case). Either can be stored with `python3 tools/archive.py --provide FILE --id ID --url URL --by NAME` or the Provide a document form. Look first at US-TX-01 (level C: title and adoption date have no stored official source) and at the host old.adilet.zan.kz, the Kazakh law database whose quotes count as secondary until a maintainer decides it.

Type: refresh. Scope: ids:US-04,US-CA-05,US-TX-01,CA-02,JP-04,KZ-01. Started 2026-10-16; report written 2026-10-16.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | - | - | - |
| extract | Claude Code | claude-opus-5-5 | 2026-10-16 |
| blind | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-16 |

## Summary

- Candidates: 6 (active 6)
- Added: 0; fields changed: 20 in 6 record(s); re-verified without change: 0
- Not added: 0; need a human: 0; not ready: 0
- Repeatability: 0% field agreement between blind double extractions (5 pair(s)); 100% agreement on the resulting records (62 field values; in a refresh run the first figure counts only fields that an extraction changed)

## Added

None.

## Changed

- **US-04** official_url: https://www.federalregister.gov/documents/2023/11/01/2023-2… → https://www.govinfo.gov/content/pkg/FR-2023-11-01/pdf/2023-… (the Federal Register printing of the order on govinfo.gov, stored in this run; federalregister.gov serves the archiver only a bot-check page, so the record had no stored text of its own)
- **US-04** secondary_url: - → https://govinfo.gov/content/pkg/FR-2025-01-28/html/2025-019… (EO 14148 as printed in the Federal Register (govinfo.gov, stored in this run): the revoking order, which is the source a later refresh needs for the status)
- **US-04** summary: Comprehensive federal AI order that used Defense Production… → Comprehensive federal order on AI safety and security. Unde… (rewritten from the order's text: the order directed the Secretary of Commerce to require the reports under the Defense Production Act (section 4.2), rather than requiring them itself, and the interim thresholds and the CBRN section (4.4) are named)
- **US-04** safety_topics: - safety institute, - national security & military (eight values cut to six as the vocabulary rule requires; 'safety institute' dropped because the order's text does not mention a safety institute, and 'national security & military' dropped as the least central of the remaining ones (the order directs a national security memorandum in section 4.8))
- **US-CA-05** summary: First US state frontier-AI safety law. Large frontier devel… → California's frontier AI safety law. Large frontier develop… (rewritten so that every claim rests on a stored official text (the Governor's release and the Office of Emergency Services page); the duty to publish transparency reports for new models is dropped from the summary because no stored official text states it, and is recorded in verification.note)
- **US-CA-05** notes: Signed 29 Sep 2025; effective 1 Jan 2026. Applies to fronti… → Signed 29 Sep 2025. Large frontier developers must send the… (research remarks removed ('secondary source', 'Not amended as of verification', 'commentators named it'), the unsupported thresholds, penalty cap and incident deadlines moved to verification.note, and the quarterly catastrophic-risk summaries and the signing message's compliance pathway added from stored texts)
- **US-TX-01** notes: Effective 1 Jan 2026. No private right of action. A rebutta… → Chapter 552 took effect on 1 Jan 2026. The Attorney General… (rewritten from Chapter 552: the research remark ('not verified on the fetched page') removed, the unconfirmed sandbox and council claim moved to verification.note, and the enforcement details (notice and cure, penalty ranges, defences, agency sanctions, preemption) added from Sections 552.003 and 552.101 to 552.106)
- **US-TX-01** verification.level: A → C (level computed from the evidence by tools/pipeline.py)
- **CA-02** official_url: https://www.parl.ca/legisinfo/en/bill/44-1/c-27 → https://www.parl.ca/Content/Bills/441/Government/C-27/C-27_… (the bill's own text at first reading (parl.ca PDF, stored in this run); the record had only the LEGISinfo status page and ISED's description)
- **CA-02** secondary_url: https://ised-isde.canada.ca/site/innovation-better-canada/e… → https://www.parl.ca/legisinfo/en/bill/44-1/c-27 (LEGISinfo, the page a later refresh needs for the bill's status; ISED's archived AIDA page drops out)
- **CA-02** safety_topics: - general-purpose / frontier AI ('general-purpose / frontier AI' dropped: the bill's text at first reading regulates high-impact systems and has no provision on general-purpose systems or models)
- **CA-02** notes: Introduced 16 June 2022 (first reading); referred to the St… → Introduced 16 June 2022 (first reading); second reading and… (the prorogation and its effect now rest on the Speaker's release; the order-in-council commencement of the Artificial Intelligence and Data Act added (its section 41); the press-report sentence and the remark that Bill C-36 is excluded from the register removed)
- **JP-04** official_url: https://www8.cao.go.jp/cstp/ai/ai_act/ai_act.html → https://www.shugiin.go.jp/internet/itdb_housei.nsf/html/hou… (the Act's own text as promulgated, on the House of Representatives' site (plain HTML, stored in this run); the Cabinet Office page described the Act but did not contain it)
- **KZ-01** date_last_updated: - → 2026-06-24 (Әділет footnotes to Articles 1, 13, 17, 20 and 28 record amendments by the law of 24.06.2026 No. 326-VIII)
- **KZ-01** official_identifier: - → Law No. 230-VIII ZRK (№ 230-VIII ЗРК) of 17 November 2025 (the number from the Әділет heading 'от 17 ноября 2025 года № 230-VIII ЗРК')
- **KZ-01** official_url: https://www.akorda.kz/ru/glavoy-gosudarstva-podpisan-zakon-… → https://old.adilet.zan.kz/rus/docs/Z2500000230 (the law's own Russian text on Әділет (old.adilet.zan.kz, plain HTML, stored in this run); the Akorda notice only announces the signature. old.adilet.zan.kz is not yet in pipeline/official-sites.json, so its quotes count as secondary until a person records the host)
- **KZ-01** secondary_url: https://www.akorda.kz/ru/glavoy-gosudarstva-podpisan-zakon-… → https://www.akorda.kz/ru/glavoy-gosudarstva-podpisan-zakon-… (the Akorda signing notice, formerly official_url: the official record of the President's signature and of the publication of the text; the Akorda notice on the companion law drops out)
- **KZ-01** summary: Central Asia's first comprehensive AI law. It defines AI sy… → Framework AI law. It defines an AI system as a digital obje… (rewritten from the Russian text: an AI system is now defined as a 'цифровой объект' (digital object), not an object of informatisation; goods and services made with AI require informing users (Article 21(1)), while labelling applies to synthetic outputs (Article 21(2)); the risk and autonomy classes and the full list of prohibitions (Article 17) added; the evaluative 'Central Asia's first comprehensive AI law' removed)
- **KZ-01** safety_topics: + risk-based classification ('risk-based classification' added for the minimal, medium and high risk classes of Article 17(1))
- **KZ-01** notes: Signed on 17 Nov 2025, together with a companion law amendi… → Signed on 17 Nov 2025, together with a companion law amendi… (the commencement rule (Article 31) and the 2026 amendment added from the text, and the provisions on high-risk systems, audit and copyright; research remarks removed ('reportedly', 'assumes', 'could not be fetched', 'Uzbekistan and other Central Asian states were not covered', 'referenced on primeminister.kz'))

## Re-verified without change

None.

## Needs a human



None.

## Merged with an open question

The run's checked corrections are merged; these points about values it left as published are open questions (GitHub issues, `pipeline.py questions --sync`).

- US-TX-01: title is unsupported and the checker gave no evidence-backed fix; date_published is unsupported and the checker gave no evidence-backed fix; title has no evidence; date_published has no evidence

## Not added

None.

## Repeatability

Blind second extraction of 5 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 5 | 5 |
| safety_topics | 2 | 0 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-16-refresh-ids-us-04-us-ca-05-us-tx-01-ca-0 --id CA-02 --result ok --note "..."

- [ ] CA-02 AIDA
- [ ] JP-04 Japan AI Promotion Act (AI Act)
- [ ] US-04 EO 14110 (Biden AI Executive Order)
- [ ] US-CA-05 California SB 53 (TFAIA)
- [ ] US-TX-01 Texas TRAIGA

## Hosts to review

Quotes from these hosts counted as secondary because the host is neither a government domain nor listed in `pipeline/official-sites.json`. If the issuing body runs the host, or uses it as its own channel, record it with `python3 tools/pipeline.py hosts --add HOST --code CODE --status official --by NAME --operator ... --evidence-url ...`, and run `evidence` again.

- old.adilet.zan.kz: KZ-01

## Leads and open questions

- lead from KZ-01: {"title": "Law of the Republic of Kazakhstan of 24 Jun 2026 No. 326-VIII amending the AI Law", "url": null, "note": "Named in Әділет footnotes to Articles 1, 13, 17, 20 and 28 of the AI Law as the amending law; its full subject is not known; not in the register."}
- CA-02: ourcommons.ca (House of Commons) is not in pipeline/official-sites.json for CA, so the Speaker's release counts as secondary until a person records the host; LEGISinfo on parl.ca carries the status on its own.
- KZ-01: date_in_force is null: Article 31 counts 60 calendar days from the first official publication, whose date is on the Әділет information page that could not be stored (the server closed the connection).
- KZ-01: issuing_body names Parliament, which no stored file states; the Әділет information page names the adopting body. The text is signed 'Президент Республики Казахстан К. ТОКАЕВ'.
- KZ-01: english_version is not recorded: Әділет publishes an English text marked as an unofficial translation, but the archiver could not store it.
- KZ-01: old.adilet.zan.kz is not in pipeline/official-sites.json for KZ; the site names itself the legal information system of the Ministry of Justice's Institute of Legislation and Legal Information. Until a person records it with hosts --add, quotes from it count as secondary, and after the merge the record's level will rest on the Akorda notice as secondary_url.
- US-CA-05: No official copy of the chaptered SB 53 text could be stored: leginfo.legislature.ca.gov refuses the archiver (HTTP 403, also in a browser), and no other official copy of the chaptered bill or the statute was found on another official site. date_in_force (2026-01-01), the chapter number (Chapter 138, Statutes of 2025 according to third-party trackers) for official_identifier, and the thresholds, penalty cap and incident deadlines in verification.note wait for a person to provide the chaptered bill from leginfo (AGENTS.md 7.8).
- US-CA-05: official_url (the Governor's release) and secondary_url (leginfo, which cannot be stored) stay as they are, so after the merge the record's local copy holds only the release; the signing message and the Office of Emergency Services page that support the status are stored only in this run's folder.
- US-TX-01: title: no stored official text gives the short title 'Texas Responsible Artificial Intelligence Governance Act'; Chapter 552 is headed 'Artificial Intelligence Protection'. The enrolled bill (capitol.texas.gov/tlodocs/89R/billtext/html/HB00149F.HTM) is closed to the archiver by robots.txt and needs a person to provide it (AGENTS.md 7.8).
- US-TX-01: date_published (2025-06-22) and 'signed by Governor Greg Abbott' in issuing_body rest on no stored source; the Texas Legislature Online bill history (/BillLookup/) is closed by robots.txt and the Legislative Reference Library refuses automated access, so the signing date needs a person to provide the history page or another official record of the signature.
- US-TX-01: The regulatory sandbox and the Texas Artificial Intelligence Council, which the Act is said to create in other chapters, are not in the stored text; they wait for the enrolled bill.
