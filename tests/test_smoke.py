"""Smoke tests: the package imports and the CLI entry point answers --help."""

import importlib

import pytest
from typer.testing import CliRunner

from market.cli import app

SUBPACKAGES = ["data", "engine", "strategies", "allocators", "overlays", "report", "api"]


@pytest.mark.parametrize("name", SUBPACKAGES)
def test_subpackage_imports(name: str) -> None:
    module = importlib.import_module(f"market.{name}")
    assert module.__doc__


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "market" in result.output
