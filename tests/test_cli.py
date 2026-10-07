"""The `market` CLI exposes its stub commands, which fail loudly until implemented."""

from datetime import date
from pathlib import Path
from urllib.error import URLError

import pytest
from synthetic_sp500 import CHANGES, COMPONENTS, TEST_CURATION
from typer.testing import CliRunner

from market.cli import IMPLEMENTING_ISSUE, MEMBERSHIP_DIR, NOT_IMPLEMENTED_EXIT_CODE, app
from market.data import fja05680
from market.data.membership import Membership

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
    assert "membership" in result.output


def test_data_membership_downloads_builds_and_saves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    files = {
        fja05680.raw_url(fja05680.COMPONENTS_FILE): COMPONENTS,
        fja05680.raw_url(fja05680.CHANGES_FILE): CHANGES,
    }
    monkeypatch.setattr(fja05680, "fetch_text", files.__getitem__)
    monkeypatch.setattr(fja05680, "CURATION", TEST_CURATION)

    result = runner.invoke(app, ["data", "membership", "--data-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    stored = Membership.load(tmp_path / MEMBERSHIP_DIR)
    assert stored.first_date == date(1996, 1, 2)
    assert "securities" in result.output


def test_data_membership_reports_download_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(url: str) -> str:
        raise URLError("offline")

    monkeypatch.setattr(fja05680, "fetch_text", fail)
    result = runner.invoke(app, ["data", "membership", "--data-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "offline" in result.output


def test_data_membership_has_no_ref_option(tmp_path: Path) -> None:
    result = runner.invoke(app, ["data", "membership", "--data-dir", str(tmp_path), "--ref", "x"])
    assert result.exit_code != 0
    assert "No such option" in result.output
