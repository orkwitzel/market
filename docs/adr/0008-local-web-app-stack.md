# 8. Local web app: FastAPI + React, Python 3.14 + Polars/NumPy

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The user wants to configure, launch and watch runs from a browser, served from one codebase, with a polished look suitable for a portfolio. Simulations take minutes. Data licenses forbid public redistribution, so the app runs locally.

## Decision

- **Backend:** Python 3.14, uv, FastAPI (API + serving the built frontend), Typer CLI (`market run`, `market serve`, `market data update`), a background worker process with progress pushed to the browser, SQLite for the run index, Polars for data loading/storage/reporting, NumPy in the engine core, our own indicator module (tested against TA-Lib), pytest + ruff + pyright.
- **Frontend:** React + TypeScript (Vite), Tailwind + shadcn/ui, TradingView lightweight-charts for price/equity charts, ECharts for stacked allocation and report visuals. The replay player fetches a recording once and animates in the browser.
- **Recordings:** Parquet files per run plus the SQLite run index.
- **v1 screens:** run form, run history, replay (playback, equity vs SPY and shadows, allocation, exposure, holdings, explained event feed, stock drill-down) and the report.
- v1 has run history only: no compare view, automatic what-if variants or many-start-date studies yet.

## Consequences

- One `market serve` command runs everything locally.
- Run comparison and multi-start studies are future features built on the run history.
- Historical-context annotations (recessions, market events) are a later viewer feature.

## Alternatives considered

- FastAPI + HTMX (server-rendered): good for forms, poor for a smooth animated replay.
- Static viewer + CLI, Streamlit/Dash, terminal UI.
