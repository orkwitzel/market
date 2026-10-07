"""Build point-in-time S&P 500 membership from fja05680/sp500 (ADR 0001, ADR 0007).

Two upstream files are combined:

- ``S&P 500 Historical Components & Changes.csv``, the *original* file (1996-01-02 to
  2019-01-11). Each row lists the members as of its date, valid until the next row. Its
  symbols tell reused tickers apart: ``BAC-199809`` (old BankAmerica, delisted in
  1998-09) is a different security from ``BAC``. Unsuffixed symbols were still listed
  when the file was built and carry their ~2019 ticker, so pre-2019 renames never appear.
- ``sp500_changes_since_2019.csv``: dated adds and removes after the original file ends.

The upstream "(Updated)" file is not used: it strips the suffixes and so merges reused
tickers into one security. ``sp500_curation`` adds aliases, renames and corrections.

Security ids (ADR 0010): an original-file security's id is its original symbol verbatim
(``BAC-199809``, ``BAC``, ``BRK.B``); a security first seen after that is
``<ticker>@<first index date>`` (``DOW@2019-04-02``). Ids are opaque: look securities
up by ticker with ``Membership.securities_for_ticker``, never by guessing an id.

Ticker labels: an original-file security is labelled with its symbol's base in
normalized form (``BRK.B`` -> ``BRK-B``) from its first index date until the end of its
delisting month (suffixed) or open-ended (unsuffixed). This is the upstream label, not
necessarily the ticker the stock traded under on that date (``GOOGL`` from 2006).
"""

import csv
import io
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import quote

import polars as pl

from market.data.membership import MEMBERSHIP_SCHEMA, TICKERS_SCHEMA, Membership, interval_holds
from market.data.sp500_curation import CURATION, Change, Curation

SOURCE_REPO = "fja05680/sp500"
# Upstream commit the store is built from ("2026-09-07 update"). Pinned so a rebuild is
# reproducible and the curated lists match the data; bump it deliberately.
PINNED_REF = "a2430f2af0c79ddf0748e91de11bdeb1616ab5a7"
COMPONENTS_FILE = "S&P 500 Historical Components & Changes.csv"
CHANGES_FILE = "sp500_changes_since_2019.csv"
DOWNLOAD_TIMEOUT_SECONDS = 60

_SUFFIX = re.compile(r"^(?P<base>.+)-(?P<year>\d{4})(?P<month>\d{2})$")


@dataclass(frozen=True)
class Snapshot:
    """One row of the original file: the raw member symbols on ``day``, sorted."""

    day: date
    symbols: tuple[str, ...]


def normalize_ticker(ticker: str) -> str:
    """Price-source form of a ticker: upper case, share class after a dash (``BRK-B``)."""
    return ticker.strip().upper().replace(".", "-")


def split_symbol(symbol: str) -> tuple[str, date | None]:
    """Split an original-file symbol into its normalized ticker and delisting bound.

    ``TICKER-YYYYMM`` means the security was delisted in that month; the bound returned is
    the first day of the following month (exclusive end). Unsuffixed symbols return
    ``None``: still listed when the file was built.
    """
    match = _SUFFIX.match(symbol)
    if match is None:
        return normalize_ticker(symbol), None
    year, month = int(match["year"]), int(match["month"])
    bound = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return normalize_ticker(match["base"]), bound


def _rows(text: str, header: list[str], name: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text, newline=""))
    first = next(reader, None)
    if first != header:
        raise ValueError(f"{name}: expected header {header}, got {first}")
    return [row for row in reader if any(cell.strip() for cell in row)]


def _split_list(cell: str) -> list[str]:
    return [item.strip() for item in cell.split(",") if item.strip()]


def parse_components(text: str) -> list[Snapshot]:
    """Parse the original components file into snapshots sorted by date."""
    snapshots: dict[date, Snapshot] = {}
    for row in _rows(text, ["date", "tickers"], "components"):
        day = date.fromisoformat(row[0])
        if day in snapshots:
            raise ValueError(f"components: duplicate row for {day}")
        snapshots[day] = Snapshot(day, tuple(sorted(set(_split_list(row[1])))))
    return [snapshots[day] for day in sorted(snapshots)]


