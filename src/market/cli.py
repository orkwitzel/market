"""The `market` command-line interface."""

import typer

app = typer.Typer(
    name="market",
    help="A historical trading simulator.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """A historical trading simulator."""
