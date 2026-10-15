# Scope decisions

Precedents for borderline cases, so that the same kind of instrument gets the same decision in every run. Extractors and checkers apply them; only a human adds a new one, from the `needs-human` items of a run. Each case also goes into `data/history.jsonl` as a `scope-decision` event when it changes a record.

Format: **instrument** (record ID if any): decision. Reason. *Decided by, date.*

## General rules (decided in issue #2, October 2026)

The register is inclusive: borderline instruments are included and flagged with a `scope_note` instead of being left out.

- A strategy or action plan with some safety or risk-governance content is in. When safety is not its main content, it gets a `scope_note`.
- A law that is not AI-specific is in when it is the operative instrument for an AI-safety question, such as liability for AI systems, deepfakes or ethics review, with a `scope_note`.
- An instrument with "AI" in its title is in, with a `scope_note` when its content is mainly about something else.
- Company commitments that governments brokered and published are in, with a `scope_note`.
- Out, and only these: documents by companies, think tanks, the press, professional associations or private standard-setters; general privacy, data or cybersecurity laws, and guidance under them that does not deal with AI; strategies with no safety content; supervisory letters to a single firm, speeches, and annual or general supervisory reports that mention AI only in passing; internal administrative circulars.
- A record is never deleted. How to mark an existing record later judged out (a `scope_note` beginning "Out of scope:", or a new field) is open; with the inclusive default it should be rare.

## Supervisory authorities and standards bodies (decided October 2026)

Supervisors set much of the AI governance that regulated firms follow, often in letters and supervisory reports rather than in formal guidelines, and standards bodies write the technical standards that AI legislation relies on. These rules bring both in; the coverage frame has a `supervisors` cell for every national, EU and sub-national jurisdiction and entries for the standards bodies.

- AI-specific guidelines, opinions, supervisory statements and published Q&As of a supervisory authority are in, with no note. Sectoral supervisors (banking, insurance and pensions, securities, health and medicines) and horizontal ones (data protection, equality and anti-discrimination, consumer protection, competition) count alike, at national, EU (EBA, EIOPA, ESMA, EDPB, EDPS, ECB banking supervision) or sub-national level (for example US state insurance regulators). Instrument type: guidelines / framework.
- Guidance by a data protection authority is in when it deals with AI specifically; general data protection guidance stays out.
- A letter, statement or thematic review in which a supervisor states its expectations on AI to a whole sector or the public is in, with a `scope_note` saying what kind of document it is. Instrument type: supervisory statement / letter. A letter to a single firm, a speech, or an annual or general report that mentions AI only in passing is out.
- A report that an authority publishes but an expert group it convened wrote is in, with a `scope_note` naming the expert group; the issuing body is the authority, and the notes say who wrote it.
- European harmonised standards made for AI legislation (CEN-CENELEC JTC 21, ETSI) are in, with no note, and relate to the legislation they serve (the AI Act is EU-03; the standardisation request is EU-09). International ISO/IEC standards on AI are in with a `scope_note` when a law or official guideline cites them. The texts are sold, not published, so the record rests on the standards body's catalogue page.
- Publications of international bodies of supervisors (IAIS, IOSCO, the Basel Committee, the FSB) are intergovernmental instruments: in, with no note, when they deal with AI governance or risk.
- Frameworks by professional associations and private standard-setters (IEEE, OWASP and similar) are out, like documents by companies and think tanks.

*Michael Riegler, 2026-10-14.*

## Institutions and sector-wide rules (decided October 2026)

- AI policies that individual universities, schools, hospitals or other institutions adopt for their own use, public or private, are out: an institution governing itself is like a company's own policy or an internal administrative circular.
- Rules a government body sets for a whole sector are in, with a `scope_note`: for example, a state board's regulation that binds all public universities, or a state education department's rule for all school districts.
- Whether a host counts as official evidence is a separate question (AGENTS.md section 7.6). A body that governs a sector, such as a state university system's board of governors, runs an official host even under `.edu`; marking it official does not bring the universities' own policies into scope.

*Michael Riegler, 2026-10-15.*

## Cases

- **EU Action Plan on Cybersecurity and Artificial Intelligence** (EU-17): in. Its main focus is risks from advanced AI and pre-market model evaluation. *Recorded in the record's notes, October 2026.*
- **EU AI Continent Action Plan, COM(2025) 165, and Apply AI Strategy, COM(2025) 723**: out. Primarily adoption, investment and competitiveness strategies with only high-level references to trustworthy or safe AI. *Recorded in EU-17's notes, October 2026.*
- **EU Product Liability Directive 2024/2853** (EU-05): in, although not AI-specific. It is the EU's operative liability instrument for AI after the AI Liability Directive proposal was withdrawn. *Recorded in the record's notes, October 2026.*
- **Saudi draft Global AI Hub Law** (SA-04): in. Stays in with a scope_note under the include-and-flag rules: the Kingdom's first draft statute with AI in its title, though it mainly governs hosting foreign data in Saudi data centres. *Michael Riegler (issue #2), 2026-10-14.*
