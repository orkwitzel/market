"""Synthetic fja05680/sp500-shaped files, written in code (no real data, ADR 0007).

Tiny CSV strings that mimic the upstream formats: the original suffixed components file
(CRLF, unsorted tickers, ``TICKER-YYYYMM`` delisting suffixes, a class ticker with a dot,
an unsuffixed/suffixed alias artifact) and the changes file (quoted lists, empty cells,
trailing blank lines), plus a curation that fits them.

The scenario: ``BAC`` and ``BAC-199601`` are two securities sharing a ticker; ``AET`` is
an alias artifact of ``AET-199604``; ``XYZ`` leaves and re-enters, is renamed ``XYZW``
and its freed ticker is then taken by a new security; ``OLD-199603`` is delisted and its
ticker reused; ``BAC`` leaves and re-enters; ``LIN`` is added by a correction.
"""

from datetime import date

from market.data.sp500_curation import Correction, Curation, Rename

COMPONENTS = "\r\n".join(
    [
        "date,tickers",
        '1996-01-02,"XYZ,BAC,BAC-199601,AET,BRK.B"',
        '1996-01-10,"BAC-199601,BAC,AET-199604,AET,BRK.B,XYZ"',
        '1996-02-01,"BRK.B,BAC,AET-199604,OLD-199603"',
        '1996-03-01,"XYZ,BAC,AET-199604,BRK.B"',
        "",
    ]
)

CHANGES = "\n".join(
    [
        "date,add,remove",
        '1996-04-01,"OLD","AET"',
        '1996-05-01,"XYZW","XYZ"',
        '1996-06-03,"XYZ",""',
        '1996-07-01,"","BAC"',
        '1996-08-01,"BAC",""',
        '1996-09-03,"ZED","OLD"',
        "",
        "",
        "",
    ]
)

TEST_CURATION = Curation(
    aliases={"AET": "AET-199604"},
    renames=(Rename(date(1996, 5, 1), "XYZ", "XYZW"),),
    corrections=(Correction(date(1996, 2, 15), added=("LIN",), reason="missing upstream"),),
    reused_ticker_adds=frozenset(),
)
