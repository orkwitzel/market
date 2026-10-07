"""Building point-in-time membership from fja05680/sp500-shaped files.

Inputs are the synthetic CSV strings in ``tests/synthetic_sp500.py``; no real data (ADR 0007).
"""

from dataclasses import replace
from datetime import date

import polars as pl
import pytest
from synthetic_sp500 import CHANGES, COMPONENTS, TEST_CURATION

from market.data import fja05680
from market.data.fja05680 import (
    Change,
    Snapshot,
    build_membership,
    normalize_ticker,
    parse_changes,
    parse_components,
    raw_url,
    split_symbol,
)
from market.data.membership import EventKind, Membership
from market.data.sp500_curation import CURATION, Correction, Curation, Rename


def build(
    components: str = COMPONENTS, changes: str = CHANGES, curation: Curation = TEST_CURATION
) -> Membership:
    return build_membership(components, changes, curation)


def ids_on(membership: Membership, day: date) -> list[str]:
    return membership.members_on(day)["security_id"].to_list()


# --- parsing ---------------------------------------------------------------------------


def test_normalize_ticker_uses_the_price_source_class_form() -> None:
    assert normalize_ticker("BRK.B") == "BRK-B"
    assert normalize_ticker(" bf.b ") == "BF-B"
    assert normalize_ticker("AAPL") == "AAPL"


def test_split_symbol() -> None:
    assert split_symbol("BAC") == ("BAC", None)
    assert split_symbol("BAC-199809") == ("BAC", date(1998, 10, 1))
    assert split_symbol("XL-201812") == ("XL", date(2019, 1, 1))
    assert split_symbol("TMC.A-200006") == ("TMC-A", date(2000, 7, 1))


def test_parse_components() -> None:
    snapshots = parse_components(COMPONENTS)
    assert [s.day for s in snapshots] == [
        date(1996, 1, 2),
        date(1996, 1, 10),
        date(1996, 2, 1),
        date(1996, 3, 1),
    ]
    assert snapshots[0] == Snapshot(date(1996, 1, 2), ("AET", "BAC", "BAC-199601", "BRK.B", "XYZ"))


def test_parse_components_sorts_rows_by_date() -> None:
    lines = COMPONENTS.split("\r\n")
    shuffled = "\r\n".join([lines[0], *reversed(lines[1:-1])])
    assert parse_components(shuffled) == parse_components(COMPONENTS)


def test_parse_components_rejects_duplicate_dates() -> None:
    lines = COMPONENTS.split("\r\n")
    with pytest.raises(ValueError, match="duplicate"):
        parse_components("\r\n".join([*lines, lines[1]]))


@pytest.mark.parametrize("header", ["day,tickers", "date,add,remove"])
def test_parse_components_rejects_unexpected_header(header: str) -> None:
    with pytest.raises(ValueError, match="header"):
        parse_components(COMPONENTS.replace("date,tickers", header))


def test_parse_changes() -> None:
    changes = parse_changes(CHANGES)
    assert len(changes) == 6
    assert changes[0] == Change(date(1996, 4, 1), added=("OLD",), removed=("AET",))
    assert changes[2] == Change(date(1996, 6, 3), added=("XYZ",), removed=())
    assert changes[3] == Change(date(1996, 7, 1), added=(), removed=("BAC",))


def test_parse_changes_normalizes_class_tickers() -> None:
    changes = parse_changes('date,add,remove\n2020-01-02,"BF.B",""\n')
    assert changes == [Change(date(2020, 1, 2), added=("BF-B",), removed=())]


def test_raw_url_is_pinned_and_quoted() -> None:
    url = raw_url("S&P 500 Historical Components & Changes.csv", ref="abc123")
    assert url == (
        "https://raw.githubusercontent.com/fja05680/sp500/abc123/"
        "S%26P%20500%20Historical%20Components%20%26%20Changes.csv"
    )


# --- building ---------------------------------------------------------------------------


def test_reused_ticker_resolves_to_different_securities_by_period() -> None:
    membership = build()
    assert ids_on(membership, date(1996, 1, 5)) == [
        "AET-199604",
        "BAC",
        "BAC-199601",
        "BRK.B",
        "XYZ",
    ]
    assert membership.securities_for_ticker("BAC", date(1996, 1, 5)) == ["BAC", "BAC-199601"]
    assert membership.securities_for_ticker("BAC", date(1996, 12, 2)) == ["BAC"]


def test_tickers_are_normalized_and_suffixes_stripped() -> None:
    members = build().members_on(date(1996, 1, 5))
    assert members["ticker"].to_list() == ["AET", "BAC", "BAC", "BRK-B", "XYZ"]


