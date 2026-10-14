# Translation check, 14 October 2026

This check measures how well the register's English renders instruments whose official text is not in English: the English titles, the summaries and the defined legal terms. It covers every Chinese, Japanese, Korean and Vietnamese record and a random sample of the other records whose official text is not in English.

**Short answer.** The English titles are reliable. The summaries get what an instrument does right, but not always its exact legal wording: in about one claim in ten, an obligation comes out stronger, weaker or broader than the original, and about one defined term in five is rendered with a near-synonym instead of the original's term. Six of the 45 records that could be checked against their original text had an error that changes the legal meaning. For point-by-point work, use the original text or a government translation, which the record now names where one is stored. The summary tells you what an instrument does; it does not replace its wording.

## What was checked

58 records: every Chinese, Japanese, Korean and Vietnamese record (38), and a random sample of 20 of the other 77 records whose official text is not in English (seed `translation-check-2026-10-14`; Portuguese, Danish, Finnish, Hungarian, Indonesian, Italian, Kazakh, Latvian, Spanish, Arabic, Serbian, Swedish, Slovenian, Slovak, Thai and Turkish). For each record the checker:

1. established the language of the official text, from the stored copy;
2. looked for an English version in the stored copies and with at most two web searches, and classed it as the issuer's own English text, a translation by a public body, a translation by a third party, or none found;
3. checked the English title against the original title and the original title character by character against the stored text;
4. took the three most specific claims of the summary (obligations, scope, numbers, bodies), found the passage in the original-language text, quoted it, translated it literally and judged the claim;
5. compared one to three defined legal terms with the register's English and with the English of an official version, where one exists.

Six agents ran the check in Claude Code with Claude Opus 5.5, a different model from the one that wrote the records (Claude Fable 5.1). They worked only from the copies stored under `archive/`; a script matched every quote against text extracted from the stored file. The Vietnamese laws are scans without a text layer and were read with Tesseract OCR (Vietnamese model), which drops some diacritics; one Turkish bill was transcribed from page images. Each record's findings, with the quotes and literal translations, are in `translation-check-2026-10-14/findings/<ID>.json`.

**Limits.** This is one AI model checking another, not a review by native-speaking lawyers. It catches what a careful second reader of the original catches: shifted obligations, merged or split categories, terms that drift. It cannot certify a translation. Checks by people who read the language are welcome and are logged in the record's history (AGENTS.md section 7.5).

## Results

| Group | Records | Accurate | Minor issues | Errors | Could not check |
|---|---:|---:|---:|---:|---:|
| Chinese | 17 | 5 | 4 | 3 | 5 |
| Japanese | 6 | 0 | 4 | 0 | 2 |
| Korean | 8 | 0 | 6 | 1 | 1 |
| Vietnamese | 7 | 0 | 4 | 1 | 2 |
| Random sample of other languages | 20 | 7 | 9 | 1 | 3 |
| **All** | **58** | **12** | **27** | **6** | **13** |

*Minor issues*: a nuance, a term that differs from the official English without changing the meaning, an original title that is not verbatim, or a remark in the language field. *Errors*: a rendering or claim that changes the legal meaning. *Could not check*: the stored copy does not contain the instrument's own text in the original language.

| What | Checked | Result |
|---|---:|---|
| English titles | 57 | 12 are the issuer's or a government's English title, 45 accurate renderings, none inaccurate |
| Original-language titles | 56 | 46 verbatim; 10 not verbatim (an added descriptor, a dropped "(draft)" marker, wrong capitalisation, a condensed subtitle) or not in any stored file |
| Specific summary claims | 175 | 128 accurate (73 %); 8 overstated, 7 understated, 3 mistranslated (10 % together); 29 not found in the stored text (17 %) |
| Defined legal terms | 164 | 131 consistent (80 %); 29 differ from the original's term or its official English (18 %); 4 wrong (2 %) |

The claims "not found in the stored text" are mostly details the record took from news or law-firm summaries, or claims about a document whose own text is not stored. They are not translation errors, but a reader cannot check them against the original either.

