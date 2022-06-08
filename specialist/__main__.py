import argparse
import os
import pathlib
import runpy
import sys
import tempfile
import typing

from specialist import utils, core, writers


class Args(typing.TypedDict):
    """Command line arguments."""

    blue: bool
    dark: bool
    json: bool
    indent: int | None
    output: pathlib.Path | None
    targets: str | None
    command: typing.Sequence[str]
    module: typing.Sequence[str]
    file: typing.Sequence[str]


def parse_args(args: list[str] | None = None) -> Args:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    options = parser.add_argument_group("Options")
    options.add_argument(
        "-b", "--blue", action="store_true", help="Use a red-blue color scheme."
    )
    options.add_argument(
        "-d", "--dark", action="store_true", help="Use a dark color scheme."
    )
    options.add_argument(
        "--json", action="store_true", help="Return the data in JSON format."
    )
    options.add_argument(
        "-I", "--indent", help="Indent the JSON format data.", type=int,
    )
    options.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )
    options.add_argument(
        "-o",
        "--output",
        metavar="<output>",
        help="A directory to write HTML files to (rather than serving them).",
        type=pathlib.Path,
    )
    options.add_argument(
        "-t",
        "--targets",
        metavar="<targets>",
        help="A glob-style pattern indicating target files to analyze.",
    )
    script = parser.add_argument_group(
        "Script (terminates argument list)"
    ).add_mutually_exclusive_group(required=True)
    script.add_argument(
        "-c",
        action="extend",
        help="Equivalent to: python -c ...",
        nargs="...",
        default=[],
        dest="command",
    )
    script.add_argument(
        "-m",
        action="extend",
        help="Equivalent to: python -m ...",
        nargs="...",
        default=[],
        dest="module",
    )
    script.add_argument(
        "file",
        action="extend",
        help="Equivalent to: python <file> ...",
        nargs="?",
        default=[],
        metavar="<file> ...",
        type=lambda s: [s],
    )
    parser.add_argument(
        action="extend", nargs="...", dest="file", help=argparse.SUPPRESS
    )
    return typing.cast(Args, vars(parser.parse_args(args)))


def main() -> None:
    """Run the main program."""
    args = parse_args()
    blue = args["blue"]
    dark = args["dark"]
    json = args["json"]
    indent = args["indent"]
    output = args["output"]
    targets = args["targets"]
    path: pathlib.Path | None

    if json and (blue or dark):
        print("Cannot have theme arguments enabled with '--json'!", file=sys.stderr)
        sys.exit(-1)

    if not json and indent:
        print("Cannot have '--indent' if format is not JSON!", file=sys.stderr)
        sys.exit(-1)

    with tempfile.TemporaryDirectory() as work:
        match args:
            case {"command": [source, *argv], "module": [], "file": []}:
                path = pathlib.Path(work) / "__main__.py"
                path.write_text(source)
                with utils.patch_sys_argv(argv), utils.catch_exceptions() as caught:
                    runpy.run_path(str(path), run_name="__main__")
            case {"command": [], "module": [source, *argv], "file": []}:
                with utils.patch_sys_argv(argv), utils.catch_exceptions() as caught:
                    runpy.run_module(source, run_name="__main__")
                path = utils.main_file_for_module(source)
            case {"command": [], "module": [], "file": [source, *argv]}:
                with utils.patch_sys_argv(argv), utils.catch_exceptions() as caught:
                    runpy.run_path(source, run_name="__main__")
                path = pathlib.Path(source)
            case _:
                assert False, args
        paths: list[pathlib.Path] = []
        if targets is not None:
            for match in pathlib.Path().glob(targets):
                if core.get_code_for_path(match) is not None:
                    paths.append(match.resolve())
        elif path is not None:
            paths.append(path.resolve())

        if not paths:
            print("No source files found!", file=sys.stderr)
            sys.exit(-1)

        if output is not None:
            common = pathlib.Path(os.path.commonpath(paths)).resolve()
            output = output.resolve()
            path_and_out: typing.Generator[
                tuple[pathlib.Path, pathlib.Path | None], None, None
            ] = (
                (path, output / path.relative_to(common).with_suffix(".html"))
                for path in paths
            )
        else:
            path_and_out = ((path, None) for path in paths)
        for path, out in path_and_out:
            writer = None
            if json:
                writer = writers.JSONWriter(indent=indent)
            core.view(path, writer=writer, out=out)

    if caught:
        raise caught[0] from None


if __name__ == '__main__':
    main()
