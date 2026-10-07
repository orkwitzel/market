"""Synthetic market-data fixtures, generated in code (no data files, ADR 0007).

A tiny fake market of six securities over the first half of 2020, built to exercise the
honest-simulation rules: raw prices (ADR 0002), point-in-time membership (ADR 0001),
a split, a cash dividend, a delisting, index joins and removals, a ticker change and a
ticker reuse. Generation is deterministic: fixed dates and a seeded NumPy ``Generator``,
so the same seed always yields identical frames.

Each **security** (see ``CONTEXT.md``) has a stable ``security_id`` distinct from its
ticker, so a reused ticker is two securities sharing a ticker in non-overlapping periods.

Interval convention, for ``tickers`` and ``membership``: ``start_date`` is inclusive,
``end_date`` is exclusive (the first trading day it no longer holds), ``null`` means
still open at the end of the data.

Schemas (all frames sorted by their key columns):

``securities``
    security_id: Utf8, name: Utf8
``tickers``, ``membership``
    The store schemas of ``market.data.membership`` (imported, not duplicated).
``prices`` (raw daily OHLCV, never adjusted)
    security_id: Utf8, date: Date, open: Float64, high: Float64, low: Float64,
    close: Float64, volume: Int64
``corporate_events``
    security_id: Utf8, date: Date (effective date / ex-date), event_type: Utf8
    ("split" or "dividend"), split_ratio: Float64 (new shares per old share; null for
    dividends), dividend: Float64 (cash per share; null for splits)

The scenario (see the constants below):

- ``SPLIT_ID`` (S1) "ALFA": member throughout; 2-for-1 split on ``SPLIT_DATE``.
- ``DIVIDEND_ID`` (S2) "BRVO": member throughout; cash dividend of ``DIVIDEND_AMOUNT``
  ex ``DIVIDEND_DATE``.
- ``REMOVED_ID`` (S3) "CHRL": member at the start, removed from the index on
  ``REMOVAL_DATE``; keeps trading after removal.
- ``RENAMED_ID`` (S4) "DLTA" renamed "DLTX" on ``RENAME_DATE``: trades from the start,
  joins the index on ``JOIN_DATE``.
- ``DELISTED_ID`` (S5) "ECHO": member, delisted; its last price is on
  ``DELIST_LAST_DATE`` and it leaves the index the next trading day.
- ``REUSED_TICKER_ID`` (S6) "ECHO" again: a different company that lists on
  ``REUSE_LIST_DATE`` (after S5 is gone) and joins the index on ``REUSE_JOIN_DATE``.

On event days the overnight gap is switched off so the raw jump lands exactly at the
open: on a split day ``open == prev_close / ratio`` and on an ex-date
``open == prev_close - dividend`` (to the cent). The rest of the bar moves normally.
"""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import polars as pl

from market.data.membership import MEMBERSHIP_SCHEMA, TICKERS_SCHEMA

DATA_START = date(2020, 1, 2)
DATA_END = date(2020, 6, 30)
HOLIDAYS = frozenset(
    {
        date(2020, 1, 20),
        date(2020, 2, 17),
        date(2020, 4, 10),
        date(2020, 5, 25),
    }
)

SPLIT_DATE = date(2020, 3, 2)
SPLIT_RATIO = 2.0
DIVIDEND_DATE = date(2020, 2, 14)
DIVIDEND_AMOUNT = 0.75
REMOVAL_DATE = date(2020, 4, 1)
JOIN_DATE = date(2020, 4, 1)
RENAME_DATE = date(2020, 5, 1)
DELIST_LAST_DATE = date(2020, 3, 31)
REUSE_LIST_DATE = date(2020, 5, 1)
REUSE_JOIN_DATE = date(2020, 6, 1)

DEFAULT_SEED = 20200102

SPLIT_ID = "S1"
DIVIDEND_ID = "S2"
REMOVED_ID = "S3"
RENAMED_ID = "S4"
DELISTED_ID = "S5"
REUSED_TICKER_ID = "S6"

SECURITIES_SCHEMA = pl.Schema({"security_id": pl.Utf8, "name": pl.Utf8})
PRICES_SCHEMA = pl.Schema(
    {
        "security_id": pl.Utf8,
        "date": pl.Date,
        "open": pl.Float64,
        "high": pl.Float64,
        "low": pl.Float64,
        "close": pl.Float64,
        "volume": pl.Int64,
    }
)
CORPORATE_EVENTS_SCHEMA = pl.Schema(
    {
        "security_id": pl.Utf8,
        "date": pl.Date,
        "event_type": pl.Utf8,
        "split_ratio": pl.Float64,
        "dividend": pl.Float64,
    }
)


@dataclass(frozen=True)
class SyntheticMarket:
    """A complete synthetic market: calendar, identities, membership, raw prices, events."""

    trading_days: list[date]
    securities: pl.DataFrame
    tickers: pl.DataFrame
    membership: pl.DataFrame
    prices: pl.DataFrame
    corporate_events: pl.DataFrame


@dataclass(frozen=True)
class _Spec:
    security_id: str
    name: str
    first_priced: date
    last_priced: date
    start_price: float


def trading_days() -> list[date]:
    """Weekdays from ``DATA_START`` to ``DATA_END`` inclusive, minus the fixed ``HOLIDAYS``."""
    days: list[date] = []
    day = DATA_START
    while day <= DATA_END:
        if day.weekday() < 5 and day not in HOLIDAYS:
            days.append(day)
        day += timedelta(days=1)
    return days


