# 7. Free data: fja05680 membership, Quandl WIKI stitched to Alpaca, FRED

- **Status:** Accepted (pending verification by the data spike)
- **Date:** 2026-10-04

## Context

We need point-in-time S&P 500 membership plus raw daily prices and corporate actions for every member, including dead companies, for free, without hard caps that make the first download take days. Research (2026-10) found:

- **yfinance**: no delisted stocks, and silently returns a *different company* for recycled tickers. Ruled out.
- **Tiingo free**: good fields and coverage, but 500 symbols/month and 50 requests/hour make the first download take about 2 days across two monthly windows. Ruled out by the user.
- **Quandl WIKI** (Kaggle mirror): free, no account, downloads in seconds; raw OHLCV plus `ex-dividend` and `split_ratio`; 3,199 tickers to 2018-03-27; only names alive in 2014 or later.
- **Alpaca free plan**: raw bars and a corporate-actions API from 2016, 200 requests/minute; free sign-up. Delisted coverage unverified.

## Decision

- **Membership:** [fja05680/sp500](https://github.com/fja05680/sp500) (MIT). Use the original suffixed file to separate reused tickers, add a manual rename map, normalize class tickers (BRK.B → BRK-B).
- **Prices:** Quandl WIKI up to 2018-03-27, stitched to **Alpaca** from 2016 onward, validated on the 2016–2018 overlap (raw closes, split dates).
- **Rates:** Fed funds rate from FRED.
- **Benchmark:** SPY isn't in WIKI and Alpaca starts in 2016, so SPY history before 2016 comes from a separate single-ticker source (yfinance or Tiingo free; recycled-ticker problems don't apply to SPY). The data spike confirms which.
- Expected earliest drop date under the 85% coverage rule: about early 2008. Caveat: the missing members in 2008 are largely that year's casualties (they died before 2014), so 2008 runs are somewhat flattering; the coverage line in the report shows this.
- The data source sits behind an interface so a paid source can replace or supplement it later.
- **Data spike first:** before building the data layer, verify Alpaca's coverage of dead tickers (e.g. TWTR, CELG, SIVB) and free access to its corporate-actions API. If it fails, the fallback is one month of Tiingo Power (~$30), **only with the owner's approval**.
- Downloaded data, recordings and API keys are never committed. Licenses are personal/internal use; the app is local only.

## Consequences

- Stitching two sources requires ticker-identity mapping and overlap validation.
- A public hosted demo with real prices is not possible under these licenses.
- Possible later upgrades: EODHD (~$20/month, claims coverage back to 2000), Norgate, Sharadar.
