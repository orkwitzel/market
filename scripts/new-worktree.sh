#!/usr/bin/env bash
# Create a worktree for a task under .claude/worktrees/, on a new branch from the latest
# origin/main (or another base), and set the application up in it. See docs/agents/worktrees.md.
# Usage: scripts/new-worktree.sh <branch> [base]   e.g. scripts/new-worktree.sh feat/12-trading-clock
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: scripts/new-worktree.sh <branch> [base]   (base defaults to origin/main)" >&2
  exit 2
fi
branch="$1"
base="${2:-origin/main}"

main_root="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
"$main_root/scripts/check-branch-name.sh" "$branch"

dir="$main_root/.claude/worktrees/${branch//\//-}"
if [[ -e "$dir" ]]; then
  echo "error: $dir already exists" >&2
  exit 1
fi

git -C "$main_root" fetch --quiet origin
git -C "$main_root" worktree add --no-track -b "$branch" "$dir" "$base"
cd "$dir"
if [[ -x scripts/setup.sh ]]; then
  scripts/setup.sh
else
  "$main_root/scripts/setup.sh"   # base predates the setup script
fi

echo "worktree ready: $dir"
