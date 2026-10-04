# 2. Raw prices with corporate events applied as of the simulated date

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

Most free data and most tutorials use **adjusted prices**: a history rewritten today so that every split and dividend is smoothed out of the entire past. That series is built from future events: Apple in 2005 traded around $40 but appears at roughly $1.30 in today's adjusted series. Trading at adjusted prices breaks the whole-share rule and per-trade commissions (ADR 0006), hides dividends inside the price (so short sellers can't be charged them), and leaks future information.

## Decision

- The data layer stores **raw** daily OHLCV plus explicit **split and dividend events**.
- Fills always happen at the raw price of the day.
- On a split date the engine changes share counts; on a dividend's ex-date it credits cash to holders and debits it from short sellers.
- Strategies receive **as-of adjusted history**: prices adjusted only for events on or before the as-of date, so indicators never see a fake split "crash".
- When a stock's data ends while it is held, the position is **settled at its last traded price** and logged. This is close to exact for cash buyouts, approximate for stock-for-stock mergers, and correctly painful for collapses.

## Consequences

- The data source must provide raw prices and corporate actions (ADR 0007).
- The engine needs a corporate-events component and as-of adjustment in the data window.
- Stock-for-stock merger settlement is a documented simplification.
