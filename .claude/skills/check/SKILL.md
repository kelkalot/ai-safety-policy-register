---
name: check
description: Check a pipeline run's extracted records against their stored sources, field by field, in a fresh context. Use for the check stage, including a cross-tool check.
---

You are the checker for one pipeline run. If you took part in collecting or extracting this run, stop and say the check needs a fresh session.

Read `pipeline/roles/check.md` and follow it exactly; AGENTS.md is the contract it builds on. In a compare run (`run.json` has type `compare`), follow `pipeline/roles/compare.md` instead. The arguments are the words the user wrote after the skill name.
