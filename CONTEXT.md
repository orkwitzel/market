# Context: market

A historical trading simulator. A **bot** is dropped into the past with cash and trades real daily market data, one simulated day at a time, up to the present — without ever seeing the future. It is a learning project first; honesty of the simulation (no look-ahead, no survivorship bias, realistic frictions) is the core value.

Decisions behind these terms live in [`docs/adr/`](docs/adr/).

## Glossary

### Runs and time

- **Run** — one simulation of the bot from its drop date to its end date, defined by a run config. Runs are deterministic: the same run config on the same data snapshot gives identical results. Every run is saved to the run history.
- **Run config** — the settings of a run: drop date, end date, starting cash, toolbox, allocator, overlays and their parameters, cost mode, warm-up length, coverage threshold, trading band. Written as YAML (CLI) or filled in through the web form.
- **Drop date** — the simulated date on which the bot starts trading real (simulated) money. _Avoid_: "start date" when the warm-up matters.
- **Warm-up** — the period before the drop date (default 12 months) during which shadow portfolios run so the allocator has a track record on day one. No real money moves during warm-up.
- **End date** — the last simulated day of a run. Defaults to the latest day in the data.
- **As-of date** — the current simulated day. Everything the bot does on a day may use only information available at that day's close.
- **Data window** — the time-gated view of market data handed to strategies, the allocator and overlays. It physically cannot return anything after the as-of date.
- **Look-ahead** — any use of information from after the as-of date. Always a bug.
- **Look-ahead test** — the automated check that proves no look-ahead: run to some date, delete all data after it, run again, and require every decision up to that date to be identical.

### Universe and data

- **Universe** — the stocks the bot may trade on a given date: the members of the S&P 500 on that date (point-in-time membership) that have price data. ETFs are not in the universe.
- **Security** — one company's listed stock, identified by a stable security id that never changes. A ticker is only a label for a period: a security can change ticker, and a reused ticker belongs to two different securities. _Avoid_: using the ticker as an identifier.
- **Point-in-time membership** — index membership as it actually was on each historical date, including companies that later went bankrupt, were acquired or were removed.
- **Survivorship bias** — the distortion caused by only looking at companies that survived to today. The point-in-time universe exists to avoid it.
- **Coverage** — the share of index members on a date that have usable price data. A run may only have a drop date where coverage (through the warm-up) is at least the **coverage threshold** (default 85%).
- **Raw prices** — prices as they actually traded on the day, not rewritten for later splits or dividends. Fills always happen at raw prices.
- **Corporate event** — a split or dividend. Applied by the engine on the day it happens.
- **As-of adjusted history** — price history adjusted only for corporate events that happened on or before the as-of date. This is what strategies see. _Avoid_: "adjusted prices" (which usually means adjusted as of today and leaks the future).
- **Forced exit** — closing a position at the next open because its stock left the universe.
- **Settlement** — closing a position at its last traded price because the stock's data ended (delisting, buyout, bankruptcy).
- **Data snapshot** — an identifier of the exact data a run used, recorded with the run.

### The bot

- **Bot** — the simulated trader: one account, a toolbox of strategies, an allocator, and overlays. _Avoid_: "agent" (reserved in this repo for AI coding agents).
- **Strategy** — a classic rule-based trading algorithm. Each day it reads the data window and returns target weights. Every strategy belongs to one strategy family.
- **Strategy family** — the style group a strategy belongs to: _market_, _trend_, _mean reversion_, _rotation_, _relative value_. Used by risk-parity allocation.
- **Toolbox** — the set of strategies included in a run. The user includes or excludes strategies; that is the only universe-related choice in v1.
- **Target weights** — what a strategy (or the whole bot) would like to hold, as fractions of capital per stock. Negative means short; a sum of absolute weights above 1 means leverage. Stops are expressed as a target weight of 0 (exit at next open).
- **Shadow portfolio** — the paper track record of one strategy, as if it managed money alone. Built only from the past; the allocator's only evidence.
- **Sleeve** — the share of the bot's capital assigned to one strategy. Sleeves are virtual: the account trades only the netted combined target.
- **Allocator** — decides sleeve sizes once a month, using shadow portfolios through the previous day. v1 allocators: _equal split_, _risk parity_ (equal risk per strategy family, then per strategy), and _risk parity + trust tilt_ (the default).
- **Trust tilt** — nudging risk-parity sleeves toward strategies with better recent risk-adjusted shadow returns, bounded by a floor (0.25×) and a cap (2×).
- **Combined target** — the sum over strategies of sleeve × target weights, after overlays. The only thing the engine trades toward.
- **Overlay** — a risk control that scales the bot's total exposure after allocation. v1 overlays: _volatility targeting_ (on by default, 12% target, 1.5× leverage cap) and _drawdown brake_ (off by default). Overlays form a chain.

### Trading and accounting

- **Fill** — execution of a trade, always at the next trading day's open, at the raw price plus costs.
- **Trading band** — the tolerance below which drifts from the combined target are ignored (25% of a position's target or 1% of the portfolio, whichever is larger). Exits, new positions and margin-call liquidations always trade.
- **Minimum trade** — trades smaller than 0.5% of the account are skipped.
- **Cost model** — commissions, spread/slippage and the whole-share rule as a function of date. _Era-accurate_ by default; a _modern costs_ switch applies today's frictions to every date.
- **Margin call** — forced proportional liquidation at the next open when equity falls below the maintenance requirement (25% of long value, 30% of short value).
- **Gross exposure / net exposure** — sum of absolute position values / longs minus shorts, as a fraction of equity.
- **Tracking gap** — how far the actual holdings were from the combined target, on average, because of share rounding, minimum trades and the trading band.
- **Pre-tax** — all results ignore taxes. Positions still record their open dates so tax lots can be added later.

### Results

- **Benchmark** — SPY bought and held with dividends reinvested. Shown on every chart and table; never traded by the bot.
- **Cash line** — what the starting cash would have earned at the historical cash interest rate.
- **Recording** — everything the engine writes about a run, day by day (prices seen, targets, sleeves, fills, events, portfolio state), stored as Parquet. The viewer replays it; it never re-runs the simulation.
- **Event feed** — the explained log of a run: trades, reallocations, overlay actions, corporate events, forced exits, settlements and margin calls, each with a plain-language reason.
- **Report** — the end-of-run verdict: returns and risk, comparison with the benchmark and cash line, cost leakage, per-strategy attribution, year-by-year table, "was it luck?" check, tracking gap and coverage.

## Invariants

1. Nothing in strategy, allocator or overlay code reads market data except through the data window.
2. The engine never trades at back-adjusted prices.
3. Market data, run recordings and API keys are never committed to the repository; tests use synthetic data.
4. A run that would violate the coverage threshold, Reg T leverage limit or the run config's capabilities is rejected or constrained by the engine, never silently allowed.
