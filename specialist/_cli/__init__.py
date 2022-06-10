import pathlib
from shlex import quote
from typing import Optional, Tuple
import click

from specialist.core import (
    analyze_code,
    analyze_file,
    analyze_module,
    view,
    watch as do_watch,
)
from specialist.watch import DEFAULT_WATCH_PORT

from ._mutex import mutex


@click.group()
def main():
    pass


@main.command(
    context_settings={
        "ignore_unknown_options": True,
    }
)
@mutex(
    "-m",
    default=False,
    is_flag=True,
    disallow=["c"],
    help="Equivalent to: python -m...",
)
@mutex(
    "-c",
    default=False,
    is_flag=True,
    disallow=["m"],
    help="Equivalent to: python -c...",
)
@click.option(
    "--targets",
    default=None,
    help="A glob-style pattern indicating target files to analyze.",
)
@click.option("--output", default=None, help="Output for the reports.")
@click.argument("source")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def run(
    c: Optional[str],
    m: Optional[str],
    targets: Optional[str],
    output: Optional[str],
    source: str,
    args: Tuple[str, ...],
):
    """Analyze your code."""
    argv = " ".join(quote(a) for a in args)

    sources = []
    if targets is not None:
        sources = [p for p in pathlib.Path().glob(targets)]

    if c:
        results = analyze_code(source, argv, targets=sources)
    elif m:
        results = analyze_module(source, argv, targets=sources)
    else:
        results = analyze_file(source, argv, targets=sources)

    out_dir = None
    if output:
        out_dir = pathlib.Path(output)
    view(results, out_dir=out_dir)


@main.command(
    context_settings={
        "ignore_unknown_options": True,
    }
)
@mutex(
    "-m",
    default=False,
    is_flag=True,
    disallow=["c"],
    help="Equivalent to: python -m...",
)
@mutex(
    "-c",
    default=False,
    is_flag=True,
    disallow=["m"],
    help="Equivalent to: python -c...",
)
@click.option(
    "--targets",
    default=None,
    help="A glob-style pattern indicating target files to analyze.",
)
@click.option(
    "--port",
    "-p",
    default=DEFAULT_WATCH_PORT,
    help=f"Set the port for the analysis socket. (Default: {DEFAULT_WATCH_PORT})",
)
@click.argument("source")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def watch(
    c: Optional[str],
    m: Optional[str],
    targets: Optional[str],
    port: int,
    source: str,
    args: Tuple[str, ...],
):
    """Analyze your code (for long-running processes, or async).

    Opens a connection on localhost
    """
    argv = " ".join(quote(a) for a in args)

    sources = []
    if targets is not None:
        sources = [p for p in pathlib.Path().glob(targets)]

    do_watch(targets=sources, port=port)
    click.echo(f"Running! Analysis socket at localhost:{port}")

    if c:
        analyze_code(source, argv, targets=sources)
    elif m:
        analyze_module(source, argv, targets=sources)
    else:
        analyze_file(source, argv, targets=sources)
