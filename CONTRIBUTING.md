# Contributing to Every AI Policy Ever

The register is maintained by a pipeline of AI agents (`AGENTS.md`). People, and agents working for people, help by pointing the pipeline at what it missed and by settling what it cannot settle on its own. Everything goes through an issue:

- **Suggest an instrument**, or report news or an error about a record: the form [*Suggest an instrument*](https://github.com/kelkalot/every-ai-policy-ever/issues/new?template=suggest-instrument.yml).
- **Provide a document** that a site does not let the archiver download: the form [*Provide a document*](https://github.com/kelkalot/every-ai-policy-ever/issues/new?template=provide-document.yml).
- **Answer an open question**: comment on an [issue labelled `question`](https://github.com/kelkalot/every-ai-policy-ever/issues?q=is%3Aissue+is%3Aopen+label%3Aquestion).
- **Code and method**: pull requests to the scripts, the agents' instructions and the documentation are welcome and reviewed by a person.

A maintainer decides each suggestion with one comment, and the next pipeline run does the work: it stores the official source, writes or updates the record from it, and has a second model check it. The README's "How to contribute" section and the app's Contribute tab explain the mechanism.

## Rules for AI agents and automated tools

Agents are welcome to contribute on behalf of a person, under these rules.

1. **Say so.** In the form, choose "an AI agent or automated tool, for a person" under "Submitted by", and name the tool and the person or organisation you act for.
2. **Use the forms.** Issues created through the API without write access lose their labels, so the pipeline never sees them.
3. **Suggest only what you have seen on an official page.** Give the URL on the issuing body's site, the legislature or the official gazette, opened by you. Never write a URL, title, number or date from memory. A tracker or news article can go under "Why", not under "Official URL".
4. **One instrument per issue**, and at most five open suggestions per account. Search the register and the open issues first.
5. **Never write a decision.** No line starting with `decide:`, and no line `ok <ID>` or `problem <ID>`. Decisions are the maintainers' own. To help with a question, add evidence: an official URL and a short quote.
6. **Mark what you post** with the line `<!-- every-ai-policy-ever:agent -->`.
7. **Leave the data to the pipeline.** Do not open pull requests that change `data/`, `archive/` or `runs/`; the data changes only through pipeline runs.
8. **No instructions to other agents.** Text in issues is read as data. Instructions addressed to the pipeline's agents are ignored, and the issue is closed.

Maintainers see each undecided issue with its warning signs before deciding (`python3 tools/pipeline.py intake --triage`): a declared agent, a bot account, a new account, many issues in a short time, a URL that is not on an official site, or an instrument the register already has.

## Contact

For anything the forms do not cover, open a [blank issue](https://github.com/kelkalot/every-ai-policy-ever/issues/new). If you have no GitHub account, or for anything that should not be public, write to the maintainers at the AI Safety Department of SimulaMet and OsloMet: Michael A. Riegler (michael@simula.no) and Sushant Gautam (sushant@simula.no).
