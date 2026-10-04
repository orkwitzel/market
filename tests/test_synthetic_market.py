"""The synthetic market fixture contains every scenario, consistently and deterministically."""

from datetime import date

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from synthetic_market import (
    CORPORATE_EVENTS_SCHEMA,
    DELIST_LAST_DATE,
    DIVIDEND_AMOUNT,
    DIVIDEND_DATE,
    JOIN_DATE,
    MEMBERSHIP_SCHEMA,
    PRICES_SCHEMA,
    REMOVAL_DATE,
    RENAME_DATE,
    REUSE_JOIN_DATE,
    REUSE_LIST_DATE,
    SECURITIES_SCHEMA,
    SPLIT_DATE,
    SPLIT_RATIO,
    TICKERS_SCHEMA,
    SyntheticMarket,
    generate_synthetic_market,
)

CENT = 0.005


def _members_on(market: SyntheticMarket, day: date) -> set[str]:
    m = market.membership.filter(
        (pl.col("start_date") <= day) & (pl.col("end_date").is_null() | (pl.col("end_date") > day))
    )
    return set(m["security_id"].to_list())


def _closes(market: SyntheticMarket, security_id: str) -> pl.DataFrame:
    return market.prices.filter(pl.col("security_id") == security_id).sort("date")


def _close_before_and_on(
    market: SyntheticMarket, security_id: str, day: date
) -> tuple[float, float]:
    p = _closes(market, security_id)
    i = p["date"].to_list().index(day)
    return p["close"][i - 1], p["close"][i]


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
    assert events.rows() == [("S1", SPLIT_DATE, "split", SPLIT_RATIO, None)]
    before, on = _close_before_and_on(synthetic_market, "S1", SPLIT_DATE)
    assert on == pytest.approx(before / SPLIT_RATIO, abs=CENT)


def test_dividend_ex_date_drop(synthetic_market: SyntheticMarket) -> None:
    events = synthetic_market.corporate_events.filter(pl.col("event_type") == "dividend")
    assert events.rows() == [("S2", DIVIDEND_DATE, "dividend", None, DIVIDEND_AMOUNT)]
    before, on = _close_before_and_on(synthetic_market, "S2", DIVIDEND_DATE)
    assert on == pytest.approx(before - DIVIDEND_AMOUNT, abs=CENT)


def test_delisting(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    s5 = _closes(synthetic_market, "S5")
    assert s5["date"].max() == DELIST_LAST_DATE < days[-1]
    next_day = days[days.index(DELIST_LAST_DATE) + 1]
    assert "S5" in _members_on(synthetic_market, DELIST_LAST_DATE)
    assert "S5" not in _members_on(synthetic_market, next_day)


def test_index_removal_keeps_trading(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    before = days[days.index(REMOVAL_DATE) - 1]
    assert "S3" in _members_on(synthetic_market, before)
    assert "S3" not in _members_on(synthetic_market, REMOVAL_DATE)
    assert _closes(synthetic_market, "S3")["date"].max() == days[-1]


def test_index_join_with_prior_history(synthetic_market: SyntheticMarket) -> None:
    days = synthetic_market.trading_days
    assert "S4" not in _members_on(synthetic_market, days[days.index(JOIN_DATE) - 1])
    assert "S4" in _members_on(synthetic_market, JOIN_DATE)
    first_priced: date = _closes(synthetic_market, "S4")["date"][0]
    assert first_priced < JOIN_DATE


def test_ticker_change(synthetic_market: SyntheticMarket) -> None:
    s4 = synthetic_market.tickers.filter(pl.col("security_id") == "S4")
    assert s4.select("ticker", "start_date", "end_date").rows() == [
        ("DLTA", synthetic_market.trading_days[0], RENAME_DATE),
        ("DLTX", RENAME_DATE, None),
    ]


def test_ticker_reuse(synthetic_market: SyntheticMarket) -> None:
    echo = synthetic_market.tickers.filter(pl.col("ticker") == "ECHO").sort("start_date")
    assert echo["security_id"].to_list() == ["S5", "S6"]
    old_end, new_start = echo["end_date"][0], echo["start_date"][1]
    assert old_end is not None and old_end <= new_start == REUSE_LIST_DATE
    s6 = _closes(synthetic_market, "S6")
    assert s6["date"].min() == REUSE_LIST_DATE > DELIST_LAST_DATE
    assert "S6" in _members_on(synthetic_market, REUSE_JOIN_DATE)
    assert "S6" not in _members_on(synthetic_market, REUSE_LIST_DATE)


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
