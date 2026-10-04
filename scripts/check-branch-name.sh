#!/usr/bin/env bash
# Check a branch name against the repo's naming rule (docs/agents/git-workflow.md).
# Usage: scripts/check-branch-name.sh [branch]   (defaults to the current branch)
# This is the single source of truth for the rule; CI runs it on every pull request.
set -euo pipefail

branch="${1:-$(git rev-parse --abbrev-ref HEAD)}"

slug='[a-z0-9]+(-[a-z0-9]+)*'
types='feat|fix|docs|refactor|test|chore|ci|perf|build'
pattern="^((${types})/${slug}|claude/${slug}|(dependabot|renovate)/.+)$"

if [[ "$branch" =~ $pattern ]]; then
  echo "ok: branch name '$branch' follows the naming rule"
  exit 0
fi

cat >&2 <<MSG
error: branch name '$branch' does not follow the naming rule.

Use <type>/<short-kebab-description>, lowercase letters, digits and single hyphens only:
  type: ${types//|/, }
  e.g.  feat/12-trading-clock, fix/margin-call-rounding, docs/adr-0010-overlays

Claude Code sessions use claude/<slug>; dependabot/ and renovate/ branches are allowed as-is.
Rename with: git branch -m <new-name>   (then push it and open a new PR)
MSG
exit 1
