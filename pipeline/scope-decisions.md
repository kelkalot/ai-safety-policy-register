# Scope decisions

Precedents for borderline cases, so that the same kind of instrument gets the same decision in every run. Extractors and checkers apply them; only a human adds a new one, from the `needs-human` items of a run. Each case also goes into `data/history.jsonl` as a `scope-decision` event when it changes a record.

Format: **instrument** (record ID if any): decision. Reason. *Decided by, date.*

## General rules drawn from the cases (proposed; confirm or edit)

- A strategy or action plan is in only when its main content is about AI risks, safety or risk governance; an adoption, investment or competitiveness strategy with general references to "trustworthy AI" is out.
- A law that is not AI-specific is in only when it is the jurisdiction's operative instrument for an AI-safety question (for example liability for AI systems); general privacy, data or cybersecurity laws are out.
- An instrument with "AI" in its title is not in for that reason alone; its content decides.

## Cases

- **EU Action Plan on Cybersecurity and Artificial Intelligence** (EU-17): in. Its main focus is risks from advanced AI and pre-market model evaluation. *Recorded in the record's notes, October 2026.*
- **EU AI Continent Action Plan, COM(2025) 165, and Apply AI Strategy, COM(2025) 723**: out. Primarily adoption, investment and competitiveness strategies with only high-level references to trustworthy or safe AI. *Recorded in EU-17's notes, October 2026.*
- **EU Product Liability Directive 2024/2853** (EU-05): in, although not AI-specific. It is the EU's operative liability instrument for AI after the AI Liability Directive proposal was withdrawn. *Recorded in the record's notes, October 2026.*
- **Saudi Global AI Hub Law, draft** (SA-04): open. The draft concerns hosting foreign data and advanced-technology services in Saudi data centres rather than AI safety rules; it was kept because it is the Kingdom's first draft statute with "AI" in its title. The quality check of 12 October 2026 questioned it against the scope rule that keeps out instruments without safety content. *Needs a human decision.*
