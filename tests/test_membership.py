"""Point-in-time membership queries, on the synthetic market's frames (ADR 0001)."""

from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
from synthetic_market import (
    DATA_START,
    DELIST_LAST_DATE,
    DELISTED_ID,
    DIVIDEND_ID,
    JOIN_DATE,
    REMOVAL_DATE,
    REMOVED_ID,
    RENAME_DATE,
    RENAMED_ID,
    REUSE_JOIN_DATE,
    REUSED_TICKER_ID,
    SPLIT_ID,
    SyntheticMarket,
    next_trading_day,
)

from market.data.membership import EVENTS_SCHEMA, JOIN, LEAVE, Membership


@pytest.fixture
def membership(synthetic_market: SyntheticMarket) -> Membership:
    return Membership(tickers=synthetic_market.tickers, membership=synthetic_market.membership)


def _ids(frame: pl.DataFrame) -> list[str]:
    return frame["security_id"].to_list()


def test_members_on_first_day(membership: Membership) -> None:
    members = membership.members_on(DATA_START)
    assert _ids(members) == [SPLIT_ID, DIVIDEND_ID, REMOVED_ID, DELISTED_ID]
    assert members["ticker"].to_list() == ["ALFA", "BRVO", "CHRL", "ECHO"]


def test_members_on_is_start_inclusive_end_exclusive(membership: Membership) -> None:
    before = REMOVAL_DATE - timedelta(days=1)
    assert REMOVED_ID in _ids(membership.members_on(before))
    on = _ids(membership.members_on(REMOVAL_DATE))
    assert REMOVED_ID not in on
    assert RENAMED_ID in on  # joined on the same day


def test_members_on_uses_the_ticker_of_that_day(membership: Membership) -> None:
    before = membership.members_on(RENAME_DATE - timedelta(days=1))
    after = membership.members_on(RENAME_DATE)
    assert before.filter(pl.col("security_id") == RENAMED_ID)["ticker"].item() == "DLTA"
    assert after.filter(pl.col("security_id") == RENAMED_ID)["ticker"].item() == "DLTX"


def test_members_on_is_open_ended_after_the_last_change(membership: Membership) -> None:
    far = membership.members_on(date(2030, 1, 1))
    assert _ids(far) == [SPLIT_ID, DIVIDEND_ID, RENAMED_ID, REUSED_TICKER_ID]


def test_members_on_before_coverage_is_an_error(membership: Membership) -> None:
    assert membership.first_date == DATA_START
    with pytest.raises(ValueError, match="before"):
        membership.members_on(DATA_START - timedelta(days=1))


def test_reused_ticker_resolves_by_date(
    membership: Membership, synthetic_market: SyntheticMarket
) -> None:
    assert membership.securities_for_ticker("ECHO", DELIST_LAST_DATE) == [DELISTED_ID]
    assert membership.securities_for_ticker("ECHO", REUSE_JOIN_DATE) == [REUSED_TICKER_ID]
    gap = next_trading_day(synthetic_market.trading_days, DELIST_LAST_DATE)
    assert membership.securities_for_ticker("ECHO", gap) == []


def test_ticker_of(membership: Membership) -> None:
    assert membership.ticker_of(RENAMED_ID, RENAME_DATE - timedelta(days=1)) == "DLTA"
    assert membership.ticker_of(RENAMED_ID, RENAME_DATE) == "DLTX"
    assert membership.ticker_of("nope", RENAME_DATE) is None


def test_events_between(membership: Membership, synthetic_market: SyntheticMarket) -> None:
    delist_end = next_trading_day(synthetic_market.trading_days, DELIST_LAST_DATE)
    events = membership.events_between(date(2020, 3, 1), date(2020, 6, 30))
    assert events.schema == EVENTS_SCHEMA
    # Sorted by date, then security id; in the fixture all three April events share a day.
    assert delist_end == REMOVAL_DATE == JOIN_DATE
    assert events.rows() == [
        (REMOVAL_DATE, REMOVED_ID, "CHRL", LEAVE),
        (JOIN_DATE, RENAMED_ID, "DLTA", JOIN),
        (delist_end, DELISTED_ID, "ECHO", LEAVE),
        (REUSE_JOIN_DATE, REUSED_TICKER_ID, "ECHO", JOIN),
    ]


def test_events_between_includes_both_ends(membership: Membership) -> None:
    events = membership.events_between(REUSE_JOIN_DATE, REUSE_JOIN_DATE)
    assert _ids(events) == [REUSED_TICKER_ID]
    assert membership.events_between(
        REUSE_JOIN_DATE, REUSE_JOIN_DATE - timedelta(days=1)
    ).is_empty()


def test_initial_members_join_on_the_first_date(membership: Membership) -> None:
    events = membership.events_between(DATA_START, DATA_START)
    assert set(events["event"]) == {JOIN}
    assert _ids(events) == _ids(membership.members_on(DATA_START))


def test_rejects_overlapping_membership(synthetic_market: SyntheticMarket) -> None:
    doubled = pl.concat([synthetic_market.membership, synthetic_market.membership.head(1)])
    with pytest.raises(ValueError, match="overlap"):
        Membership(tickers=synthetic_market.tickers, membership=doubled)


def test_rejects_wrong_schema(synthetic_market: SyntheticMarket) -> None:
    with pytest.raises(ValueError, match="schema"):
        Membership(
            tickers=synthetic_market.tickers,
            membership=synthetic_market.membership.drop("end_date"),
        )


def test_save_and_load_round_trip(membership: Membership, tmp_path: Path) -> None:
    membership.save(tmp_path / "membership")
    loaded = Membership.load(tmp_path / "membership")
    assert loaded.tickers.equals(membership.tickers)
    assert loaded.membership.equals(membership.membership)
