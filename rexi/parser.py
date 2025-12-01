"""CLI parser for Rexi."""

import os
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
        input_content = sys.stdin.read()
        
        # Reopen stdin as tty for Textual
        if sys.platform != "win32":
            # Open the TTY
            tty = open("/dev/tty", "r")
            # Duplicate the TTY file descriptor to standard input (fd 0)
            os.dup2(tty.fileno(), 0)
            # Update sys.stdin to point to the new file descriptor
            sys.stdin = os.fdopen(0, "r")
    else:
        # No input provided
        print("Error: No input provided. Pipe text to rexi or use --input file.")
        raise typer.Exit(code=1)

    tui = RexiApp(input_content, initial_pattern=initial_pattern)
    tui.run()


if __name__ == "__main__":
    app()
