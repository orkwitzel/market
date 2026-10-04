"""The `market` CLI exposes its stub commands, which fail loudly until implemented."""

import pytest
from typer.testing import CliRunner

from market.cli import NOT_IMPLEMENTED_EXIT_CODE, app

runner = CliRunner()


@pytest.mark.parametrize(
    ("args", "issue"),
    [(["run"], 7), (["serve"], 19), (["data", "update"], 4)],
)
def test_stub_command_reports_not_implemented(args: list[str], issue: int) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == NOT_IMPLEMENTED_EXIT_CODE != 0
    assert "not implemented yet" in result.output
    assert f"#{issue}" in result.output


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "serve", "data"):
        assert command in result.output


def test_data_help_lists_update() -> None:
    result = runner.invoke(app, ["data", "--help"])
    assert result.exit_code == 0
    assert "update" in result.output
