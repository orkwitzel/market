# 1. Point-in-time S&P 500 universe

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The bot must trade "without knowing the future". The easiest place for the future to leak in is the choice of stocks: a hand-picked list (NVDA, AAPL, AMZN…) or today's index members only contains companies that survived and won. Strategies that rank or select from the universe, momentum rotation especially, look brilliant when no stock in the universe ever collapses (survivorship bias).

## Decision

- The universe on each simulated date is the S&P 500 **as it was on that date** (point-in-time membership), including companies later delisted, acquired or bankrupt.
- v1 offers no per-stock include/exclude, no custom ticker lists and no tradable ETFs. SPY is used only as the benchmark.
- When a held stock leaves the index, the engine closes the position at the next open (**forced exit**), mirroring an index fund.
- When a stock joins, it is tradable from its addition date; its earlier price history counts as visible past.
- A run may only start where **coverage** (members with usable price data) is at least the configurable threshold, 85% by default. Coverage is shown in every report.

## Consequences

- We need point-in-time membership data and price data for dead companies (see ADR 0007).
- Forced exits sometimes sell at bad moments (the index "deletion effect"); this is realistic and visible in the event feed.
- Data needs are bounded: prices are only required while a stock is a member, plus one day.

## Alternatives considered

- **User-supplied ticker list:** simplest, but bakes in hindsight. May return later as an explicitly labelled "biased" mode.
- **Exit-only after removal** (hold but never add): more natural for some strategies, but needs open-ended post-removal data and exit-only logic everywhere. Possible later config option.
