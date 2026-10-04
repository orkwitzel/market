# Worktrees: one per task

Every task runs in its own [git worktree](https://git-scm.com/docs/git-worktree) under `.claude/worktrees/`, never directly in the main checkout. Several sessions can then work in parallel without switching each other's branches, mixing uncommitted changes or rebuilding each other's environments, and the main checkout stays on `main` as the place local data and secrets live.

## Starting a task

```sh
scripts/new-worktree.sh feat/12-trading-clock     # branch name must pass scripts/check-branch-name.sh
cd .claude/worktrees/feat-12-trading-clock
```

[`scripts/new-worktree.sh`](../../scripts/new-worktree.sh) fetches `origin`, creates the branch from the latest `origin/main` (pass a second argument for another base), adds the worktree at `.claude/worktrees/<branch with / replaced by ->` and runs the setup script in it.

If the Claude Code harness created the worktree for you (`claude --worktree`, or entering a worktree mid-session), it already lives in `.claude/worktrees/`: check the branch name, then run `scripts/setup.sh` in it before doing anything else.

## The setup script

[`scripts/setup.sh`](../../scripts/setup.sh) sets the application up in whatever checkout it runs in. It is safe to re-run, so run it again after pulling changes to dependencies.

- **Shared local state.** Symlinks `data/` (the market data store) and `.env` (API keys) from the main checkout, when they exist there, so worktrees neither re-download data nor copy secrets around. Both stay gitignored; never commit them (ground rule 4). `runs/` is not shared: each worktree keeps its own recordings.
- **Python.** `uv sync`, once `pyproject.toml` exists.
- **Frontend.** `npm ci` in `web/` (or `npm install` before there is a lockfile), once `web/package.json` exists.

When setup gains a step (a new tool, a generated file, a database migration), add it to `scripts/setup.sh` in the same PR, so every new worktree keeps working with no manual steps.

## Rules for agents

- Do all edits, commands and commits from inside the task's worktree. Don't `cd` back to the main checkout, and never commit there.
- Only touch the shared `data/` through the app (`market data update`); a worktree writes to the same store as every other checkout.
- The git stash is shared by all worktrees. Set work aside with a WIP commit on your branch, not `git stash`.
- One branch per worktree; git refuses to check out a branch that is already checked out in another one.

## Cleaning up

After the PR is merged:

```sh
git worktree remove .claude/worktrees/feat-12-trading-clock
git branch -D feat/12-trading-clock      # squash merges leave the branch looking unmerged
git worktree prune                       # drop records of worktree folders deleted by hand
```
