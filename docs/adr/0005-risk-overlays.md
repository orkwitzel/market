# 5. Risk overlays: volatility targeting on, drawdown brake off

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The allocator decides how to split capital between strategies, not how much total risk the bot takes. Professional practice adds portfolio-level risk controls on top of any allocation.

## Decision

- After allocation, a chain of **overlays** scales the bot's total exposure before the engine trades. The engine's hard limits (Reg T, margin) still apply afterwards.
- **Volatility targeting**, on by default: scale exposure toward a 12% annualized volatility target, estimated from roughly the last two months, with a 1.5× leverage cap. This is how the bot normally uses margin.
- **Drawdown brake**, built but off by default: cut exposure after configurable drawdowns (e.g. −10% → half, −20% → quarter), restoring after partial recovery or a cooling-off period.
- Both are configurable per run; overlays are pluggable.

## Consequences

- Volatility targeting reacts after shocks start, not before; the replay shows this.
- The drawdown brake tends to sell near bottoms (e.g. March 2020), which is why it is off by default; turning it on is an intended experiment.
- Later overlays, such as a market-trend filter, plug into the same chain.
