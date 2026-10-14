# Run 2026-10-14-refresh-ids-ca-on-01-coe-01-int-15-us-ca

<!-- coordinator: one paragraph here on what a human should look at first -->
**Look at first.** (1) The one change of substance: CA-ON-01 is now *In force* from 29 Jan 2025, on Order in Council 361/2025 and the e-Laws consolidation (stored ontario.ca copies). The human sample is all four changed records, starting with this one. (2) COE-01: every Council of Europe page returns HTTP 403 to this network, so the Convention's status as of today needs the Treaty Office chart of signatures and ratifications, checked by hand. (3) The other nine needs-human records are level-C records from version 1. The checker held their whole text against stored sources for the first time, and their notes and summaries carry claims from pages that were seen but never stored. The usual fix is to trim them to the stored text, or to store an official copy from a network the legislature sites accept (leginfo.legislature.ca.gov, legislature.idaho.gov, rilegislature.gov, leg.state.nv.us, silpy.congreso.gov.py, law.go.th and coe.int all refused this one). (4) Two decisions on `known_hosts` in `pipeline/frame.json` affect levels. Whether `gov-pritzker-newsroom.prezly.com` (the Illinois Governor's newsroom on a commercial platform) counts as official decides between level A and C for US-IL-01, which is why US-IL-01 was not merged. 48 hosts came into `known_hosts` only from records' `secondary_url`, among them law firms (cms.law, tilleke.com, basham.com.mx, nixonpeabody.com, skadden.com, morogluarseven.com), news sites and an advocacy tracker. None of them raised a level in this run, but they should be removed, and `ontario.ca` added for CA-ON. (5) The 100% repeatability figure covers only the fields that both extractors changed; in a refresh run the comparison skips fields left unchanged. (6) The check ran on claude-sonnet-5-5, because the Fable usage limit was reached before any check file was written.

Type: refresh. Scope: ids:CA-ON-01,COE-01,INT-15,US-CA-07,US-CA-08,CN-06,PY-01,TH-01,US-27,US-ID-01,US-IL-01,US-NV-01,US-RI-01,VN-07. Started 2026-10-14; report written 2026-10-14.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | - | - | - |
| extract | Claude Code | claude-opus-5-5 | 2026-10-14 |
| blind | Claude Code | claude-opus-5-5 | 2026-10-14 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-14 |

## Summary

- Candidates: 14 (active 14)
- Added: 0; fields changed: 10 in 4 record(s); re-verified without change: 0
- Not added: 0; need a human: 10; not ready: 0
- Repeatability: 100% field agreement between blind double extractions (5 pair(s))

## Added

None.

## Changed

