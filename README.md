# market

**Drop a trading bot into the past with cash, and watch it trade real market history, one day at a time, without ever seeing the future.**

> **Status: design complete, implementation starting.** Nothing below is runnable yet. The [issues](https://github.com/orkwitzel/market/issues) and [milestones](https://github.com/orkwitzel/market/milestones) track progress layer by layer.

## The idea

Pick a date, say March 2008, and an amount of cash. The bot wakes up on that day knowing everything that happened *before* it and nothing after. Each simulated day it looks at the market, decides what to hold, and trades at the next morning's open. Time moves forward over **real historical prices** until it reaches today. Then you replay the whole journey and see how it did, and why.

The bot isn't one strategy. It's a manager with a **toolbox of classic trading algorithms** that you choose. Every month it decides how much to trust each one, based on how they've been doing.

## What makes it honest

Most hobby backtests flatter their strategies without anyone noticing. This one is built to avoid the classic traps:

- **No look-ahead, provably.** The engine steps one day at a time, and strategies can only see data up to "today". An automated test cuts the data at a date, re-runs, and fails if any earlier decision changes.
- **No survivorship bias.** The bot trades the S&P 500 *as it was on each date*, including companies that later went bankrupt or were bought out. If it holds Lehman in 2008, it eats the loss.
- **Real prices, not rewritten ones.** Trades happen at the prices of the day. Splits and dividends are applied when they occur, not baked into the history in advance.
- **The era's frictions.** Commissions, spreads and whole-share trading follow the simulated year, borrowing and idle cash earn the historical interest rate, short sellers pay dividends, and margin calls really happen. A "modern costs" switch shows what changes.
- **A "was it luck?" check.** The report estimates how likely the bot's edge over the market is to be real.

## How the bot thinks

```
 market data (only up to today)
        │
        ▼
 ┌──────────────┐   each strategy says what it would like to hold
 │  strategies  │   (target weights; negative = short)
 └──────┬───────┘
        ▼
 ┌──────────────┐   monthly: how much to trust each strategy,
 │  allocator   │   judged by each one's paper track record
 └──────┬───────┘
        ▼
 ┌──────────────┐   scale total risk up or down
 │   overlays   │   (volatility targeting, drawdown brake)
 └──────┬───────┘
        ▼
 ┌──────────────┐   trade toward the combined target at the next open,
 │    engine    │   with costs, margin, dividends, splits and index changes
 └──────────────┘
```

### The v1 toolbox

| Family | Strategy |
|---|---|
| Market | Equal-weight hold of the whole index |
| Trend | SMA 50/200 crossover |
| Trend | Donchian / Turtle breakout with ATR stop |
| Mean reversion | RSI-2 pullback with a 200-day trend filter |
| Rotation | Cross-sectional 12-1 momentum, top N |
| Relative value | Short-term reversal, long/short |

### Allocators

- **Equal split:** the baseline every clever allocator must beat.
- **Risk parity:** each strategy family contributes the same risk.
- **Risk parity + trust tilt** (default): risk parity nudged toward strategies that have been working, within limits.

## What you'll see

A local web app where you configure a run (drop date, cash, toolbox, allocator, overlays, costs), launch it, and replay it:

- the bot's equity against **SPY buy-and-hold** and each strategy's stand-alone track record
- a stacked chart of **who the bot trusts** over time
- long, short and cash exposure, plus leverage
- current holdings, and a drill-down chart per stock with the bot's trades
- an **event feed that explains every decision**, e.g. *"Volatility target cut exposure to 52%: recent volatility 41% vs 12% target"*
- a final report: returns, risk, drawdowns, costs, attribution per strategy, year-by-year results and the luck check

## Data

All data is free, fetched by the app onto your machine, and **never committed to this repository**. The licenses allow personal use only.

- S&P 500 point-in-time membership: [fja05680/sp500](https://github.com/fja05680/sp500)
- Daily prices with splits and dividends: the Quandl WIKI dataset (to 2018), joined to [Alpaca](https://alpaca.markets/) market data (2016 onward, free API key)
- Interest rates: [FRED](https://fred.stlouisfed.org/) (Fed funds rate)

Runs can start where at least 85% of the index has price data, about 2008 onward with these sources.

## Tech

Python 3.14 · uv · FastAPI · Polars · NumPy · React · TypeScript · Tailwind · shadcn/ui · lightweight-charts · ECharts

## Roadmap

v1 is built layer by layer: data spike & scaffolding → data → engine → strategies → allocators → overlays → report → web app.

Planned after v1:
- run comparison and automatic "what if" variants
- dropping the bot at many start dates to measure start-date luck
- an online-learning allocator
- more strategies (pairs trading, time-series momentum, Bollinger, MACD)
- taxes
- historical market annotations
- paid data for earlier start dates

## Project docs

- [`CONTEXT.md`](CONTEXT.md): the project's vocabulary
- [`docs/adr/`](docs/adr/): why the design is the way it is
- [`AGENTS.md`](AGENTS.md): ground rules for contributors and coding agents

## Disclaimer

An educational project. Nothing here is financial advice, and simulated results say nothing about future returns.

## License

[MIT](LICENSE)
