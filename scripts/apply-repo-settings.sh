#!/usr/bin/env bash
# Apply the repo's GitHub settings: squash-only merges, delete head branches after merge,
# and the protect-main ruleset (.github/rulesets/protect-main.json). Safe to re-run.
# Needs the gh CLI logged in as a repo admin.
# Usage: scripts/apply-repo-settings.sh [owner/repo]
set -euo pipefail

repo="${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
ruleset_file="$(dirname "$0")/../.github/rulesets/protect-main.json"
ruleset_name="$(jq -r .name "$ruleset_file")"

echo "Updating merge settings on $repo"
gh api --method PATCH "repos/$repo" --silent \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY

existing_id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == \"$ruleset_name\") | .id")"
if [[ -n "$existing_id" ]]; then
  echo "Updating ruleset '$ruleset_name' (id $existing_id)"
  gh api --method PUT "repos/$repo/rulesets/$existing_id" --input "$ruleset_file" --silent
else
  echo "Creating ruleset '$ruleset_name'"
  gh api --method POST "repos/$repo/rulesets" --input "$ruleset_file" --silent
fi

echo "Done."
