# market: guide for coding agents

A historical trading simulator. A **bot** is dropped into the past with cash and trades real daily S&P 500 data one simulated day at a time, up to the present, without ever seeing the future. Read [`README.md`](README.md) for the overview, [`CONTEXT.md`](CONTEXT.md) for the vocabulary, and [`docs/adr/`](docs/adr/) for the decisions behind the design.

## Ground rules

These protect the project's core value: an honest simulation. Do not weaken them without a new ADR.

1. **No look-ahead.** Strategy, allocator and overlay code reads market data *only* through the time-gated data window. Never index into raw arrays or dataframes by future dates, never use the day's close to fill that day's order, and never precompute anything with information past the as-of date. The look-ahead test must pass for every strategy, allocator and overlay. (ADR 0003)
2. **Raw prices for trading.** Fills use raw prices; strategies see as-of adjusted history. Never use back-adjusted series in the engine. (ADR 0002)
3. **Point-in-time universe.** The bot may only hold stocks that are S&P 500 members on the as-of date. Never hard-code or filter tickers with knowledge of their future. (ADR 0001)
4. **No data in git.** Never commit market data, run recordings, API keys or `.env`. Tests and CI use small synthetic fixtures generated in code. Data source licenses forbid redistribution. (ADR 0007)
5. **Determinism.** The same run config and data snapshot must give identical results. No unseeded randomness, no dependence on wall-clock time or dict/set iteration order.
6. **Use the glossary.** Name things with the terms in `CONTEXT.md` (bot, toolbox, allocator, shadow portfolio, sleeve, overlay, drop date, data window…). Avoid "agent" for the bot.
7. **Layer order.** v1 is built layer by layer (ADR 0009); each layer is a GitHub milestone. Don't start work in a later layer before its prerequisites are closed unless the issue says otherwise.

## Stack

- **Backend:** Python 3.14, uv, FastAPI, Typer, Polars (data), NumPy (engine core), SQLite (run index), Parquet (data store and recordings).
- **Frontend:** React + TypeScript (Vite), Tailwind + shadcn/ui, lightweight-charts, ECharts, in `web/`.
- **Quality:** pytest, ruff (lint + format), pyright.

## Planned layout

The layout may evolve; update this section when it does.

```
src/market/
  data/         membership, prices, corporate events, rates, coverage, data window
  engine/       clock, account, fills, cost model, trading band, margin, recording
  strategies/   indicator module + the v1 toolbox
  allocators/   shadow portfolios, sleeves, allocators
  overlays/     volatility targeting, drawdown brake
  report/       metrics and the CLI summary
  api/          FastAPI app, run worker, run history
  cli.py        `market run | serve | data update`
web/            React frontend
tests/          pytest suite (synthetic data only), incl. the look-ahead test
docs/adr/       architecture decision records
scripts/        repo tooling (branch-name check, GitHub settings)
.github/        CI workflows and the main-branch ruleset
```

## Commands (once scaffolding lands)

```sh
uv sync                      # install
uv run pytest                # tests, including the look-ahead test
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run market --help         # CLI
```

## Decisions

Record significant or hard-to-reverse decisions as a new ADR in `docs/adr/` (next number, same format). If a change contradicts an existing ADR, say so explicitly and propose superseding it rather than silently diverging.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default labels, unchanged: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Git workflow

`main` is protected: changes land only through a squash-merged pull request, and branch names must follow `<type>/<short-kebab-description>` (Claude Code sessions use `claude/<slug>`), checked in CI by `scripts/check-branch-name.sh`. See `docs/agents/git-workflow.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
