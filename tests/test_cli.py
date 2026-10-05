"""The `market` CLI exposes its stub commands, which fail loudly until implemented."""

import pytest
from typer.testing import CliRunner

from market.cli import IMPLEMENTING_ISSUE, NOT_IMPLEMENTED_EXIT_CODE, app

runner = CliRunner()


@pytest.mark.parametrize("command", sorted(IMPLEMENTING_ISSUE))
def test_stub_command_reports_not_implemented(command: str) -> None:
    result = runner.invoke(app, command.split())
    assert result.exit_code == NOT_IMPLEMENTED_EXIT_CODE != 0
    assert "not implemented yet" in result.output
    assert f"#{IMPLEMENTING_ISSUE[command]}" in result.output


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "serve", "data"):
        assert command in result.output


def test_data_help_lists_update() -> None:
    result = runner.invoke(app, ["data", "--help"])
    assert result.exit_code == 0
    assert "update" in result.output
