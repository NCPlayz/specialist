import collections
import dis
import http.server
import itertools
import os
import pathlib
import runpy
import sys
import tempfile
import typing
import types
import webbrowser


from . import CODE
from .instructions import score_instruction
from .stats import Stats, SourceChunk
from .utils import catch_exceptions, main_file_for_module, patch_sys_argv
from .writers import Writer, HTMLWriter

FIRST_POSTION = (1, 0)
LAST_POSITION = (sys.maxsize, 0)


def walk_code(code: types.CodeType) -> typing.Generator[types.CodeType, None, None]:
    """Walk a code object, yielding all of its sub-code objects."""
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from walk_code(constant)


def parse(code: types.CodeType) -> typing.Generator[SourceChunk, None, None]:
    """Parse a code object's source code into SourceChunks."""
    events: collections.defaultdict[tuple[int, int], Stats] = collections.defaultdict(
        Stats
    )
    events[FIRST_POSTION] = Stats()
    events[LAST_POSITION] = Stats()
    previous = None
    for child in walk_code(code):
        # dis has a bug in how position information is computed for CACHEs:
        fixed_positions = list(child.co_positions())
        for instruction in dis.get_instructions(child, adaptive=True):
            position = fixed_positions[instruction.offset // 2]
            lineno, end_lineno, col_offset, end_col_offset = position
            if (
                lineno is None
                or end_lineno is None
                or col_offset is None
                or end_col_offset is None
            ):
                previous = instruction
                continue
            stats = score_instruction(instruction, previous)
            events[lineno, col_offset] += stats
            events[end_lineno, end_col_offset] -= stats
            previous = instruction
    stats = Stats()
    for (start, event), (stop, _) in itertools.pairwise(sorted(events.items())):
        stats += event
        yield SourceChunk(start, stop, stats)


def get_code_for_path(path: pathlib.Path) -> types.CodeType | None:
    """Get the code object for a file."""
    for code in CODE:
        try:
            if path.samefile(code.co_filename):
                return code
        except FileNotFoundError:
            pass
    return None


AnalysisResults = typing.Iterable[typing.Tuple[str, Stats]]


def _read(path: pathlib.Path) -> AnalysisResults:
    """Read the code and accumulate the results."""
    code = get_code_for_path(path)
    assert code is not None
    parser = parse(code)
    chunk = next(parser)
    group = bytearray()
    with path.open("rb") as file:
        for lineno, line in enumerate(file, 1):
            for col_offset, character in enumerate(line):
                if chunk.stop == (lineno, col_offset):
                    yield group.decode("utf-8"), chunk.stats
                    group.clear()
                    chunk = next(parser)
                    assert chunk.start == (lineno, col_offset)
                group.append(character)
    yield group.decode("utf-8"), chunk.stats


def _process_analysis(
    path: typing.Optional[pathlib.Path],
    targets: typing.List[pathlib.Path],
    caught: typing.List[BaseException],
):
    paths = []

    if targets:
        for target in targets:
            if get_code_for_path(target) is not None:
                paths.append(target.resolve())
    elif path is not None:
        paths.append(path.resolve())

    if not paths:
        raise FileNotFoundError("No source files found!")

    if caught:
        raise caught[0] from None

    return paths


PathToResults = typing.Dict[pathlib.Path, AnalysisResults]


def analyze_code(
    code: str, /, *argv: str, targets: typing.List[pathlib.Path]
) -> PathToResults:
    with tempfile.TemporaryDirectory() as work:
        path = pathlib.Path(work) / "__main__.py"
        path.write_text(code)
        with patch_sys_argv(argv), catch_exceptions() as caught:
            runpy.run_path(str(path), run_name="__main__")

        paths = _process_analysis(path, targets, caught)
        return {p: _read(p) for p in paths}


def analyze_module(
    module: str, /, *argv: str, targets: typing.List[pathlib.Path]
) -> PathToResults:
    with patch_sys_argv(argv), catch_exceptions() as caught:
        runpy.run_module(module, run_name="__main__")
    path = main_file_for_module(module)
    paths = _process_analysis(path, targets, caught)
    return {p: _read(p) for p in paths}


def analyze_file(
    source: str, /, *argv: str, targets: typing.List[pathlib.Path]
) -> PathToResults:
    with patch_sys_argv(argv), catch_exceptions() as caught:
        runpy.run_path(source, run_name="__main__")
    path = pathlib.Path(source)
    paths = _process_analysis(path, targets, caught)
    return {p: _read(p) for p in paths}


def view(
    results: PathToResults,
    *,
    writer: typing.Optional[Writer] = None,
    out_dir: pathlib.Path | None,
) -> None:
    """View a code object's source code."""
    if writer is None:
        writer = HTMLWriter(blue=False, dark=False)

    common_path = pathlib.Path(os.path.commonpath(list(results.keys()))).resolve()
    if out_dir is not None:
        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

    for p, r in results.items():
        writer = writer.copy()

        for source, stats in r:
            writer.add(source, stats)

        written = writer.emit()

        if out_dir is not None:
            out_file = out_dir / p.relative_to(common_path).with_suffix(
                f".{writer.EXTENSION}"
            )
            out_file.unlink(missing_ok=True)
            out_file.write_text(written)
        else:
            browse(written)


def browse(page: str) -> None:
    """Open a web browser to display a page."""

    class RequestHandler(http.server.BaseHTTPRequestHandler):
        """A simple handler for a single web page."""

        def do_GET(self) -> None:
            """Serve the given HTML."""
            self.send_response(200)
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))

        def log_request(self, *_: object) -> None:
            """Don't log requests."""

    with http.server.HTTPServer(("localhost", 0), RequestHandler) as server:
        webbrowser.open_new_tab(f"http://localhost:{server.server_port}")
        server.handle_request()
