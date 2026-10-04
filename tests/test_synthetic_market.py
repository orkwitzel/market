"""The synthetic market fixture contains every scenario, consistently and deterministically."""

from datetime import date

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from synthetic_market import (
    CORPORATE_EVENTS_SCHEMA,
    DELIST_LAST_DATE,
    DELISTED_ID,
    DIVIDEND_AMOUNT,
    DIVIDEND_DATE,
    DIVIDEND_ID,
    JOIN_DATE,
    MEMBERSHIP_SCHEMA,
    PRICES_SCHEMA,
    REMOVAL_DATE,
    REMOVED_ID,
    RENAME_DATE,
    RENAMED_ID,
    REUSE_JOIN_DATE,
    REUSE_LIST_DATE,
    REUSED_TICKER_ID,
    SECURITIES_SCHEMA,
    SPLIT_DATE,
    SPLIT_ID,
    SPLIT_RATIO,
    TICKERS_SCHEMA,
    SyntheticMarket,
    generate_synthetic_market,
    next_trading_day,
    previous_trading_day,
)

# Prices are rounded to the cent, so exact jumps hold to within half a cent.
ROUNDING_TOLERANCE = 0.005


def _members_on(market: SyntheticMarket, day: date) -> set[str]:
    m = market.membership.filter(
        (pl.col("start_date") <= day) & (pl.col("end_date").is_null() | (pl.col("end_date") > day))
    )
    return set(m["security_id"].to_list())


def _bars(market: SyntheticMarket, security_id: str) -> pl.DataFrame:
    return market.prices.filter(pl.col("security_id") == security_id).sort("date")


def _prev_close_and_open(
    market: SyntheticMarket, security_id: str, day: date
) -> tuple[float, float]:
    p = _bars(market, security_id)
    i = p["date"].to_list().index(day)
    return p["close"][i - 1], p["open"][i]


def test_schemas(synthetic_market: SyntheticMarket) -> None:
    assert synthetic_market.securities.schema == SECURITIES_SCHEMA
    assert synthetic_market.tickers.schema == TICKERS_SCHEMA
    assert synthetic_market.membership.schema == MEMBERSHIP_SCHEMA
    assert synthetic_market.prices.schema == PRICES_SCHEMA
    assert synthetic_market.corporate_events.schema == CORPORATE_EVENTS_SCHEMA


def test_deterministic() -> None:
    a, b = generate_synthetic_market(), generate_synthetic_market()
    assert a.trading_days == b.trading_days
    for name in ("securities", "tickers", "membership", "prices", "corporate_events"):
        assert_frame_equal(getattr(a, name), getattr(b, name))


def test_seed_changes_prices_only() -> None:
    a, b = generate_synthetic_market(seed=1), generate_synthetic_market(seed=2)
    assert_frame_equal(a.membership, b.membership)
    assert not a.prices.equals(b.prices)


def test_prices_on_trading_days_and_well_formed(synthetic_market: SyntheticMarket) -> None:
    p = synthetic_market.prices
    days = set(synthetic_market.trading_days)
    assert all(d.weekday() < 5 for d in days)
    assert set(p["date"].to_list()) <= days
    assert p.select(pl.struct("security_id", "date").is_unique().all()).item()
    assert p.filter(
        (pl.col("low") > pl.min_horizontal("open", "close"))
        | (pl.col("high") < pl.max_horizontal("open", "close"))
        | (pl.col("low") <= 0)
        | (pl.col("volume") <= 0)
    ).is_empty()
    # Every security trades on every trading day of its price span: no gaps.
    for sid, g in p.group_by("security_id"):
        dates: list[date] = g["date"].sort().to_list()
        span = [d for d in synthetic_market.trading_days if dates[0] <= d <= dates[-1]]
        assert dates == span, sid


def test_ids_distinct_from_tickers(synthetic_market: SyntheticMarket) -> None:
    ids = set(synthetic_market.securities["security_id"].to_list())
    assert set(synthetic_market.tickers["security_id"].to_list()) == ids
    assert set(synthetic_market.prices["security_id"].to_list()) == ids
    assert not ids & set(synthetic_market.tickers["ticker"].to_list())