For the 77 non-English records outside China, Japan, Korea and Vietnam, the random sample gives an estimate: 1 of the 17 checkable records had an error, so the share of records with an error there is probably below about 25 percent (one-sided 95 % bound). That is a wide bound; the sample shows that errors occur, not how rare they are.

## The six errors

| Record | What the register says | What the original says |
|---|---|---|
| CN-02, Deep Synthesis Provisions | Providers *and technical supporters* must verify identities and review content; providers file their algorithms | Identity verification and content review are duties of providers only (Arts. 9, 10, 16, 17); filing applies only to services with public-opinion attributes or social-mobilisation capacity (Art. 19) |
| CN-09, Labelling Measures | Requests for *unlabelled* output are allowed under user agreements | Only output without *explicit* labels is allowed; the implicit metadata label (Art. 5) still applies |
| CN-12, AI Plus opinions | Safety makes up about one-fifth of the text | The two safety-related items are about 7 percent of the text (a scope judgment, not a translation error) |
| KR-06, High-impact AI guidelines | "Biometric identification" and "criminal investigation" are separate high-impact domains | One domain: analysis and use of biometric information for criminal investigation or arrest (Act Art. 2(4)(f)); the split widens the defined class |
| SI-01, Slovenian AI Act implementing decree | AKOS supervises most Annex I and III areas; the Information Commissioner only Article 5 | AKOS has Annex I Section A but only Annex III points 2, 4, 5(a), 5(d); the Information Commissioner has Article 5 and Annex III points 1, 3, 6, 7, 8 |
| VN-02, Law on Artificial Intelligence | Treats data, computing and safe AI infrastructure as strategic national assets | Art. 5(4) makes it state policy to prioritise investment in them; "of national strategic character" qualifies the shared AI platforms |

## By language

**Korean (8 records).** No record was fully accurate, and one had an error (KR-06). The Korea Legislation Research Institute (KLRI) publishes an English translation of the AI Basic Act; its own notice says the translations "are for reference only, and are neither official nor legally effective". The register's title for the Act matches KLRI's word for word. No English edition of the Ministry of Science and ICT's five guidelines under the Act was found; the only official English in them is the cover title of the high-impact AI guideline and a few term glosses ("AI business operator", "high-impact AI", "domestic agent", "impacted person"), which the register follows. Recurring drift: "frontier-level" for 최첨단 ("most advanced"), "fundamental-rights impact assessment" for 인공지능 영향평가 ("AI impact assessment"; the guideline uses the former name only for the EU AI Act's Article 27 instrument), "must confirm" for a duty to review in advance (KR-02), and two names for the national AI committee. Not a translation finding but found on the way: the stored copy of the AI Basic Act shows an amendment by Act No. 21311 (20 January 2026, in force 21 July 2026) that the record does not mention.

**Chinese (17 records).** Five accurate, three with errors (CN-02, CN-09, CN-12). The government publishes its own English only for the foreign ministry's documents (CN-05, CN-11) and for some national standards (an English version of GB 45438-2025 is listed on the standards platform). Most laws and measures exist in English only in third-party translations: China Law Translate, the Center for Security and Emerging Technology (CSET) at Georgetown University, and DigiChina at Stanford. For five records only an announcement or catalogue page is stored, not the instrument itself.

**Japanese (6 records).** Four with minor issues, two not checkable (JP-02, METI's guideline, has no stored copy; JP-06's Japanese text is not stored). The Cabinet Office and the Japan AI Safety Institute publish "provisional translations" that ask readers to "refer to the original text for accuracy". The Ministry of Justice's Japanese Law Translation database has a full English text of the AI Promotion Act (not yet stored). The two official overviews of that Act disagree: the Japanese one says businesses "must cooperate", the English one that they "shall endeavor to cooperate". JP-02 is probably out of date: other stored documents cite version 1.2 of the AI Guidelines for Business, while the record names version 1.1.

**Vietnamese (7 records).** Four with minor issues, one error (VN-02), two not checkable. The laws are scans without a text layer. English texts exist on the government news portal and in LuatVietnam, a commercial legal database whose English texts may be its own translations; neither is stored yet. The register wrote the country as "Viet Nam", the Vietnamese government's own English spelling, while it used common short names for every other country; it now writes "Vietnam" in the country and jurisdiction fields, and keeps the issuer's spelling in titles.