def parse_changes(text: str) -> list[Change]:
    """Parse the changes file into changes sorted by date, tickers normalized and sorted."""
    changes: dict[date, Change] = {}
    for row in _rows(text, ["date", "add", "remove"], "changes"):
        day = date.fromisoformat(row[0])
        if day in changes:
            raise ValueError(f"changes: duplicate row for {day}")
        added = sorted({normalize_ticker(t) for t in _split_list(row[1])})
        removed = sorted({normalize_ticker(t) for t in _split_list(row[2])})
        changes[day] = Change(day, tuple(added), tuple(removed))
    return [changes[day] for day in sorted(changes)]


@dataclass
class _Label:
    ticker: str
    start: date
    end: date | None

    def holds(self, day: date) -> bool:
        return interval_holds(self.start, self.end, day)


@dataclass
class _Ledger:
    """Mutable build state: membership intervals and ticker labels per security."""

    closed: list[tuple[str, date, date | None]] = field(
        default_factory=list[tuple[str, date, date | None]]
    )
    open_since: dict[str, date] = field(default_factory=dict[str, date])
    labels: dict[str, list[_Label]] = field(default_factory=dict[str, list[_Label]])

    def knows(self, sid: str) -> bool:
        return sid in self.labels

    def is_member(self, sid: str) -> bool:
        return sid in self.open_since

    def new_security(self, sid: str, ticker: str, day: date, end: date | None = None) -> None:
        """Register ``sid`` with its first label ``ticker`` from ``day`` until ``end``."""
        if sid in self.labels:
            raise ValueError(f"{day}: security {sid} already exists")
        self.labels[sid] = [_Label(ticker, day, end)]

    def current_label(self, sid: str) -> _Label:
        return self.labels[sid][-1]

    def holder(self, ticker: str, day: date) -> str | None:
        """The security whose current label is ``ticker`` on ``day``, if any."""
        holders = sorted(
            sid
            for sid, labels in self.labels.items()
            if labels[-1].ticker == ticker and labels[-1].holds(day)
        )
        if len(holders) > 1:
            raise ValueError(f"{day}: ticker {ticker} is ambiguous between {holders}")
        return holders[0] if holders else None

    def member_holding(self, ticker: str, day: date) -> str | None:
        """The current index member labelled ``ticker`` on ``day``, if any."""
        sid = self.holder(ticker, day)
        return sid if sid is not None and self.is_member(sid) else None

    def join(self, sid: str, day: date) -> None:
        self.open_since[sid] = day

    def leave(self, sid: str, day: date) -> None:
        self.closed.append((sid, self.open_since.pop(sid), day))

    def relabel(self, sid: str, day: date, ticker: str | None) -> None:
        """End the current label of ``sid`` on ``day`` and start ``ticker`` (if any)."""
        self.labels[sid][-1].end = day
        if ticker is not None:
            self.labels[sid].append(_Label(ticker, day, None))

    def to_membership(self) -> Membership:
        intervals = [*self.closed, *((sid, start, None) for sid, start in self.open_since.items())]
        tickers = [
            (sid, label.ticker, label.start, label.end)
            for sid, labels in self.labels.items()
            for label in labels
        ]
        return Membership(
            tickers=pl.DataFrame(tickers, schema=TICKERS_SCHEMA, orient="row"),
            membership=pl.DataFrame(intervals, schema=MEMBERSHIP_SCHEMA, orient="row"),
        )