def test_split_raw_price_jump(synthetic_market: SyntheticMarket) -> None:
    events = synthetic_market.corporate_events.filter(pl.col("event_type") == "split")
    assert events.rows() == [(SPLIT_ID, SPLIT_DATE, "split", SPLIT_RATIO, None)]
    prev_close, open_ = _prev_close_and_open(synthetic_market, SPLIT_ID, SPLIT_DATE)
    assert open_ == pytest.approx(prev_close / SPLIT_RATIO, abs=ROUNDING_TOLERANCE)


def test_dividend_ex_date_drop(synthetic_market: SyntheticMarket) -> None:
    events = synthetic_market.corporate_events.filter(pl.col("event_type") == "dividend")
    assert events.rows() == [(DIVIDEND_ID, DIVIDEND_DATE, "dividend", None, DIVIDEND_AMOUNT)]
    prev_close, open_ = _prev_close_and_open(synthetic_market, DIVIDEND_ID, DIVIDEND_DATE)
    assert open_ == pytest.approx(prev_close - DIVIDEND_AMOUNT, abs=ROUNDING_TOLERANCE)


def test_event_days_are_not_flat(synthetic_market: SyntheticMarket) -> None:
    events = synthetic_market.corporate_events.select("security_id", "date")
    bars = synthetic_market.prices.join(events, on=["security_id", "date"])
    assert bars.height == events.height
    assert bars.filter(pl.col("open") == pl.col("close")).is_empty()


def test_delisting(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    s5 = _bars(synthetic_market, DELISTED_ID)
    assert s5["date"].max() == DELIST_LAST_DATE < days[-1]
    next_day = next_trading_day(days, DELIST_LAST_DATE)
    assert DELISTED_ID in _members_on(synthetic_market, DELIST_LAST_DATE)
    assert DELISTED_ID not in _members_on(synthetic_market, next_day)


def test_index_removal_keeps_trading(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    before = previous_trading_day(days, REMOVAL_DATE)
    assert REMOVED_ID in _members_on(synthetic_market, before)
    assert REMOVED_ID not in _members_on(synthetic_market, REMOVAL_DATE)
    assert _bars(synthetic_market, REMOVED_ID)["date"].max() == days[-1]


def test_index_join_with_prior_history(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    day_before = previous_trading_day(days, JOIN_DATE)
    assert RENAMED_ID not in _members_on(synthetic_market, day_before)
    assert RENAMED_ID in _members_on(synthetic_market, JOIN_DATE)
    first_priced: date = _bars(synthetic_market, RENAMED_ID)["date"][0]
    assert first_priced < JOIN_DATE


def test_ticker_change(synthetic_market: SyntheticMarket) -> None:
    s4 = synthetic_market.tickers.filter(pl.col("security_id") == RENAMED_ID)
    assert s4.select("ticker", "start_date", "end_date").rows() == [
        ("DLTA", synthetic_market.trading_days[0], RENAME_DATE),
        ("DLTX", RENAME_DATE, None),
    ]


def test_ticker_reuse(synthetic_market: SyntheticMarket) -> None:
    echo = synthetic_market.tickers.filter(pl.col("ticker") == "ECHO").sort("start_date")
    assert echo["security_id"].to_list() == [DELISTED_ID, REUSED_TICKER_ID]
    old_end, new_start = echo["end_date"][0], echo["start_date"][1]
    assert old_end is not None and old_end <= new_start == REUSE_LIST_DATE
    s6 = _bars(synthetic_market, REUSED_TICKER_ID)
    assert s6["date"].min() == REUSE_LIST_DATE > DELIST_LAST_DATE
    assert REUSED_TICKER_ID in _members_on(synthetic_market, REUSE_JOIN_DATE)
    assert REUSED_TICKER_ID not in _members_on(synthetic_market, REUSE_LIST_DATE)


def test_members_always_have_prices(synthetic_market: SyntheticMarket) -> None:
    priced = synthetic_market.prices.group_by("date").agg(pl.col("security_id"))
    by_day = {d: set(ids) for d, ids in priced.iter_rows()}
    for day in synthetic_market.trading_days:
        assert _members_on(synthetic_market, day) <= by_day[day], day


def test_ticker_intervals_do_not_overlap(synthetic_market: SyntheticMarket) -> None:
    for ticker, g in synthetic_market.tickers.sort("start_date").group_by("ticker"):
        ends, starts = g["end_date"].to_list()[:-1], g["start_date"].to_list()[1:]
        for end, start in zip(ends, starts, strict=True):
            assert end is not None and end <= start, ticker
