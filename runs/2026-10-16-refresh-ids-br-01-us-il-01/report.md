# Run 2026-10-16-refresh-ids-br-01-us-il-01

<!-- coordinator: one paragraph here on what a human should look at first -->
BR-01 (Brazil's PL 2338/2023) now has the bill's own text in its local copy: the Senate's signed copy as presented in the Chamber, which the record's summary, topics, title and notes now follow article by article. Its level goes from A to B because the 3 May 2023 date is on the Senate page, which the local copy no longer holds; a later refresh that stores the Senate page again brings it back to A. US-IL-01 (Illinois HB 3773) could not be checked: ilga.gov times out and ilsos.gov refuses the archiver, so its title, dates and status rest on secondary sources (level C, an open question). A person who downloads Public Act 103-0804 and the Illinois Register issues of 15 May and 26 June 2026 and provides them settles it. The proposed IDHR rules under HB 3773 are a lead for a separate record.

Type: refresh. Scope: ids:BR-01,US-IL-01. Started 2026-10-16; report written 2026-10-16.

| Stage | Tool | Model | Date |
|---|---|---|---|
| collect | - | - | - |
| extract | Claude Code | claude-opus-5-5 | 2026-10-16 |
| blind | Claude Code | claude-sonnet-5-5 | 2026-10-16 |
| check | Claude Code | claude-sonnet-5-5 | 2026-10-16 |

## Summary

- Candidates: 2 (active 2)
- Added: 0; fields changed: 9 in 1 record(s); re-verified without change: 1
- Not added: 0; need a human: 0; not ready: 0
- Repeatability: 0% field agreement between blind double extractions (2 pair(s)); 85% agreement on the resulting records (13 field values; in a refresh run the first figure counts only fields that an extraction changed)

## Added

None.

## Changed

- **BR-01** title: Bill No. 2338/2023 on the development, promotion and ethica… → Bill No. 2338/2023 on the development, promotion and ethica… (Rendered from the full ementa of the stored text; the earlier title left out 'based on the centrality of the human person' (com base na centralidade da pessoa humana).)
- **BR-01** original_title: Projeto de Lei nº 2338/2023 – Dispõe sobre o desenvolviment… → Projeto de Lei nº 2338, de 2023 – Dispõe sobre o desenvolvi… (The number in the form both chambers use in full ('Projeto de Lei nº 2338, de 2023', as on the Chamber page) followed by the ementa verbatim from the stored text; 'nº 2338/2023' does not appear in that form on any stored page.)
- **BR-01** date_last_updated: 2026-09-02 → 2024-12-10 (The last new version of the text is the Senate substitute definitively adopted on 10 Dec 2024; the 2 Sep 2026 entry was an attachment of other bills, not a new version of PL 2338/2023.)
- **BR-01** secondary_url: https://www25.senado.leg.br/web/atividade/materias/-/materi… → https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegr… (Points the record's second source at the stored bill text, so that the local copy holds the bill's own text; see local_copy_reasoning.)
- **BR-01** summary: Comprehensive risk-based AI framework passed by the Senate:… → Sets national rules for responsible governance of AI system… (Rewritten from the stored Portuguese text (arts. 1, 6, 13, 14, 18, 19, 25, 29, 30, 42 and 45), using the bill's own terms: 'excessive risk' (risco excessivo), 'high risk' (alto risco), general-purpose and generative AI (IA de propósito geral e generativa), systemic risk (risco sistêmico), synthetic content (conteúdo sintético), serious incidents (grave incidente), the SIA and the ANPD as competent authority. Moved liability and fines to the notes.)
- **BR-01** safety_topics: - accountability & liability (Six topics, each backed by a provision: risk-based classification (arts. 12-15), prohibited practices (art. 13), general-purpose / frontier AI (arts. 29-30), human oversight (arts. 6 and 8), transparency & labelling (art. 19), incident reporting (art. 42). Dropped 'accountability & liability': the record had seven topics, one more than allowed, and the liability chapter mostly keeps the existing Consumer Defence Code and Civil Code regimes (arts. 35-36); the liability and fine provisions are now in the notes.)
- **BR-01** notes: Presented in the Senate 3 May 2023; Senate plenary approved… → Presented in the Federal Senate by Sen. Rodrigo Pacheco on … (Rewritten from the stored pages and text: adds the CTIA approval, the Senate's final adoption and the bills declared prejudicados, the autógrafo of 31 Jan 2025, the Ofício and art. 65 review, the phased entry into force of art. 80, the liability and fine provisions, the Chamber's distribution, Special Committee and priority regime, the 2026 attachments, the absence of a Chamber report and the version the English translation renders. Removed the press reports on the timing of a vote and the remark that Chamber amendments send the bill back to the Senate, which no stored source shows, and the sentence on the excluded PBIA, which was about the research, not the bill.)
- **BR-01** english_version: - → {"kind": "third-party translation", "url": "https://campost… (The only English text found: a Google machine translation of the Senate's revised text of 19 Dec 2024, published by Campos Thomaz Advogados (third-party); stored in this run.)
- **BR-01** verification.level: A → B (level computed from the evidence by tools/pipeline.py)

## Re-verified without change

US-IL-01

## Needs a human



None.

## Merged with an open question

The run's checked corrections are merged; these points about values it left as published are open questions (GitHub issues, `pipeline.py questions --sync`).

- US-IL-01: checker: The run changes only verification.note, which is accurate and carries CAUTION. No title, date or status can be supported from a stored file, since the ILGA page has not been stored in any attempt and the IDHR page names no statute. Web search agrees with the published values (signed 9 Aug 2024, effective 1 Jan 2026) but only from secondary sources, and conflicts on whether the 2026 IDHR rules were withdrawn. The existing notes sentence about what the IDHR page says belongs in verification.note. A human or a run on a network that reaches ilga.gov must store the Public Act.; title is unsupported and the checker gave no evidence-backed fix; official_identifier is unsupported and the checker gave no evidence-backed fix; date_published is unsupported and the checker gave no evidence-ba

## Not added

None.

## Repeatability

Blind second extraction of 2 candidate(s) (AGENTS.md section 7.4).

| Field | Compared | Agree |
|---|---:|---:|
| decision | 2 | 1 |
| title | 1 | 0 |
| original_title | 1 | 0 |
| date_last_updated | 1 | 0 |
| safety_topics | 1 | 0 |

## Human sample

Check these records against their stored sources, then log the result, for example:

    python3 tools/pipeline.py log-human --run 2026-10-16-refresh-ids-br-01-us-il-01 --id BR-01 --result ok --note "..."

- [ ] BR-01 Brazil AI Bill (PL 2338/2023)
- [ ] US-IL-01 Illinois HB 3773 (AI in employment)

## Leads and open questions

- lead from US-IL-01: {"title": "Illinois Department of Human Rights, proposed amendments to 56 Ill. Adm. Code 2520 (Procedures of the Department of Human Rights): new subpart on the use of artificial intelligence in employment decisions (Sections 2520.900 and 2520.910), notice and record-keeping rules implementing Public Act 103-0804", "url": "https://www.ilsos.gov/content/dam/departments/index/register/volume50/register_volume50_20.pdf", "seen_in": "web search results (Illinois Register issue list on ilsos.gov; alerts by Kilpatrick Townsend, Seyfarth and others); withdrawal reportedly in the Illinois Register of 26 Jun 2026, https://www.ilsos.gov/content/dam/departments/index/register/volume50/register_volume50_26.pdf", "why": "A proposed implementing regulation by the state's anti-discrimination authority (a horizontal supervisor), published 15 May 2026 and withdrawn in June 2026; in scope as a withdrawn proposed rule and not in the register. It could become its own record related to US-IL-01."}
- BR-01: date_published (3 May 2023) rests only on the Senate page, stored in this run as the record's secondary source (alt-official). With secondary_url pointing at the bill text, the Senate page leaves the local copy; a later refresh should request it in extra_urls.
- US-IL-01: title, official_identifier (Public Act 103-0804), date_published (2024-08-09), date_in_force (2026-01-01), status (In force), legal_force and issuing_body are not supported by any stored file; the only stored file (IDHR legislative updates) names no statute. They stay as published until the Public Act text or the ILGA bill status page is stored.
- US-IL-01: summary: the elements it states (discriminatory effect, zip codes as a proxy, notice to employees) rest on no stored text; check against Public Act 103-0804 once stored.
- US-IL-01: notes: 'Approved 9 Aug 2024; effective 1 Jan 2026' and the enforcement by IDHR and the Human Rights Commission rest on no stored file; the sentence about what the IDHR page says is about a source and belongs in verification.note; the 2026 rulemaking (proposed 15 May 2026, withdrawn June 2026) should be added once the Illinois Register issues are stored.
- US-IL-01: Whether IDHR has republished or restarted the AI rulemaking after the June 2026 withdrawal is unknown; the stored IDHR page (14 Oct 2026) shows no open comment period.
