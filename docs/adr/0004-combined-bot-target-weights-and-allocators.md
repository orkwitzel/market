# 4. A combined bot: target weights, shadow portfolios, sleeves and allocators

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The bot uses existing, classic trading algorithms. Rather than one strategy per run or a side-by-side race, the user wants a single bot with one account that holds a toolbox of strategies and decides how far to trust each one over time. Research into multi-strategy practice (CTAs, pod shops, the 1/N literature, risk parity, factor momentum) favoured weighting by risk, with only modest performance tilts.

## Decision

- **Strategies output target weights** (fractions of capital per stock; negative = short). They never handle shares, cash or orders. Stops become "target 0, exit at next open".
- Each strategy has a **family** tag: market, trend, mean reversion, rotation, relative value.
- Each strategy keeps a **shadow portfolio** (its stand-alone paper track record), which is the allocator's only evidence and the basis for attribution.
- **Virtual sleeves, netted execution:** the combined target is Σ sleeve × strategy weights; the account trades only the net, so opposing views cancel instead of paying costs twice. Costs are attributed back to strategies pro rata.
- The **allocator** reallocates monthly using shadow results through the previous day; it starts from an equal split during warm-up. v1 ships:
  1. **Equal split (1/N)**: the baseline.
  2. **Risk parity**: inverse volatility of shadow returns, equal risk per family first, then per strategy.
  3. **Risk parity + trust tilt** (default): risk-parity sleeves tilted by trailing 6–12-month risk-adjusted shadow return, floor 0.25×, cap 2×.
- The allocator is selectable in the run config. Allocators are pluggable.
- v1 toolbox: equal-weight hold (market), SMA 50/200 crossover (trend), Donchian/Turtle breakout with ATR stop (trend), RSI-2 pullback with 200-day filter (mean reversion), cross-sectional 12-1 momentum top N (rotation), short-term reversal long/short (relative value). Parameters are configurable with textbook defaults.

## Consequences

- Strategies stay small and easy to read; combining them is a weighted average.
- Attribution between strategies is approximate under netting; it is computed from sleeves and shadows.
- Next additions: online learning (multiplicative weights / exponentiated gradient) allocator; pairs trading, time-series momentum, Bollinger and MACD strategies.

## Alternatives considered

- **One strategy per run / strategy race:** simpler, less interesting. The race may still appear later via run comparison.
- **Orders instead of target weights:** finer control (intraday stops, limits) but awkward to combine.
- **Mean-variance / Kelly allocation:** estimation error makes them fragile; possible later as a teaching example.
