# 9. Build layer by layer, starting with a data spike

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

v1 is large. Building in thin end-to-end slices was considered; the owner chose to complete each layer before starting the next.

## Decision

Build in this order, each layer as a GitHub milestone with its own issues:

0. **Foundations:** data spike (verify ADR 0007's sources) and project scaffolding with CI.
1. **Data:** membership, prices, corporate events, rates, benchmark, coverage.
2. **Engine:** clock, data window, account, fills, recording, look-ahead test, cost model, trading band, corporate events, universe changes, shorts, margin and interest.
3. **Strategies:** indicator module, strategy interface, the six v1 strategies.
4. **Allocators:** shadow portfolios, warm-up, sleeves, the three allocators.
5. **Overlays:** volatility targeting, drawdown brake.
6. **Report:** all report calculations, with a text summary from the CLI so engine results can be checked before any UI exists.
7. **Web app:** API, worker, run history, React frontend, replay and report screens.

## Consequences

- Nothing is visible in a browser until layer 7; the CLI summary (layer 6) is the first human-readable output, and tests are the main feedback before that.
- Interface mismatches between layers can surface late; keep the recording format and the data window interface explicit and documented to reduce that risk.