def next_trading_day(days: list[date], day: date) -> date:
    """The trading day after ``day``, which must itself be in ``days``."""
    return days[days.index(day) + 1]


def previous_trading_day(days: list[date], day: date) -> date:
    """The trading day before ``day``, which must itself be in ``days``."""
    return days[days.index(day) - 1]


def generate_synthetic_market(seed: int = DEFAULT_SEED) -> SyntheticMarket:
    """Build the synthetic market. Same ``seed`` gives identical frames."""
    days = trading_days()
    last_day = days[-1]
    delist_end = next_trading_day(days, DELIST_LAST_DATE)

    specs = [
        _Spec(SPLIT_ID, "Alfa Corp", days[0], last_day, 120.0),
        _Spec(DIVIDEND_ID, "Bravo Inc", days[0], last_day, 45.0),
        _Spec(REMOVED_ID, "Charlie Co", days[0], last_day, 30.0),
        _Spec(RENAMED_ID, "Delta Holdings", days[0], last_day, 60.0),
        _Spec(DELISTED_ID, "Echo Old Corp", days[0], DELIST_LAST_DATE, 25.0),
        _Spec(REUSED_TICKER_ID, "Echo New Inc", REUSE_LIST_DATE, last_day, 18.0),
    ]

    securities = pl.DataFrame(
        {"security_id": [s.security_id for s in specs], "name": [s.name for s in specs]},
        schema=SECURITIES_SCHEMA,
    )
    tickers = pl.DataFrame(
        [
            (SPLIT_ID, "ALFA", days[0], None),
            (DIVIDEND_ID, "BRVO", days[0], None),
            (REMOVED_ID, "CHRL", days[0], None),
            (RENAMED_ID, "DLTA", days[0], RENAME_DATE),
            (RENAMED_ID, "DLTX", RENAME_DATE, None),
            (DELISTED_ID, "ECHO", days[0], delist_end),
            (REUSED_TICKER_ID, "ECHO", REUSE_LIST_DATE, None),
        ],
        schema=TICKERS_SCHEMA,
        orient="row",
    )
    membership = pl.DataFrame(
        [
            (SPLIT_ID, days[0], None),
            (DIVIDEND_ID, days[0], None),
            (REMOVED_ID, days[0], REMOVAL_DATE),
            (RENAMED_ID, JOIN_DATE, None),
            (DELISTED_ID, days[0], delist_end),
            (REUSED_TICKER_ID, REUSE_JOIN_DATE, None),
        ],
        schema=MEMBERSHIP_SCHEMA,
        orient="row",
    )
    corporate_events = pl.DataFrame(
        [
            (SPLIT_ID, SPLIT_DATE, "split", SPLIT_RATIO, None),
            (DIVIDEND_ID, DIVIDEND_DATE, "dividend", None, DIVIDEND_AMOUNT),
        ],
        schema=CORPORATE_EVENTS_SCHEMA,
        orient="row",
    )

    splits: dict[tuple[str, date], float] = {
        (sid, day): ratio
        for sid, day, ratio in corporate_events.filter(pl.col("event_type") == "split")
        .select("security_id", "date", "split_ratio")
        .iter_rows()
    }
    dividends: dict[tuple[str, date], float] = {
        (sid, day): amount
        for sid, day, amount in corporate_events.filter(pl.col("event_type") == "dividend")
        .select("security_id", "date", "dividend")
        .iter_rows()
    }

    rng = np.random.default_rng(seed)
    frames = [_price_path(spec, days, rng, splits, dividends) for spec in specs]
    prices = pl.concat(frames).sort("security_id", "date")

    return SyntheticMarket(
        trading_days=days,
        securities=securities,
        tickers=tickers.sort("security_id", "start_date"),
        membership=membership.sort("security_id", "start_date"),
        prices=prices,
        corporate_events=corporate_events.sort("security_id", "date"),
    )


def _price_path(
    spec: _Spec,
    days: list[date],
    rng: np.random.Generator,
    splits: dict[tuple[str, date], float],
    dividends: dict[tuple[str, date], float],
) -> pl.DataFrame:
    """Raw OHLCV for one security: a random walk with exact split and dividend jumps at the open."""
    span = [d for d in days if spec.first_priced <= d <= spec.last_priced]
    n = len(span)
    # Draw a fixed amount of noise per security regardless of its span, so one
    # security's dates never shift another security's random numbers.
    returns = rng.normal(0.0005, 0.015, len(days))[:n]
    gaps = rng.normal(0.0, 0.004, len(days))[:n]
    wicks = rng.uniform(0.0, 0.01, (len(days), 2))[:n]
    volumes = rng.integers(100_000, 5_000_000, len(days))[:n]

    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    prev_close = spec.start_price
    for i, day in enumerate(span):
        key = (spec.security_id, day)
        if key in splits or key in dividends:
            open_ = round(prev_close / splits.get(key, 1.0) - dividends.get(key, 0.0), 2)
        else:
            open_ = round(prev_close * (1.0 + gaps[i]), 2) if i else round(prev_close, 2)
        close = round(open_ * (1.0 + returns[i]), 2)
        high = round(max(open_, close) * (1.0 + wicks[i, 0]), 2)
        low = round(min(open_, close) * (1.0 - wicks[i, 1]), 2)
        opens.append(open_)
        highs.append(high)
        lows.append(low)
        closes.append(close)
        prev_close = close

    return pl.DataFrame(
        {
            "security_id": [spec.security_id] * n,
            "date": span,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes.astype(np.int64),
        },
        schema=PRICES_SCHEMA,
    )