def test_snapshot_rows_hold_until_the_next_row() -> None:
    membership = build()
    # BAC-199601 is in the 1996-01-10 row but not the 1996-02-01 one.
    assert "BAC-199601" in ids_on(membership, date(1996, 1, 31))
    assert "BAC-199601" not in ids_on(membership, date(1996, 2, 1))


def test_alias_artifact_is_one_security() -> None:
    membership = build()
    aet = membership.membership.filter(pl.col("security_id") == "AET-199604")
    assert aet.select("start_date", "end_date").rows() == [(date(1996, 1, 2), date(1996, 4, 1))]
    assert "AET" not in membership.membership["security_id"].to_list()


def test_re_entry_keeps_the_security() -> None:
    membership = build()
    xyz = membership.membership.filter(pl.col("security_id") == "XYZ")
    assert xyz.select("start_date", "end_date").rows() == [
        (date(1996, 1, 2), date(1996, 2, 1)),
        (date(1996, 3, 1), None),
    ]
    bac = membership.membership.filter(pl.col("security_id") == "BAC")
    assert bac.select("start_date", "end_date").rows() == [
        (date(1996, 1, 2), date(1996, 7, 1)),
        (date(1996, 8, 1), None),
    ]


def test_rename_changes_the_ticker_not_the_security() -> None:
    membership = build()
    assert membership.ticker_of("XYZ", date(1996, 4, 30)) == "XYZ"
    assert membership.ticker_of("XYZ", date(1996, 5, 1)) == "XYZW"
    events = membership.events_between(date(1996, 5, 1), date(1996, 5, 1))
    assert events.is_empty()


def test_ticker_freed_by_a_rename_or_delisting_is_a_new_security() -> None:
    membership = build()
    assert membership.securities_for_ticker("XYZ", date(1996, 6, 3)) == ["XYZ@1996-06-03"]
    assert membership.securities_for_ticker("OLD", date(1996, 2, 1)) == ["OLD-199603"]
    assert membership.securities_for_ticker("OLD", date(1996, 4, 1)) == ["OLD@1996-04-01"]


def test_correction_within_the_snapshots_adds_a_missing_member() -> None:
    # Like Linde plc in 2018: dated before the last snapshot, a ticker no snapshot uses.
    membership = build()
    assert "LIN@1996-02-15" not in ids_on(membership, date(1996, 2, 14))
    assert "LIN@1996-02-15" in ids_on(membership, date(1996, 2, 15))
    assert "LIN@1996-02-15" in ids_on(membership, date(1997, 1, 2))


def test_curated_ticker_reuse_closes_the_old_label() -> None:
    curation = replace(
        TEST_CURATION,
        re_entries=frozenset(),
        reused_ticker_adds=frozenset({(date(1996, 8, 1), "BAC")}),
    )
    membership = build(curation=curation)
    assert membership.securities_for_ticker("BAC", date(1996, 8, 1)) == ["BAC@1996-08-01"]
    assert membership.ticker_of("BAC", date(1996, 8, 1)) is None
    assert membership.ticker_of("BAC", date(1996, 7, 31)) == "BAC"


def test_events_between() -> None:
    events = build().events_between(date(1996, 4, 1), date(1996, 9, 3))
    assert events.select("date", "security_id", "event").rows() == [
        (date(1996, 4, 1), "AET-199604", EventKind.LEAVE),
        (date(1996, 4, 1), "OLD@1996-04-01", EventKind.JOIN),
        (date(1996, 6, 3), "XYZ@1996-06-03", EventKind.JOIN),
        (date(1996, 7, 1), "BAC", EventKind.LEAVE),
        (date(1996, 8, 1), "BAC", EventKind.JOIN),
        (date(1996, 9, 3), "OLD@1996-04-01", EventKind.LEAVE),
        (date(1996, 9, 3), "ZED@1996-09-03", EventKind.JOIN),
    ]


def test_every_member_has_a_ticker_on_every_change_date() -> None:
    membership = build()
    days = sorted(
        {*membership.membership["start_date"].to_list(), *membership.tickers["start_date"]}
    )
    for day in days:
        assert membership.members_on(day)["ticker"].null_count() == 0, day


def test_build_is_deterministic() -> None:
    first, second = build(), build()
    assert first.membership.equals(second.membership)
    assert first.tickers.equals(second.tickers)


# --- inconsistent input fails loudly ----------------------------------------------------


def test_removing_a_non_member_is_an_error() -> None:
    with pytest.raises(ValueError, match="not a member"):
        build(changes=CHANGES.replace('"","BAC"', '"","NOPE"'))


def test_adding_a_current_member_is_an_error() -> None:
    with pytest.raises(ValueError, match="already a member"):
        build(changes=CHANGES.replace('"ZED","OLD"', '"BRK.B","OLD"'))


