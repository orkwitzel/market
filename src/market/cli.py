"""The `market` command-line interface.

Commands not built yet are stubs: each one prints which issue will implement it and
exits with code 1, so scripts never mistake a stub for a successful run.
"""

from pathlib import Path
from typing import Annotated, NoReturn
from urllib.error import URLError

import typer

from market.data import fja05680

NOT_IMPLEMENTED_EXIT_CODE = 1

# The issue that will implement each stub command.
IMPLEMENTING_ISSUE: dict[str, int] = {"run": 7, "serve": 19, "data update": 4}

# Where the local market-data store lives (gitignored, ADR 0007), and its membership part.
DEFAULT_DATA_DIR = Path("data")
MEMBERSHIP_DIR = "membership"

app = typer.Typer(
    name="market",
    help="A historical trading simulator.",
    no_args_is_help=True,
)

data_app = typer.Typer(
    name="data",
    help="Manage the local market-data store.",
    no_args_is_help=True,
)
app.add_typer(data_app)


@app.callback()
def main() -> None:
    """A historical trading simulator."""


def _not_implemented(command: str) -> NoReturn:
    issue = IMPLEMENTING_ISSUE[command]
    typer.echo(f"`market {command}` is not implemented yet (see issue #{issue}).", err=True)
    raise typer.Exit(code=NOT_IMPLEMENTED_EXIT_CODE)


@app.command()
def run() -> None:
    """Run a bot through history from its drop date to the present."""
    _not_implemented("run")


@app.command()
def serve() -> None:
    """Serve the local web app."""
    _not_implemented("serve")


@data_app.command()
def update() -> None:
    """Fetch and refresh the local market-data store."""
    _not_implemented("data update")


@data_app.command()
def membership(
    data_dir: Annotated[Path, typer.Option(help="The local market-data store.")] = DEFAULT_DATA_DIR,
) -> None:
    """Download fja05680/sp500 and rebuild the point-in-time S&P 500 membership store.

    Always builds from the pinned upstream commit (ADR 0010), so the shared store matches
    the curated identity fixes.
    """
    target = data_dir / MEMBERSHIP_DIR
    try:
        built = fja05680.update_membership_store(target)
    except URLError as error:
        typer.echo(f"Download from {fja05680.SOURCE_REPO} failed: {error.reason}", err=True)
        raise typer.Exit(code=1) from error
    securities = built.membership["security_id"].n_unique()
    typer.echo(
        f"Wrote {target}: {securities} securities, "
        f"{built.membership.height} membership intervals from {built.first_date}."
    )
