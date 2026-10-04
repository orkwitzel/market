# 3. Step-by-step engine with a time-gated data window and a look-ahead test

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

Vectorized backtests (compute every indicator for all history at once, then align signals) are fast but leak the future silently: one misaligned line and results just look a bit too good. "Without knowing the future" is the project's core rule, so it must be guaranteed structurally and proven by a test.

## Decision

- The engine is **event-driven and steps one trading day at a time**.
- Each day, strategies, the allocator and overlays read market data only through the **data window**, which cannot return anything after the as-of date.
- Decisions are made after the day's close; orders fill at the next day's open.
- An automated **look-ahead test** runs on every strategy, allocator and overlay: simulate to a cutoff date, delete all data after the cutoff, re-run, and require identical decisions up to the cutoff. It runs in CI on synthetic data.
- Runs are deterministic.

## Consequences

- Runs take minutes rather than seconds; the web app shows a progress bar.
- If speed becomes a problem, indicator computation can move to a precomputed-but-gated **hybrid** without changing strategy code, because strategies only ever see the data window.
- The look-ahead test is the project's proof of honesty and must never be skipped.

## Alternatives considered

- **Vectorized:** 10–100× faster, unacceptable leak risk.
- **Hybrid (precomputed indicators behind the gated window):** recommended at the time; deferred as a possible optimization.
