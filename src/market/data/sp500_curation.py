"""Hand-maintained fixes on top of the fja05680/sp500 membership files.

The upstream files identify companies by ticker, which is not enough to know *which
security* a row means (``CONTEXT.md``: a ticker is only a label for a period). These lists
supply the missing identity facts. Every entry is checked against the data when the store
is built, so a stale entry fails the build instead of silently doing nothing.

All tickers here are in normalized (price-source) form: ``BRK-B``, not ``BRK.B``.
Maintenance: after bumping ``fja05680.PINNED_REF``, review every new same-day
remove-and-add pair in ``sp500_changes_since_2019.csv``; a pure ticker change belongs in
``RENAMES``, otherwise it is a real index change.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Rename:
    """A security changed ticker from ``old`` to ``new``, effective ``day``.

    The changes file records a rename as a same-day remove(old) plus add(new); without
    this entry the build would treat it as one company leaving and another joining, which
    would force the bot into a spurious exit and re-entry.
    """

    day: date
    old: str
    new: str


@dataclass(frozen=True)
class Change:
    """Tickers added to and removed from the index on ``day``, normalized and sorted.

    One row of upstream's changes file, or the events of a curated correction.
    """

    day: date
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


@dataclass(frozen=True)
class Correction:
    """A ``change`` the upstream files miss or mislabel, merged into them, and why."""

    change: Change
    reason: str


@dataclass(frozen=True)
class Curation:
    """Identity fixes applied while building membership.

    ``aliases``
        Original-file symbol -> the symbol of the same security. Used for artifacts where
        one company appears both unsuffixed and suffixed (for example ``AET`` and
        ``AET-201811`` are both Aetna). Keys and values are raw original-file symbols.
    ``renames``
        Ticker changes after 2019, sorted by date.
    ``corrections``
        Events the upstream files miss or mislabel.
    ``reused_ticker_adds``
        ``(day, ticker)`` adds that are a *new* security even though an earlier security
        still holds the ticker label. By default an add of a ticker still held by a
        listed non-member is a re-entry of that security.
    """

    aliases: Mapping[str, str] = field(default_factory=dict[str, str])
    renames: tuple[Rename, ...] = ()
    corrections: tuple[Correction, ...] = ()
    reused_ticker_adds: frozenset[tuple[date, str]] = frozenset()


# Unsuffixed symbols that vanish before the original file's last row (2019-01-11) while a
# same-base suffixed symbol covering the same period exists: one security listed twice in
# 2016-2018. Distinct same-base pairs (AN, ATI, CB, ITT, S, AGN, ...) are not aliases.
ALIASES: dict[str, str] = {
    "AET": "AET-201811",  # Aetna, acquired by CVS 2018-11
    "ANDV": "ANDV-201809",  # Andeavor, acquired by Marathon Petroleum 2018-10
    "CA": "CA-201811",  # CA Inc, acquired by Broadcom 2018-11
    "COL": "COL-201811",  # Rockwell Collins, acquired by United Technologies 2018-11
    "ESRX": "ESRX-201812",  # Express Scripts, acquired by Cigna 2018-12
    "EVHC": "EVHC-201810",  # Envision Healthcare, taken private 2018-10
    "GGP": "GGP-201808",  # GGP Inc, acquired by Brookfield Property 2018-08
    "PX": "PX-201810",  # Praxair, combined into Linde plc 2018-10
    "SCG": "SCG-201812",  # SCANA, acquired by Dominion 2019-01
    "XL": "XL-201809",  # XL Group, acquired by AXA 2018-09
}

# Ticker changes of the same security, dated as in sp500_changes_since_2019.csv.
RENAMES: tuple[Rename, ...] = (
    Rename(date(2019, 6, 1), "HRS", "LHX"),  # Harris -> L3Harris
    Rename(date(2019, 6, 3), "DWDP", "DD"),  # DowDuPont -> DuPont (not the old DD)
    Rename(date(2019, 8, 8), "TMK", "GL"),  # Torchmark -> Globe Life
    Rename(date(2019, 10, 18), "BHGE", "BKR"),  # Baker Hughes, a GE company -> Baker Hughes
    Rename(date(2019, 11, 5), "HCP", "PEAK"),  # HCP -> Healthpeak
    Rename(date(2019, 11, 5), "SYMC", "NLOK"),  # Symantec -> NortonLifeLock
    Rename(date(2019, 12, 5), "CBS", "VIAC"),  # CBS -> ViacomCBS (CBS was the survivor)
    Rename(date(2019, 12, 9), "BBT", "TFC"),  # BB&T -> Truist
    Rename(date(2019, 12, 10), "JEC", "J"),  # Jacobs Engineering
    Rename(date(2020, 3, 3), "IR", "TT"),  # Ingersoll-Rand plc -> Trane (see CORRECTIONS)
    Rename(date(2020, 4, 3), "UTX", "RTX"),  # United Technologies -> Raytheon Technologies
    Rename(date(2020, 4, 6), "ARNC", "HWM"),  # Arconic Inc -> Howmet Aerospace
    Rename(date(2020, 9, 18), "CTL", "LUMN"),  # CenturyLink -> Lumen
    Rename(date(2021, 8, 3), "LB", "BBWI"),  # L Brands -> Bath & Body Works
    Rename(date(2021, 10, 4), "COG", "CTRA"),  # Cabot Oil & Gas -> Coterra
    Rename(date(2022, 1, 10), "WLTW", "WTW"),  # Willis Towers Watson
    Rename(date(2022, 2, 17), "VIAC", "PARA"),  # ViacomCBS -> Paramount Global
    Rename(date(2022, 4, 11), "DISCA", "WBD"),  # Discovery -> Warner Bros. Discovery
    Rename(date(2022, 5, 10), "BLL", "BALL"),  # Ball Corp
    Rename(date(2022, 6, 9), "FB", "META"),  # Facebook -> Meta Platforms
    Rename(date(2022, 6, 28), "ANTM", "ELV"),  # Anthem -> Elevance Health
    Rename(date(2022, 11, 8), "NLOK", "GEN"),  # NortonLifeLock -> Gen Digital
    Rename(date(2023, 5, 16), "PKI", "RVTY"),  # PerkinElmer -> Revvity
    Rename(date(2023, 6, 7), "FISV", "FI"),  # Fiserv
    Rename(date(2023, 7, 10), "RE", "EG"),  # Everest Re -> Everest Group
    Rename(date(2023, 8, 30), "ABC", "COR"),  # AmerisourceBergen -> Cencora
    Rename(date(2024, 2, 1), "CDAY", "DAY"),  # Ceridian -> Dayforce
    Rename(date(2024, 3, 4), "PEAK", "DOC"),  # Healthpeak (survived the Physicians Realty merger)
    Rename(date(2024, 3, 25), "FLT", "CPAY"),  # FleetCor -> Corpay
    # The four below are inferred from same-day pairs and the current Wikipedia list, which
    # gives the new ticker the old one's index date; not independently verified.
    Rename(date(2025, 11, 11), "FI", "FISV"),  # Fiserv, back to FISV
    Rename(date(2026, 1, 14), "MMC", "MRSH"),  # Marsh McLennan
    Rename(date(2026, 5, 21), "BK", "BNY"),  # Bank of New York Mellon -> BNY
    Rename(date(2026, 6, 24), "SATS", "ECHO"),  # EchoStar
)

CORRECTIONS: tuple[Correction, ...] = (
    Correction(
        Change(date(2018, 10, 31), added=("LIN",)),
        reason=(
            "Linde plc replaced Praxair (PX-201810) on 2018-10-31; the original file has no"
            " LIN and the changes file starts in 2019, so upstream patches it in separately."
        ),
    ),
    Correction(
        Change(date(2020, 3, 3), added=("IR",), removed=("IR",)),
        reason=(
            "The changes file records add TT / remove XEC. In fact Ingersoll-Rand plc (IR, a"
            " member) renamed itself Trane Technologies (TT), and Gardner Denver took the IR"
            " ticker and joined the index (Wikipedia: IR added 2020-03-03, TT 2010-11-17)."
        ),
    ),
)

CURATION = Curation(aliases=ALIASES, renames=RENAMES, corrections=CORRECTIONS)
