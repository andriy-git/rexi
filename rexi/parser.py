"""CLI parser for Rexi."""

import sys
from typing import Optional

import typer
from typing_extensions import Annotated

from rexi.ui.views.regex_view import RexiApp

app = typer.Typer(no_args_is_help=False)


def is_stdin_a_tty() -> bool:
    """Check if stdin is a TTY."""
    return sys.stdin.isatty()


@app.command()
def rexi_cli(
    initial_pattern: Annotated[
        Optional[str],
        typer.Option(
            "--pattern",
            "-p",
            help="Initial regex pattern",
        ),
    ] = None,
    input_file: Annotated[
        Optional[str],
        typer.Option(
            "--input",
            "-i",
            help="Input file path",
        ),
    ] = None,
) -> None:
    """Run the Rexi TUI."""
    input_content = ""
    if input_file:
        try:
            with open(input_file, "r") as f:
                input_content = f.read()
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found.")
            raise typer.Exit(code=1)
    elif not is_stdin_a_tty():
        # Read from stdin
        # We need to open stdin in a way that doesn't conflict with Textual
        # Textual needs stdin to be a TTY, so we read content then reopen stdin as TTY if possible
        # But actually, if we pipe to rexi, stdin is the pipe.
        # Textual app needs to be run with a driver that supports this or we need to handle it.
        # Standard way: read stdin, then open /dev/tty for TUI.
        input_content = sys.stdin.read()
        
        # Reopen stdin as tty for Textual
        if sys.platform != "win32":
            sys.stdin = open("/dev/tty", "r")
    else:
        # No input provided
        print("Error: No input provided. Pipe text to rexi or use --input file.")
        raise typer.Exit(code=1)

    tui = RexiApp(input_content, initial_pattern=initial_pattern)
    tui.run()


if __name__ == "__main__":
    app()
