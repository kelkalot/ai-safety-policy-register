#!/usr/bin/env python3
"""Claude Code hook before every Bash command (AGENTS.md section 4, rule 11).

Agents may open, comment on and close GitHub issues; the pipeline depends on it. Two things are stopped:
a post that contains a maintainer's decision line (the lines `tools/pipeline.py` reads as decisions), and a
post without the agent marker, which the scripts use to tell agents' comments from maintainers'.
The scripts' own posts go through `tools/pipeline.py`, which adds the marker itself, so they never reach this hook
as a `gh` command. Exit code 2 stops the command and shows the message to the agent.
"""
import json
import os
import re
import sys

MARK = "every-ai-policy-ever:agent"
POSTS = re.compile(r"\bgh\s+(?:issue|pr)\s+(?:create|comment|close|edit|review)\b|\bgh\s+api\b.*\b(?:issues|pulls)\b",
                   re.S)
WRITES = re.compile(r"\bgh\s+(?:issue|pr)\s+(?:create|comment|review)\b|\bgh\s+api\b.*\bcomments\b", re.S)
# the same lines tools/pipeline.py parse_decisions reads: "decide: ..." and sample lines "ok <ID>" / "problem <ID>"
DECISION = re.compile(r"(?im)^\s*decide\s*:|^\s*(?:ok|problem)\s+[A-Z]{2,5}(?:-[A-Z]{2,3})?-\d+\b")


def body_files(cmd):
    """Text of files a gh command posts from: --body-file PATH, -F PATH, body=@PATH."""
    out = []
    for m in re.finditer(r"(?:--body-file|-F)\s+(\"[^\"]+\"|'[^']+'|\S+)|body=@(\S+)", cmd):
        path = (m.group(1) or m.group(2) or "").strip("'\"")
        if path and path != "-" and os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                out.append(fh.read())
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if data.get("tool_name") != "Bash" or not POSTS.search(cmd):
        return 0
    # an inline body starts a new line, so that a decision on its first line is seen as one
    inline = re.sub(r"(?:(?<=\s)(?:--body|--comment|-b)(?:\s+|=)|\bbody=)['\"]?", "\n", cmd)
    text = "\n".join([inline] + body_files(cmd))
    if DECISION.search(text):
        sys.stderr.write(
            "Stopped: this GitHub post contains a decision line (a line starting with `decide:`, or `ok <ID>` / "
            "`problem <ID>`). Decisions are the maintainers' own; an agent never writes one (AGENTS.md section 4, "
            "rule 11). Post without that line, or quote the syntax inside a sentence, and leave the decision to a "
            "maintainer.\n")
        return 2
    if WRITES.search(cmd) and MARK not in text:
        sys.stderr.write(
            "Stopped: add the line `<!-- every-ai-policy-ever:agent -->` to the body of anything an agent posts on "
            "GitHub (AGENTS.md section 4, rule 11), so that it is never read as a maintainer's decision.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
