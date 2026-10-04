"""Smoke tests: every subpackage imports. CLI behaviour is tested in ``test_cli.py``."""

import importlib

import pytest

SUBPACKAGES = ["data", "engine", "strategies", "allocators", "overlays", "report", "api"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    module = importlib.import_module(f"market.{name}")
    assert module.__doc__
