#!/usr/bin/env bash
# Set up the application in the current checkout (the main one or a worktree): link the
# shared local data and secrets from the main checkout, install the Python environment and
# the frontend dependencies. Steps whose project files don't exist yet are skipped.
# Safe to re-run. See docs/agents/worktrees.md.
# Usage: scripts/setup.sh
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
main_root="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
cd "$root"

# Gitignored local state lives once, in the main checkout. Link it into worktrees so they
# share the data store and API keys instead of re-downloading or copying secrets around.
if [[ "$root" != "$main_root" ]]; then
  for path in data .env; do
    if [[ -e "$main_root/$path" && ! -e "$path" && ! -L "$path" ]]; then
      ln -s "$main_root/$path" "$path"
      echo "linked $path -> $main_root/$path"
    fi
  done
fi
if [[ ! -e .env ]]; then
  echo "note: no .env; copy .env.example to .env in $main_root and fill in the API keys"
fi

if [[ -f pyproject.toml ]]; then
  if ! command -v uv >/dev/null; then
    echo "error: uv is not installed; see https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
  uv sync
fi

if [[ -f web/package.json ]]; then
  if ! command -v npm >/dev/null; then
    echo "error: npm is not installed; install Node.js to build the frontend" >&2
    exit 1
  fi
  if [[ -f web/package-lock.json ]]; then
    npm ci --prefix web
  else
    npm install --prefix web
  fi
fi

echo "ok: $root is set up"