**Other languages (random sample of 20).** Seven accurate, nine with minor issues, one error (SI-01), three not checkable (IT-01, MX-01 and SK-02 store no text of the instrument in its own language). Also: PE-02 presents the ban on autonomous lethal capability without saying that it applies only to civilian uses; TR-02 says "traceable training data" where the bill says "transparency and auditability", a word taken from a law firm's summary; LV-03 uses a literal rendering although the State Language Centre publishes an official English title.

## What changed in the register

In the same change set as this report (`translation-check-2026-10-14/pass.json`, merged with `tools/merge.py`, 66 history events):

- `english_version`, a new field, says whether an English text exists and who made it: `authentic` (English is one of the issuer's own texts), `government translation`, `third-party translation` or `none found`, with its link and translator. The names say who translated, not that a text is binding: KLRI's and the Cabinet Office's translations are government translations and expressly not authoritative. It is set for 35 of the checked records, only where the English text is a stored copy or none was found. The app shows a Language section on each record page and an "English text" filter.
- `language` now holds language names only. Fifteen records carried remarks there ("Korean (English reference translation by KLRI)", "Japanese, English" where the English was a provisional translation); `tools/validate.py` now warns about remarks.
- Country names: "Viet Nam" became "Vietnam" and "Brunei Darussalam" "Brunei" in the country and jurisdiction fields of eight records. `pipeline/frame.json` is now the reference for these names, and `tools/validate.py` warns when a record differs from it.
- The extractor and checker instructions (`pipeline/roles/`) now require `english_version` for every new record whose official text is not in English, a verbatim original title, summaries written from the original-language text, and defined terms rendered literally or as a government translation renders them. The evidence script enforces the first and checks that a translation's link is a stored copy.

## What is left

The content corrections go through the pipeline, so that each one is made by an extractor from the stored original and confirmed by a checker:

- **Errors and minor issues, 33 records:** CN-02, CN-07, CN-09, CN-11, CN-12, CN-13, CN-16, JP-01, JP-03, JP-04, JP-05, KR-02, KR-03, KR-04, KR-05, KR-06, KR-07, KR-08, VN-02, VN-03, VN-04, VN-05, VN-06, BR-02, DK-02, HU-02, LV-03, OM-01, PE-02, RS-02, SI-01, TH-03, TR-02.
- **Instrument text missing from the stored copy, 13 records:** CN-06, CN-08, CN-10, CN-15, CN-17, JP-02, JP-06, KR-01, VN-01, VN-07, IT-01, MX-01, SK-02. The archiver stores the official page and the PDFs it links on the same site; where that page is an announcement on another site, a catalogue entry or an empty JavaScript page, the instrument itself is missing although the record is marked archived.
- **English versions to store** (found on the web, linked from a stored page, or unclear): CN-01 (DigiChina), CN-04, CN-10, CN-12, CN-14 (CSET), CN-09, CN-16 (China Law Translate), CN-07 (CAC, English edition of the framework), CN-08 (SAMR standards platform), CN-13 (CAC; possibly bilingual), JP-01 (J-AISI), JP-02 (Ministry of Internal Affairs and Communications), JP-04 (Japanese Law Translation), KR-01 (Korea AI Safety Institute), KR-03 (KLRI, Enforcement Decree), KZ-01 (Adilet), LV-03 (likumi.lv), OM-01 (Ministry of Transport, Communications and IT), SE-01 (English summary in the inquiry report), VN-02 (government news portal), VN-05 and VN-07 (LuatVietnam), DK-02 (EU TRIS notification). The links are in the findings files.

One refresh run over these 46 records (`/run-pipeline refresh` with `ids:` and the list above, the findings files given to the extractors as leads) would store the missing texts and translations, correct the summaries, and record `english_version` for the rest. The 57 records whose official text is not in English and that this check did not cover get `english_version` the same way in a later refresh or recheck run.
