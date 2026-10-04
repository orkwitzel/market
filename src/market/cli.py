"""The `market` command-line interface.

The commands are stubs until the layers that implement them land: each one
prints which issue will implement it and exits with code 1, so scripts never
mistake a stub for a successful run.
"""

from typing import NoReturn

import typer

NOT_IMPLEMENTED_EXIT_CODE = 1

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


def _not_implemented(command: str, issue: int) -> NoReturn:
    typer.echo(f"`market {command}` is not implemented yet (see issue #{issue}).", err=True)
    raise typer.Exit(code=NOT_IMPLEMENTED_EXIT_CODE)


@app.command()
def run() -> None:
    """Run a bot through history from its drop date to the present."""
    _not_implemented("run", 7)


@app.command()
def serve() -> None:
    """Serve the local web app."""
    _not_implemented("serve", 19)


@data_app.command()
def update() -> None:
    """Fetch and refresh the local market-data store."""
    _not_implemented("data update", 4)