def test_rename_missing_from_the_changes_is_an_error() -> None:
    curation = replace(TEST_CURATION, renames=(Rename(date(1996, 6, 3), "BAC", "BOA"),))
    with pytest.raises(ValueError, match="rename"):
        build(curation=curation)


def test_uncurated_re_entry_is_an_error() -> None:
    curation = replace(TEST_CURATION, re_entries=frozenset())
    with pytest.raises(ValueError, match=r"former member BAC\..*curated re-entries"):
        build(curation=curation)


def test_curated_re_entry_without_a_former_member_is_an_error() -> None:
    curation = replace(
        TEST_CURATION, re_entries=TEST_CURATION.re_entries | {(date(1996, 9, 3), "ZED")}
    )
    with pytest.raises(ValueError, match="no former member holds"):
        build(curation=curation)


@pytest.mark.parametrize("field", ["re_entries", "reused_ticker_adds"])
def test_curated_add_missing_from_the_changes_is_an_error(field: str) -> None:
    extra = frozenset({(date(1996, 8, 2), "BAC")})
    curation = replace(TEST_CURATION, **{field: getattr(TEST_CURATION, field) | extra})
    with pytest.raises(ValueError, match="no matching add"):
        build(curation=curation)


def test_curated_as_both_re_entry_and_reuse_is_an_error() -> None:
    curation = replace(TEST_CURATION, reused_ticker_adds=TEST_CURATION.re_entries)
    with pytest.raises(ValueError, match="both"):
        build(curation=curation)


def test_rename_on_a_day_without_changes_is_an_error() -> None:
    curation = replace(TEST_CURATION, renames=(Rename(date(1996, 5, 2), "XYZ", "XYZW"),))
    with pytest.raises(ValueError, match="has no change"):
        build(curation=curation)


def test_correction_within_the_snapshots_must_not_clash_with_them() -> None:
    clash = Correction(Change(date(1996, 1, 20), added=("XYZ",)), "clash")
    curation = replace(TEST_CURATION, corrections=(clash,))
    with pytest.raises(ValueError, match="still uses"):
        build(curation=curation)


def test_correction_within_the_snapshots_must_not_remove() -> None:
    removal = Correction(Change(date(1996, 1, 20), removed=("BAC",)), "removal")
    curation = replace(TEST_CURATION, corrections=(removal,))
    with pytest.raises(ValueError, match="correction removes"):
        build(curation=curation)


def test_correction_before_the_first_snapshot_is_an_error() -> None:
    early = Correction(Change(date(1995, 12, 29), added=("LIN",)), "too early")
    curation = replace(TEST_CURATION, corrections=(early,))
    with pytest.raises(ValueError, match="before the first components row"):
        build(curation=curation)


@pytest.mark.parametrize("ticker", ["OLD", "BRK-B"])
def test_correction_within_the_snapshots_must_not_take_a_label_still_in_use(ticker: str) -> None:
    # OLD-199603 is last listed on 1996-02-01 but keeps its label until 1996-04-01;
    # BRK.B is listed in later snapshots.
    late = Correction(Change(date(1996, 2, 15), added=(ticker,)), "label in use")
    curation = replace(TEST_CURATION, corrections=(late,))
    with pytest.raises(ValueError, match="still uses"):
        build(curation=curation)


def test_changes_must_follow_the_last_snapshot() -> None:
    with pytest.raises(ValueError, match="after the last components row"):
        build(changes='date,add,remove\n1996-03-01,"ZED",""\n')


def test_suffixed_symbol_after_its_delisting_is_an_error() -> None:
    components = COMPONENTS.replace("OLD-199603", "OLD-199601")
    with pytest.raises(ValueError, match="delist"):
        build(components=components)


# --- the curated lists ------------------------------------------------------------------


def test_curated_aliases_point_unsuffixed_symbols_at_their_suffixed_twin() -> None:
    for unsuffixed, suffixed in CURATION.aliases.items():
        assert split_symbol(unsuffixed)[1] is None
        assert split_symbol(suffixed)[0] == unsuffixed


def test_curated_renames_are_dated_and_unique() -> None:
    keys = [(r.day, r.old) for r in CURATION.renames]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    for rename in CURATION.renames:
        assert rename.old != rename.new
        assert normalize_ticker(rename.old) == rename.old
        assert normalize_ticker(rename.new) == rename.new


def test_curated_corrections_explain_themselves() -> None:
    for correction in CURATION.corrections:
        assert correction.reason
        assert correction.change.added or correction.change.removed


def test_pinned_ref_is_a_commit_sha() -> None:
    assert len(fja05680.PINNED_REF) == 40
    int(fja05680.PINNED_REF, 16)
