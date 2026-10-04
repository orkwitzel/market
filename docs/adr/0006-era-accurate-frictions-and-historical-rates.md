# 6. Era-accurate trading frictions and historical interest rates

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The bot is "dropped into the past", so it should live under that era's conditions. Commissions fell from roughly $15–20 per trade in 2000 to $0 in October 2019, spreads were wide before decimalization (April 2001), and mainstream fractional shares only arrived around 2019. Interest rates swung from near zero (2009–2015, 2020–21) to over 5% (2000, 2023–24), changing the cost of leverage and the return on idle cash.

## Decision

- **Cost model**, a function of date, configured in a visible table:
  - commission per trade, slippage/spread as a percentage, and whether fractional shares are allowed (whole shares before 2019, rounded down; positions smaller than one share are skipped and logged).
  - **Era-accurate by default**, with a **"modern costs"** run switch that applies today's frictions to every date.
- **Fills** at the next day's open.
- **Trading band** to avoid fidgeting: adjust a position only if it is off target by more than 25% of its target weight or 1% of the portfolio (whichever is larger); skip trades under 0.5% of the account; exits, new positions and margin calls always trade. Both configurable.
- **Long, short and margin** all allowed:
  - Reg T 2× leverage limit always enforced by the engine.
  - Margin interest = historical Fed funds rate + spread (default 2%); cash interest = Fed funds − spread (default 0.5%), floored at 0. Rates stay historical even under "modern costs".
  - Flat short-borrow fee (default 0.5%/year); every S&P 500 stock is assumed shortable; short sellers pay dividends.
  - Margin call when equity falls below 25% of long value / 30% of short value: proportional liquidation at the next open, flagged in the event feed.
- **Default starting cash: $100,000.** Any amount is allowed; a pre-run warning flags cash too small for the toolbox and era, and the report shows the tracking gap.
- **No taxes** in v1; everything is labelled pre-tax. Positions record open dates so tax-lot accounting can be added later.

## Consequences

- Historical commission and spread numbers are documented approximations, not a specific broker's price list.
- Small accounts genuinely struggle with 500-stock strategies before 2019; this is shown, not hidden.
- The Fed funds series (FRED) becomes a required data input.
