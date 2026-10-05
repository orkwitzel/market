#!/usr/bin/env python3
"""Check a pull request body against .github/pull_request_template.md.

The required sections must be present and contain more than template comments.
Usage: PR_BODY="..." scripts/check-pr-body.py   (or pipe the body on stdin)
CI runs this on every pull request; see docs/agents/git-workflow.md.
"""

import os
import re
import sys

REQUIRED_SECTIONS = ("Summary", "Testing")


def section_text(body: str, heading: str) -> str | None:
    match = re.search(rf"^##[ \t]+{re.escape(heading)}[ \t]*$", body, re.MULTILINE)
    if match is None:
        return None
    rest = body[match.end() :]
    next_heading = re.search(r"^##[ \t]", rest, re.MULTILINE)
    text = rest[: next_heading.start()] if next_heading else rest
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def main() -> int:
    body = os.environ.get("PR_BODY")
    if body is None:
        body = sys.stdin.read()
    body = body.replace("\r\n", "\n")

    problems = []
    for heading in REQUIRED_SECTIONS:
        text = section_text(body, heading)
        if text is None:
            problems.append(f"missing the '## {heading}' section")
        elif not text:
            problems.append(f"the '## {heading}' section is empty")

    if problems:
        print(
            "error: the PR body does not follow .github/pull_request_template.md:", file=sys.stderr
        )
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("Edit the PR description; this check re-runs automatically.", file=sys.stderr)
        return 1
    print("ok: PR body has the required sections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