- **CA-ON-01** status: Adopted, not yet in force → In force (Schedule 1, ss. 1-16 came into force on 29 Jan 2025 under Order in Council 361/2025, as the e-Laws consolidation confirms.)
- **CA-ON-01** date_in_force: - → 2025-01-29 (29 Jan 2025, the day named in Order in Council 361/2025.)
- **CA-ON-01** notes: Royal Assent received on 25 November 2024 (S.O. 2024, c. 24… → Royal Assent received on 25 November 2024 (S.O. 2024, c. 24… (Added the commencement order and the regulations made so far (none for AI). Removed the earlier remark about e-Laws and the unconfirmed status, which is now settled.)
- **US-CA-07** date_last_updated: 2026-09-18 → - (2026-09-18 is the date of EO N-9-26, a separate implementing order recorded as US-CA-09, not an amendment or new version of SB 813 or AB 1405. AGENTS.md 5.6 keeps the field for amendments and new versions; the EO stays in the notes.)
- **US-CA-07** official_identifier: California Senate Bill 813 and Assembly Bill 1405 (2025-202… → California Senate Bill 813 and Assembly Bill 1405; Governme… (pipeline run 2026-10-14-refresh-ids-ca-on-01-coe-01-int-15-us-ca (refresh), candidate US-CA-07)
- **US-CA-07** notes: Both signed 9 Sep 2026. Effective dates not confirmed; Cali… → Both signed 9 Sep 2026. EO N-9-26 of 18 Sep 2026 (US-CA-09)… (Removed the remark that the effective dates were unconfirmed (it now sits in verification.note), and with it the default-rule date, which no stored file supports. EO N-9-26 deadlines kept and linked to US-CA-09.)
- **US-CA-08** summary: Strengthens children's protections on companion chatbots. T… → SB 1119, 'Adam's Law', named after Adam Raine, expands Cali… (Rewritten from the stored author release, which names the bill 'Adam's Law (SB 1119)' and lists its requirements. This replaces the earlier source-attributed wording ('The Governor's release describes...').)
- **US-CA-08** safety_topics: + incident reporting (Added 'incident reporting': the bill requires 'an incident reporting mechanism, overseen by the Attorney General' (Padilla release).)
- **US-CA-08** notes: Signed 10 Sep 2026 (Padilla; Wicks; Bauer-Kahan) in a 13-bi… → Passed the Legislature on 31 Aug 2026 (Senate 39-0, Assembl… (Added the 31 Aug 2026 passage and votes, the bill's links to SB 243, AB 1043 and AB 1064, and the private right of redress. Package bills are given by their listed titles. Removed the remarks on the 'Adam's Law' mapping and the unconfirmed effective date (now settled or in verification.note).)
- **US-RI-01** notes: Reported signed on 22 Jun 2026 and effective 1 Jan 2027. En… → Signed by the Governor on 22 Jun 2026 and effective 1 Jan 2… (The signing date is now in a stored copy (tracker action '06/22/2026 Signed by Governor'), so 'Reported signed' loses its hedge; added the Senate and House passage dates and the companion bill from the stored action history.)

## Re-verified without change

None.

## Needs a human

- COE-01: extractor: needs-human: the stored EU documents (Council 9718/25 ADD 1, Decisions (EU) 2024/2218 and 2026/1080) support the Convention's title, the date of 5 Sep 2024, its adoption by the Committee of Ministers on 17 May 2024, the Article 30 entry-into-force rule and the EU's approval of 21 Apr 2026. They cannot show whether five signatories, at least three of them CoE member States, had ratified by 30 Jun 2026, which is what entry into force on or before 14 Oct 2026 would require. Every CoE source (www.coe.int, rm.coe.int, the record's own URLs) returned HTTP 403. A human should check the CoE Treaty Office chart of signatures and ratifications for the treaty and confirm or change status and date_in_force.; official_identifier 'CETS No. 225' is not in any stored file; it rests on the 11 Oct 2026 pass.; date_last_updated is 2026-05-15, the EU ratification date. Under AGENTS.md 5.6 the field is for the last amendment or new version, and one Party's ratification is neither, so it should probably become null, with the ratification kept in the notes. The stored Decision 2026/1080 dates the EU's approval 21 Apr 2026 (published in OJ L 13 May 2026); the 15 May 2026 deposit in the notes is not in any stored file.; If the human confirms the status, the three EU documents can serve as the record's alt-official evidence (level B). Level A needs a stored CoE page.
- INT-15: checker: The extracted changes are well supported (signing, 29 founding members, 31 Jul close of signature). Needs a human for three items with no stored evidence: the July 2025 proposal claim in notes, the non-language value in language, and a single safety topic. Status stays provisional until a treaty text or depositary notice is stored.
- CN-06: checker: New summary and notes are supported by the CSET translation, but the record is level C and two inherited values lack stored evidence. official_identifier TC260-003 is not in any stored file (search results name it; Junhe and sesec pages could be stored for evidence), and status 'Superseded' is judgment. The official URL is dead. A human should decide on the identifier, status and URL. Blind extraction made no changes and agrees (no disagreements in agreement.json).
- PY-01: checker: The extraction's new summary and verification note are supported by the stored Última Hora article (level C). Three record fields are not: status as of today (a May 2025 report only), issuing_body (six co-sponsors absent from stored sources), and notes (hearing, MITIC and co-sponsor claims unstored, plus process wording 'SILpy file number was not identified'). A targeted web search found no newer version or enactment (only a June 2025 Senate public hearing, on a Senate page that is not stored). A human should check the SILpy file S-2502197 and rewrite notes.
- TH-01: checker: The extraction only changes verification.note, which is accurate. The record as it stands has two problems that predate this run but are not covered by stored sources: the summary's June 2025 predecessor clause is unsupported, and notes misstate the Thai PBS article (hearing described as concluded on 1 August) and rely on unstored sources (Rajah & Tann, ETDA 2025 page, law.go.th, ONDE). Level stays C. A targeted search found no Cabinet approval or newer draft.
- US-27: checker: Title, date, status and the summary are supported by the American Presidency Project copy of the accord and the Obernolte/Trahan statement (level C, no whitehouse.gov copy; a targeted search again found none). Notes carry claims from press reports that are not stored (roundtable, EO 14434 link, 'morally binding' remark). The blind extraction agrees on every compared field; it also carries the EO 14434 claim unstored. Record needs a scope_note for a government-brokered company commitment.
- US-ID-01: checker: Title, enactment date, effective date, status and legal force are supported by the Transparency Coalition tracker (level C). The summary and notes go well beyond that one stored source: AG enforcement, penalties, the three-hour disclaimer, the votes and the Governor's signature are unstored, and both texts contain hedges ('reported', 'Trackers give', 'should be checked'). A targeted search found no newer version; it did show LegiScan listing Session Law Chapter 249 and mostly July 1, 2027, but those pages are not stored. A human should decide whether to trim the summary to the stored text or store a bill copy.
- US-IL-01: checker: Status, effective date and summary are supported. Two issues. (1) official_identifier 'Public Act 103-0804' is not in any stored text; a human or an ilga.gov copy should confirm it. (2) The only official source for date and status is gov-pritzker-newsroom.prezly.com, listed in known_hosts. It is the State of Illinois Newsroom page and carries the Governor's press contact, but it sits on Prezly, a commercial platform, and it is the reason the level moves from C to A. A human should decide whether that host counts as official. A search suggests the IDHR notice rules proposed on 15 May 2026 may have been withdrawn (one secondary source only); the notes' 'as of April 2026' phrasing is still true.
- US-NV-01: checker: Enactment, approval date, chapter, votes, sponsors and the summary are supported by the stored NASW-NV and FastDemocracy pages (level C). The 1 July 2025 effective date, the Governor's name and the amended NRS chapters are not in any stored text, so date_in_force and the status 'In force' need a human or a stored official copy (the enrolled bill and NELIS page failed to store). Targeted search found no repeal or amendment. The blind extraction agrees with the main extraction on the compared fields.
- VN-07: checker: Law number, adoption date, entry into force, repeal of Chapter IV on 1 March 2026 and status are supported by stored Government News and Can Tho pages (level C; the vbpl.vn copy is an empty shell). The summary and notes go beyond them: first-statute claim, labelling and definition content, the Law on AI number, the vote and structure, and hedged wording. The search found no newer amendment; it did surface an official text on vanban.chinhphu.vn (listed in extra_urls) that, once stored, could support Chapter IV's content.

## Not added

None.

## Repeatability

Blind second extraction of 5 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 5 | 5 |
| official_identifier | 1 | 1 |
| date_in_force | 1 | 1 |
| status | 1 | 1 |
| safety_topics | 1 | 1 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-14-refresh-ids-ca-on-01-coe-01-int-15-us-ca --id CA-ON-01 --result ok --note "..."

- [ ] CA-ON-01 Ontario Bill 194 / Enhancing Digital Security and Trust Act
- [ ] US-CA-07 California SB 813 / AB 1405 (AI independent verification & auditors)
- [ ] US-CA-08 California SB 1119 (children's chatbot safety)
- [ ] US-RI-01 Rhode Island AI Companion Models Act (S 2195)

## Leads and open questions

- lead from CA-ON-01: {"title": "Ontario Responsible Use of Artificial Intelligence Directive", "url": null, "seen_in": "archive/_runs/2026-10-14-refresh-ids-ca-on-01-coe-01-int-15-us-ca/CA-ON-01/extra-918dfb6d5e/2026-10-14/official.html", "why": "The page says the Directive 'sets requirements and guiding principles for the transparent, responsible and accountable use of AI by Ontario ministries and provincial agencies'. The register has no record of it."}
- lead from CA-ON-01: {"title": "Ontario's Trustworthy Artificial Intelligence Framework", "url": null, "seen_in": "same page, 'Related information'", "why": "Ontario government AI framework linked from the EDSTA page; not in the register."}
- lead from CN-06: {"title": "网络安全标准实践指南——智能体系统开发安全指南（征求意见稿） (TC260 practice guide draft: security guide for developing AI agent systems)", "url": "https://www.tc260.org.cn/", "seen_in": "archive/CN-06/2026-10-14/official.html (TC260 homepage, notice of 2026-09-18)", "why": "TC260 public consultation on AI-agent system development security, Sep 2026; not in the register."}
- lead from CN-06: {"title": "网络安全技术 人工智能安全能力成熟度评估方法 (draft national standard: AI security capability maturity assessment method)", "url": "https://www.tc260.org.cn/", "seen_in": "archive/CN-06/2026-10-14/official-rendered.html (TC260 homepage, consultation 2026-08-26 to 2026-10-25)", "why": "Draft national standard on AI security assessment under consultation; not in the register."}
- lead from CN-06: {"title": "TC260-PG-20268A 网络安全标准实践指南——人工智能应用安全指引 总则 (v1.0-202609) and sector guides such as 卫生健康 (TC260-PG-202610A)", "url": "https://www.tc260.org.cn/tc260/sjzn/list.shtml", "seen_in": "web search results while looking for the TC260-003 page", "why": "TC260 practice guides on AI application security issued in Sep 2026; not in the register."}
- lead from PY-01: {"title": "Chamber of Deputies bill promoting the use of artificial intelligence for the economic and social development of the country (D-2584139)", "url": "https://silpy.congreso.gov.py/web/expediente/142181", "note": "Separate Paraguayan AI bill named in the record's notes as not recorded; listed with this SILpy file by Morrison & Foerster's AI tracker."}
- lead from PY-01: {"title": "Supreme Court of Justice of Paraguay, Resolución N° 12.677 (guidelines on the use of AI in the judiciary)", "url": null, "note": "Reported in a search result (palabrasdelderecho.com.ar, June 2026); a judicial-branch AI guideline that may fall in scope."}
- lead from TH-01: {"title": "People's Party draft Artificial Intelligence Act for creative workers (ร่างพระราชบัญญัติปัญญาประดิษฐ์ (AI) เพื่อคนสร้างสรรค์ ฉบับพรรคประชาชน)", "url": "https://www.thairath.co.th/news/politic/2948798", "note": "Opposition party's own AI bill, discussed at a forum on 26 July 2026 per Thairath; a private members' bill that may merit a record with a scope_note."}
- lead from US-27: {"title": "Interagency 'Super Intelligence Force' (task force) announced 4 October 2026", "url": "https://www.crowell.com/en/insights/client-alerts/white-house-announces-ai-responsibility-accord-executive-orders-and-super-intelligence-task-force", "note": "Reported by search results as created after the accord with a report due within 120 days; the founding instrument may be in scope."}
- lead from US-CA-07: {"title": "California Executive Order N-5-26 (30 Mar 2026) on AI procurement, civil rights, civil liberties and privacy", "url": null, "seen_in": "archive/US-CA-07/2026-10-11/secondary.pdf, page 1", "why": "EO N-9-26 recites it as directing that state AI procurement and adoption protect civil rights, civil liberties and privacy and be 'transparent, safe, and responsible'. The register has no record of it."}
- lead from US-CA-08: {"title": "California SB 867 (2026): Toys: companion chatbots", "url": "https://www.gov.ca.gov/2026/09/10/governor-newsom-signs-the-strongest-child-safety-chatbot-and-social-media-laws-in-the-nation/", "seen_in": "archive/US-CA-08/2026-10-14/official.html", "why": "Signed 10 Sep 2026 in the same package. It regulates companion chatbots in toys, an AI child-safety measure, and is named only in the notes of US-CA-06 and US-CA-08, without its own record."}
- lead from US-CA-08: {"title": "California Executive Order N-12-23 (6 Sep 2023) on generative AI", "url": "https://www.gov.ca.gov/wp-content/uploads/2023/09/AI-EO-No.12-_-GGN-Signed.pdf", "seen_in": "archive/US-CA-08/2026-10-14/document-1.pdf", "why": "Governor's order directing state agencies to assess generative AI risks and set guardrails for state use. It is already stored as a linked document here, and the register has no record of it."}
- lead from US-IL-01: {"title": "IDHR proposed rules on notice of AI use in employment (Illinois Human Rights Act)", "url": null, "seen_in": "archive/_runs/2026-10-14-refresh-ids-ca-on-01-coe-01-int-15-us-ca/US-IL-01/extra-442285362c/2026-10-14/official.pdf, pages 17-21", "why": "Implementing rules for HB 3773's notice duty, at the proposed stage in April 2026. Either an implementing regulation for the register or a note on this record once an official IDHR or Illinois Register source is stored."}
- lead from US-NV-01: {"title": "Nevada State Executive Branch policy on the responsible and ethical use of artificial intelligence (draft)", "url": "https://www.it.nv.gov/uploadedFiles/itnew.nv.gov/content/About(1)/Policy on the Responsible and Ethical Use of Artificial Intelligence in Nevada State Government Executive Branch(draft).pdf", "note": "Governor Lombardo's AI policy for the executive branch, found in a search result; a state government AI-use framework that may be in scope."}
- lead from VN-07: {"title": "Decree No. 353/2025/NĐ-CP detailing the Law on Digital Technology Industry (31 December 2025)", "url": "https://luatvietnam.vn/cong-nghiep/nghi-dinh-353-2025-nd-cp-quy-dinh-chi-tiet-luat-cong-nghiep-cong-nghe-so-423495-d1.html", "note": "Implementing decree; check whether it has AI provisions that survived the repeal of Chapter IV."}
- CA-ON-01: Host recognition: ontario.ca is the Government of Ontario's own domain, but it is not in CA-ON known_hosts in pipeline/frame.json (only ola.org) and does not match the government-domain pattern. The evidence script will therefore count the OIC and e-Laws quotes as secondary. The level still reaches A, because title and date rest on OLA quotes and status also has the s. 17 commencement rule from the OLA Royal Assent text. A human should add ontario.ca to CA-ON known_hosts.
- CN-06: official_identifier 'TC260-003' is not in any stored file: the official URL now serves the TC260 homepage, the CSET page does not give the number, and the requested copies (perma.cc, c-csa.cn) could not be stored. It is kept as it is and rests on the 11 Oct 2026 pass.
- CN-06: The official URL (tc260.org.cn/portal/article/2/20240301164054) no longer leads to the notice; the TC260 site has been redesigned and no replacement official page for TC260-003 was found. A human may want to keep the URL as a dead link and say so, or replace it if TC260 republishes the document.
- CN-06: Level stays C: no stored official file supports title, date or status.
- COE-01: needs-human: the stored EU documents (Council 9718/25 ADD 1, Decisions (EU) 2024/2218 and 2026/1080) support the Convention's title, the date of 5 Sep 2024, its adoption by the Committee of Ministers on 17 May 2024, the Article 30 entry-into-force rule and the EU's approval of 21 Apr 2026. They cannot show whether five signatories, at least three of them CoE member States, had ratified by 30 Jun 2026, which is what entry into force on or before 14 Oct 2026 would require. Every CoE source (www.coe.int, rm.coe.int, the record's own URLs) returned HTTP 403. A human should check the CoE Treaty Office chart of signatures and ratifications for the treaty and confirm or change status and date_in_force.
- COE-01: official_identifier 'CETS No. 225' is not in any stored file; it rests on the 11 Oct 2026 pass.
- COE-01: date_last_updated is 2026-05-15, the EU ratification date. Under AGENTS.md 5.6 the field is for the last amendment or new version, and one Party's ratification is neither, so it should probably become null, with the ratification kept in the notes. The stored Decision 2026/1080 dates the EU's approval 21 Apr 2026 (published in OJ L 13 May 2026); the 15 May 2026 deposit in the notes is not in any stored file.
- COE-01: If the human confirms the status, the three EU documents can serve as the record's alt-official evidence (level B). Level A needs a stored CoE page.
- INT-15: language holds a remark, 'Not confirmed (multilingual treaty text not reviewed)', not a language. No stored page gives the Agreement's authentic languages, so the field cannot be filled from evidence; it is left as it is.
- INT-15: safety_topics has one value ('international cooperation'), below the minimum of two in AGENTS.md 5.6. The stored pages describe the Agreement's purposes only in general terms (a 'beneficial, safe and fair direction', bridging the AI divide), which do not clearly support a second topic from the vocabulary. Not changed.
- INT-15: 'First proposed by China at WAIC in July 2025' (notes) is not in the stored pages; it rests on the earlier pass.
- INT-15: Entry-into-force and ratification conditions are unknown; no stored page has the treaty text or a depositary notice.
- INT-15: The total number of signatories after 16 Jul 2026 is not known: the stored pages show 29 at the ceremony plus Georgia on 31 Jul 2026, and others may have signed in the same window.
- PY-01: official_identifier and official_url stay null: the SILpy file (https://silpy.congreso.gov.py/web/expediente/142635, expediente S-2502197) and the SILpy PDF of the bill could not be stored in this run.
- PY-01: issuing_body lists six co-sponsors that the stored report does not name; the unstored SILpy file lists eight authors, adding Sen. Patrick Kemper.
- PY-01: date_published could become 2025-05-08 (SILpy entry date) once an official copy is stored.
- PY-01: Current legislative stage is not shown by any stored copy; the record's status rests on the absence of later events in a May 2025 report.
- PY-01: notes says 'The bill's SILpy file number was not identified', which is research-process wording; rewrite the notes once the SILpy file is stored.
- TH-01: No official copy of the 2026 draft is stored: the law.go.th hearing page (survey_id NzU4MERHQV9MQVdfRlJPTlRFTkQ=) failed with HTTP 403.
- TH-01: The hearing window conflicts between sources (release 2 July with about 30 days of comments vs 9 July to 14 August 2026, the latter not stored).
- TH-01: Whether the draft has gone to the Council of State or the Cabinet after the hearing is not shown by any stored copy; a later refresh should check.
- US-27: No official White House copy of the accord exists in the stored sources; whitehouse.gov was not reachable or showed no copy.
- US-27: The Truth Social posting and the 'morally binding' remark in notes are not confirmed by any stored text.
- US-27: issuing_body says 'Alphabet/Google' and 'xAI'; the signature block reads 'Google' and 'XAI'.
- US-CA-07: date_in_force: neither stored file gives an effective date. The leginfo pages for SB 813, AB 1405 and Gov. Code sec. 9600 were requested and could not be stored. 1 Jan 2027, the default for a non-urgency statute enacted in Sep 2026, is the expected value, but it stays null until a stored source gives it. Status 'Adopted, not yet in force' holds either way until 1 Jan 2027.
- US-CA-07: official_identifier is kept as it is. 'California Senate Bill 813 and Assembly Bill 1405' and the Government Code sections are supported. '(2025-2026 Regular Session)' is not in the stored files, and '(as cited in EO N-9-26)' is a remark about the source, not part of an identifier. Once leginfo can be stored, the identifier should give the chapter numbers (Statutes of 2026) and drop the remark.
- US-CA-07: The title is descriptive, not the bills' official titles; leginfo would give the official short titles.
- US-CA-08: date_in_force: no stored file gives an effective date. The leginfo pages for SB 1119 and Gov. Code sec. 9600 were requested and could not be stored. 1 Jan 2027 is the expected default for a non-urgency statute enacted in Sep 2026, but the field stays null; the status holds until then either way.
- US-CA-08: official_identifier is kept as it is. 'Senate Bill 1119' is supported; '(2025-2026 Regular Session)' is not in a stored file, and the chapter number is unknown without leginfo.
- US-CA-08: The requirements in the summary come from the author's release on the version passed by the Legislature on 31 Aug 2026. The Governor's release confirms that version was signed, but no stored file has the chaptered text.
- US-CA-08: The record's second stored file, document-1.pdf, is EO N-12-23 (2023), followed by the archiver from a link in the release. It is not a source for SB 1119.
- US-ID-01: No official copy is stored: all four legislature.idaho.gov sources (bill page sessioninfo/2026/legislation/S1297/, S1297.pdf, S1297E1.pdf, Idaho Code Title 48 chapter PDF) failed.
- US-ID-01: issuing_body ('signed by Governor Brad Little') and official_identifier ('68th Idaho Legislature') are not in the stored tracker.
- US-ID-01: Sponsor conflict: the stored tracker names 'Green' as sponsor, while a KIVI-TV report found by search says Sen. Ben Toews introduced the bill in the Senate State Affairs Committee on 20 February 2026.
- US-ID-01: The summary's penalty clause ('penalties are reported at USD 1,000 per violation, capped at USD 500,000 per operator') is hedged and rests on an unstored source.
- US-ID-01: notes end with 'the enrolled text should be checked', which is research-process wording; rewrite once an official copy is stored.
- US-IL-01: official_identifier 'Public Act 103-0804 (HB 3773, 103rd General Assembly)' is kept as it is. The bill number HB3773 is supported by the Governor's release; the Public Act number and the General Assembly are not in any stored file (ilga.gov could not be reached).
- US-IL-01: The HRC-site presentation is by a Fisher Phillips partner, not by the Commission, so its quotes are labelled secondary although the host is official. Status and date_in_force also rest on the Governor's release (official).
- US-NV-01: date_in_force (2025-07-01) has no stored evidence; the enrolled bill (AB406_EN.pdf) failed to store.
- US-NV-01: issuing_body names Governor Joe Lombardo; the stored tracker says only 'Approved by the Governor'.
- US-NV-01: official_url is still null; the Legislature's NELIS overview (https://www.leg.state.nv.us/App/NELIS/REL/83rd2025/Bill/12575/Overview, named in the stored tracker) should become official_url once it can be stored.
- US-RI-01: No official copy is stored: S2195A.htm, H7350A.htm and the General Assembly press release on rilegislature.gov all failed.
- US-RI-01: official_identifier ('2026 S 2195 Sub A / H 7350 Sub A'): the stored tracker gives the enacted text as '2195 SUB A as amended' with companion HB 7350; no public-law chapter number is stored.
- US-RI-01: The 1 January 2027 effective date rests only on the Nixon Peabody alert; the bill text was not stored.
- VN-07: No copy of the law's own text is stored: the vbpl.vn page (ItemID 179989) is an empty JavaScript shell.
- VN-07: original_title's '(Chương IV về trí tuệ nhân tạo)' and the description of Chapter IV as the AI chapter are not explicit in any stored copy.
- VN-07: notes contain hedges ('reported 441 of 445', 'press and law-firm reports', 'reportedly issued a consolidated text') whose facts are not in a stored copy; left unchanged and flagged in verification.note.