def _ingest_snapshots(ledger: _Ledger, snapshots: list[Snapshot], curation: Curation) -> None:
    """Membership intervals and labels for every security in the original file."""
    previous: set[str] = set()
    for snapshot in snapshots:
        current = {curation.aliases.get(s, s) for s in snapshot.symbols}
        for sid in sorted(previous - current):
            ledger.leave(sid, snapshot.day)
        for sid in sorted(current - previous):
            ledger.join(sid, snapshot.day)
            if not ledger.knows(sid):
                ticker, delisted = split_symbol(sid)
                ledger.new_security(sid, ticker, snapshot.day, delisted)
        for sid in sorted(current):
            delisted = ledger.current_label(sid).end
            if delisted is not None and snapshot.day >= delisted:
                raise ValueError(f"{sid} is listed on {snapshot.day}, after its delisting")
        previous = current


def _merged_changes(changes: list[Change], curation: Curation) -> list[Change]:
    by_day: dict[date, tuple[set[str], set[str]]] = {}
    for change in [*changes, *(c.change for c in curation.corrections)]:
        added, removed = by_day.setdefault(change.day, (set(), set()))
        added.update(change.added)
        removed.update(change.removed)
    return [
        Change(day, tuple(sorted(by_day[day][0])), tuple(sorted(by_day[day][1])))
        for day in sorted(by_day)
    ]


def _apply_change(ledger: _Ledger, change: Change, curation: Curation) -> None:
    """Apply one day's renames, then removes, then adds."""
    day = change.day
    added, removed = set(change.added), set(change.removed)
    for rename in (r for r in curation.renames if r.day == day):
        if rename.old not in removed or rename.new not in added:
            raise ValueError(f"{day}: rename {rename.old}->{rename.new} is not in the changes")
        sid = ledger.member_holding(rename.old, day)
        if sid is None:
            raise ValueError(f"{day}: rename of {rename.old}, which is not a member")
        if ledger.holder(rename.new, day) is not None:
            raise ValueError(f"{day}: rename to {rename.new}, which is already in use")
        ledger.relabel(sid, day, rename.new)
        removed.discard(rename.old)
        added.discard(rename.new)
    for ticker in sorted(removed):
        sid = ledger.member_holding(ticker, day)
        if sid is None:
            raise ValueError(f"{day}: removal of {ticker}, which is not a member")
        ledger.leave(sid, day)
    for ticker in sorted(added):
        if ledger.member_holding(ticker, day) is not None:
            raise ValueError(f"{day}: addition of {ticker}, which is already a member")
        sid = ledger.holder(ticker, day)
        if sid is not None and (day, ticker) in curation.reused_ticker_adds:
            ledger.relabel(sid, day, None)
            sid = None
        if sid is None:
            sid = f"{ticker}@{day.isoformat()}"
            ledger.new_security(sid, ticker, day)
        ledger.join(sid, day)


def build_membership(
    components_csv: str, changes_csv: str, curation: Curation = CURATION
) -> Membership:
    """Combine the original components file and the changes file into a ``Membership``."""
    snapshots = parse_components(components_csv)
    changes = parse_changes(changes_csv)
    if not snapshots:
        raise ValueError("components: no rows")
    last = snapshots[-1].day
    if changes and changes[0].day <= last:
        raise ValueError(f"changes must start after the last components row ({last})")

    ledger = _Ledger()
    _ingest_snapshots(ledger, snapshots, curation)
    for change in _merged_changes(changes, curation):
        _apply_change(ledger, change, curation)
    return ledger.to_membership()


def raw_url(path: str, ref: str = PINNED_REF) -> str:
    """The raw.githubusercontent.com URL of ``path`` in the upstream repo at ``ref``."""
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{ref}/{quote(path)}"


def fetch_text(url: str) -> str:
    """Download ``url`` as UTF-8 text."""
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        body: bytes = response.read()
    return body.decode("utf-8-sig")


def update_membership_store(directory: Path) -> Membership:
    """Download the upstream files at the pinned commit, build membership, save it."""
    membership = build_membership(
        fetch_text(raw_url(COMPONENTS_FILE)),
        fetch_text(raw_url(CHANGES_FILE)),
        curation=CURATION,
    )
    membership.save(directory)
    return membership
