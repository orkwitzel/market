# Git workflow: branches, PRs and merging

`main` is protected. Every change reaches it through a pull request, and the rules below are enforced by GitHub, not by convention.

## Rules on `main`

Defined in [`.github/rulesets/protect-main.json`](../../.github/rulesets/protect-main.json), with no bypass, admins included:

- **No direct pushes.** Changes land only by merging a pull request.
- **No force-pushes and no deletion** of `main`; history stays linear.
- **Squash merge only.** Each PR becomes one commit on `main`, titled with the PR title. Merge commits and rebase merges are turned off.
- **Required check:** the `branch-name` CI job must pass before merging.
- **Head branches are deleted automatically** once their PR is merged.

## Branch naming

```
<type>/<short-kebab-description>
```

- `type` is one of `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`.
- The description uses lowercase letters, digits and single hyphens only. Start it with the issue number when there is one.
- Examples: `feat/12-trading-clock`, `fix/margin-call-rounding`, `docs/adr-0010-overlays`.
- Claude Code sessions use `claude/<slug>` (the harness picks the name). `dependabot/` and `renovate/` branches are allowed as-is.

The rule lives in [`scripts/check-branch-name.sh`](../../scripts/check-branch-name.sh); CI runs it on every pull request ([`.github/workflows/branch-name.yml`](../../.github/workflows/branch-name.yml)). Check before pushing:

```sh
scripts/check-branch-name.sh            # current branch
scripts/check-branch-name.sh feat/x     # any name
```

A PR from a badly named branch can never merge: rename the branch (`git branch -m <new-name>`), push it, and open a new PR. A PR's head branch can't be renamed in place.

## For agents

- Never push to `main`, and never try to work around the ruleset (no force-push, no admin bypass, no editing the ruleset to get a change in).
- Branch off the latest `main` with a name that passes the check, open a PR, and let it be squash-merged.
- Write the PR title as the final commit message: it becomes the commit on `main`.
- After a merge the remote branch is gone. Start follow-up work on a fresh branch from `main`; don't reuse the merged one.

## Changing the settings

Edit the ruleset JSON or the script, then have a repo admin run:

```sh
scripts/apply-repo-settings.sh          # needs gh logged in as an admin
```

It sets the merge options (squash only, `PR_TITLE` / `PR_BODY` as the squash commit, delete branch on merge) and creates or updates the `protect-main` ruleset. It is safe to re-run. If you rename the `branch-name` job, update the ruleset's required check in the same PR.
