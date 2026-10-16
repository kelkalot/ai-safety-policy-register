#!/usr/bin/env python3
"""Claude Code hook before every Bash command (AGENTS.md section 4, rule 12).

Before `git commit` or `git push`, when the working tree changes the official data compared with origin/main
(data/records.json, data/history.jsonl, data/definitions.json or the decision files in pipeline/), it runs
tools/gate.py and stops the command when the gate fails. Exit code 2 stops the command and shows the message to the
agent. Every other command passes untouched.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GIT_WRITE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:commit|push)\b")
OFFICIAL = ["data/records.json", "data/history.jsonl", "data/definitions.json", "pipeline/official-sites.json",
            "pipeline/frame.json", "pipeline/leads.json", "pipeline/questions.json", "pipeline/scope-decisions.md"]


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if data.get("tool_name") != "Bash" or not GIT_WRITE.search(cmd):
        return 0
    base = subprocess.run(["git", "-C", str(ROOT), "merge-base", "HEAD", "origin/main"], capture_output=True, text=True)
    if base.returncode:
        return 0  # no origin/main to compare with: nothing official to protect here
    touched = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", base.stdout.strip(), "--"] + OFFICIAL,
                             capture_output=True, text=True).stdout.split()
    if not touched:
        return 0
    res = subprocess.run([sys.executable, str(ROOT / "tools" / "gate.py"), "--quiet"], capture_output=True, text=True,
                         cwd=str(ROOT))
    if res.returncode == 0:
        return 0
    sys.stderr.write("Stopped: this commit or push changes the official data (%s), and the gate failed:\n\n%s\n%s\n"
                     "Fix what it reports (AGENTS.md section 7.10), then commit again. A hand edit to the data goes "
                     "through the tools that write it and log it.\n" % (", ".join(touched), res.stdout[-3000:],
                                                                        res.stderr[-1000:]))
    return 2


if __name__ == "__main__":
    sys.exit(main())
