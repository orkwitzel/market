"""Point-in-time S&P 500 membership: who was in the index on a date (ADR 0001).

A ``Membership`` holds two frames keyed by a stable ``security_id`` (see ``CONTEXT.md``):

``membership``
    security_id: Utf8, start_date: Date, end_date: Date (nullable)
    One row per continuous stretch in the index.
``tickers``
    security_id: Utf8, ticker: Utf8, start_date: Date, end_date: Date (nullable)
    Which ticker labels a security in each period. A ticker can belong to different
    securities in different periods (reuse), and a security can change ticker (rename).

Intervals are start inclusive and end exclusive (``end_date`` is the first day the row no
longer holds); a null ``end_date`` means still open at the end of the data, so queries
after the last known change carry the last state forward. Dates are calendar dates: a
query on a non-trading day returns the state in force on that day.

The store is a directory of Parquet files under the gitignored ``data/`` (ADR 0007).
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Self

import polars as pl

INTERVAL_SCHEMA = {"start_date": pl.Date, "end_date": pl.Date}
MEMBERSHIP_SCHEMA = pl.Schema({"security_id": pl.Utf8, **INTERVAL_SCHEMA})
TICKERS_SCHEMA = pl.Schema({"security_id": pl.Utf8, "ticker": pl.Utf8, **INTERVAL_SCHEMA})
MEMBERS_SCHEMA = pl.Schema({"security_id": pl.Utf8, "ticker": pl.Utf8})
EVENTS_SCHEMA = pl.Schema(
    {"date": pl.Date, "security_id": pl.Utf8, "ticker": pl.Utf8, "event": pl.Utf8}
)

JOIN = "join"
LEAVE = "leave"

MEMBERSHIP_FILE = "membership.parquet"
TICKERS_FILE = "tickers.parquet"


def _active_on(day: date) -> pl.Expr:
    """Rows whose ``[start_date, end_date)`` interval contains ``day``."""
    return (pl.col("start_date") <= day) & (
        pl.col("end_date").is_null() | (pl.col("end_date") > day)
    )


def _check_intervals(frame: pl.DataFrame, name: str, key: str, *, adjacent_ok: bool) -> None:
    """Every interval is non-empty and intervals of the same ``key`` never overlap."""
    if frame.filter(pl.col("end_date") <= pl.col("start_date")).height:
        raise ValueError(f"{name}: every interval must end after it starts")
    same_key = pl.col(key) == pl.col(key).shift(1)
    previous_end = pl.col("end_date").shift(1)
    start = pl.col("start_date")
    too_late = previous_end > start if adjacent_ok else previous_end >= start
    bad = frame.sort(key, "start_date").filter(same_key & (previous_end.is_null() | too_late))
    if bad.height:
        what = "overlap" if adjacent_ok else "overlap or touch"
        raise ValueError(f"{name}: intervals {what} for {bad[key].unique().sort().to_list()}")


class Membership:
    """Point-in-time index membership with dated ticker labels.

    Frames are validated and sorted on construction and must be treated as read-only.
    """

    def __init__(self, tickers: pl.DataFrame, membership: pl.DataFrame) -> None:
        for name, frame, schema in (
            ("tickers", tickers, TICKERS_SCHEMA),
            ("membership", membership, MEMBERSHIP_SCHEMA),
        ):
            if frame.schema != schema:
                raise ValueError(f"{name}: expected schema {schema}, got {frame.schema}")
        if membership.is_empty():
            raise ValueError("membership: no rows")
        _check_intervals(membership, "membership", "security_id", adjacent_ok=False)
        _check_intervals(tickers, "tickers", "security_id", adjacent_ok=True)
        self.tickers = tickers.sort("security_id", "start_date")
        self.membership = membership.sort("security_id", "start_date")
        first = membership["start_date"].min()
        assert isinstance(first, date)
        self.first_date: date = first

    def members_on(self, day: date) -> pl.DataFrame:
        """The index members on ``day`` with their ticker that day, sorted by security id."""
        if day < self.first_date:
            raise ValueError(f"{day} is before membership data begins ({self.first_date})")
        ids = self.membership.filter(_active_on(day)).select("security_id")
        labels = self.tickers.filter(_active_on(day)).select("security_id", "ticker")
        return ids.join(labels, on="security_id", how="left").sort("security_id")

    def events_between(self, start: date, end: date) -> pl.DataFrame:
        """Joins and leaves dated ``start`` to ``end`` inclusive, sorted by date and security id.

        A join is dated its first day in the index; a leave is dated the first day out of it.
        The ticker is the one the security had on its last day in the index for a leave, and
        on its first day for a join.
        """
        dated = pl.col("date").is_between(start, end)
        joins = self.membership.select(
            pl.col("start_date").alias("date"),
            "security_id",
            pl.lit(JOIN).alias("event"),
            pl.col("start_date").alias("label_day"),
        )
        leaves = self.membership.filter(pl.col("end_date").is_not_null()).select(
            pl.col("end_date").alias("date"),
            "security_id",
            pl.lit(LEAVE).alias("event"),
            (pl.col("end_date") - timedelta(days=1)).alias("label_day"),
        )
        events = pl.concat([joins, leaves]).filter(dated)
        labels = events.join(self.tickers, on="security_id", how="inner").filter(
            (pl.col("start_date") <= pl.col("label_day"))
            & (pl.col("end_date").is_null() | (pl.col("end_date") > pl.col("label_day")))
        )
        return (
            events.join(
                labels.select("security_id", "label_day", "ticker"),
                on=["security_id", "label_day"],
                how="left",
            )
            .select(EVENTS_SCHEMA.names())
            .sort("date", "security_id")
        )

    def securities_for_ticker(self, ticker: str, day: date) -> list[str]:
        """The securities labelled ``ticker`` on ``day``, sorted. Usually zero or one."""
        rows = self.tickers.filter((pl.col("ticker") == ticker) & _active_on(day))
        return sorted(rows["security_id"].to_list())

    def ticker_of(self, security_id: str, day: date) -> str | None:
        """The ticker of ``security_id`` on ``day``, or ``None`` if it has none then."""
        rows = self.tickers.filter((pl.col("security_id") == security_id) & _active_on(day))
        return rows["ticker"].item() if rows.height else None

    def save(self, directory: Path) -> None:
        """Write the store as Parquet files into ``directory`` (created if needed)."""
        directory.mkdir(parents=True, exist_ok=True)
        self.membership.write_parquet(directory / MEMBERSHIP_FILE)
        self.tickers.write_parquet(directory / TICKERS_FILE)

    @classmethod
    def load(cls, directory: Path) -> Self:
        """Read a store written by :meth:`save`."""
        return cls(
            tickers=pl.read_parquet(directory / TICKERS_FILE),
            membership=pl.read_parquet(directory / MEMBERSHIP_FILE),
        )
