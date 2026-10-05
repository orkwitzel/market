"""Shared pytest fixtures. Market data in tests is synthetic only (ADR 0007)."""

import pytest
from synthetic_market import SyntheticMarket, generate_synthetic_market


@pytest.fixture(scope="session")
def synthetic_market() -> SyntheticMarket:
    """The default synthetic market (see ``tests/synthetic_market.py``). Treat as read-only."""
    return generate_synthetic_market()
