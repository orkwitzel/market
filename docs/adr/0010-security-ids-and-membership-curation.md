# 10. Security ids and curated identity fixes for membership

- **Status:** Accepted
- **Date:** 2026-10-05

## Context

Point-in-time membership (ADR 0001) comes from fja05680/sp500 (ADR 0007), which names members by ticker. A ticker is not an identity (`CONTEXT.md`): `BAC` in 1997 is both the old BankAmerica and NationsBank, `DOW` in 2019 is a new company, and `FB` became `META` without leaving the index. Everything downstream (prices, positions, recordings) will key on the security id, so its scheme is hard to change later.

What the upstream files give us:

- The **original** file (1996-01-02 to 2019-01-11) marks delisted securities with a Norgate-style `TICKER-YYYYMM` suffix (month of delisting). Unsuffixed symbols were still listed around 2019 and carry their ~2019 ticker, so pre-2019 renames are invisible and the symbol works as a security key. A few companies appear both unsuffixed and suffixed in 2016-2018 (`AET` and `AET-201811`).
- The **changes** file since 2019 has dated adds and removes by plain ticker; renames show up as a same-day remove plus add.
- The **updated** file strips the suffixes and so merges reused tickers. Not used.

## Decision

- **Security id.** For a security in the original file: its original symbol verbatim (`BAC-199809`, `BAC`, `BRK.B`). For a security first seen later: `<ticker>@<first index date>` (`DOW@2019-04-02`). Ids are opaque strings: code looks securities up by ticker and date, never by building an id. The original file is frozen upstream, so these ids are stable across rebuilds.
- **Ticker labels** are a separate dated table (`tickers`), normalized to price-source form (`BRK-B`). For original-file securities the label is the upstream symbol's base, from the first index date to the end of the delisting month (or open-ended), even where the stock traded under another ticker then (`GOOGL` in 2006). Mapping historical tickers to price sources is left to the prices work (#4).
- **Adds after 2019.** Adding a ticker whose label is still held by a listed non-member is a **re-entry** of that security (true for every case in the data, e.g. `PCG`, `TMUS`, `EQT`); otherwise it is a new security. Delisted (suffixed) securities release their ticker at the end of their delisting month, so `DOW`, `DD`, `Q`, `DELL` become new securities.
- **Curated fixes** live in one module (`market/data/sp500_curation.py`): aliases (unsuffixed/suffixed duplicates of one company), renames, corrections (missing or mislabelled events, each with a reason, e.g. Linde plc in 2018 and the 2020 Ingersoll-Rand/Trane ticker swap) and explicit ticker reuses that override the re-entry default. Each entry is checked against the data; a stale entry fails the build.
- **Pinned source.** The store is built from a pinned upstream commit, bumped deliberately together with a review of the curated lists. The build is byte-for-byte reproducible from that commit.
- **Snapshot dating.** Original-file rows are irregular snapshots; a change between two rows is dated at the later row, so pre-2019 joins and leaves can be late by up to a few weeks.

## Consequences

- The ids encode source details (`-YYYYMM`, `@date`). If a better membership source replaces fja05680, its securities must be mapped onto these ids or the ids migrated; that is a deliberate future decision.
- Curated lists need a human check after each upstream bump. Four post-2025 renames (FI->FISV, MMC->MRSH, BK->BNY, SATS->ECHO) are inferred from the data and the current constituents list, not independently verified.
- A future ticker reuse by a new company of a ticker still held by a listed former member would be read as a re-entry unless it is added to the curated reuses.
- Validated locally against the pinned commit: members on 2026-08-18 match the 503 tickers of upstream `sp500.csv`, and `BAC` resolves to two securities in 1997 and one in 2020.

## Alternatives considered

- **Use the updated file:** simpler, but merges reused tickers into one security, the exact survivorship-style error ADR 0001 exists to avoid.
- **Hash-based or sequential ids:** opaque by construction, but sequential ids shift when upstream history changes and hashes are unreadable in event feeds and debugging.
- **Ticker plus first index date for every security:** uniform, but collides for overlapping securities that both start on 1996-01-02 (`BAC`, `BAC-199809`).
