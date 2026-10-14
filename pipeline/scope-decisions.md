# Scope decisions

Precedents for borderline cases, so that the same kind of instrument gets the same decision in every run. Extractors and checkers apply them; only a human adds a new one, from the `needs-human` items of a run. Each case also goes into `data/history.jsonl` as a `scope-decision` event when it changes a record.

Format: **instrument** (record ID if any): decision. Reason. *Decided by, date.*

## General rules (decided in issue #2, October 2026)

The register is inclusive: borderline instruments are included and flagged with a `scope_note` instead of being left out.

- A strategy or action plan with some safety or risk-governance content is in. When safety is not its main content, it gets a `scope_note`.
- A law that is not AI-specific is in when it is the operative instrument for an AI-safety question, such as liability for AI systems, deepfakes or ethics review, with a `scope_note`.
- An instrument with "AI" in its title is in, with a `scope_note` when its content is mainly about something else.
- Company commitments that governments brokered and published are in, with a `scope_note`.
- Out, and only these: documents by companies, think tanks or the press; general privacy, data or cybersecurity laws; strategies with no safety content; minor sectoral circulars.
- A record is never deleted. How to mark an existing record later judged out (a `scope_note` beginning "Out of scope:", or a new field) is open; with the inclusive default it should be rare.

## Cases

- **EU Action Plan on Cybersecurity and Artificial Intelligence** (EU-17): in. Its main focus is risks from advanced AI and pre-market model evaluation. *Recorded in the record's notes, October 2026.*
- **EU AI Continent Action Plan, COM(2025) 165, and Apply AI Strategy, COM(2025) 723**: out. Primarily adoption, investment and competitiveness strategies with only high-level references to trustworthy or safe AI. *Recorded in EU-17's notes, October 2026.*
- **EU Product Liability Directive 2024/2853** (EU-05): in, although not AI-specific. It is the EU's operative liability instrument for AI after the AI Liability Directive proposal was withdrawn. *Recorded in the record's notes, October 2026.*
- **Saudi draft Global AI Hub Law** (SA-04): in. Stays in with a scope_note under the include-and-flag rules: the Kingdom's first draft statute with AI in its title, though it mainly governs hosting foreign data in Saudi data centres. *Michael Riegler (issue #2), 2026-10-14.*
