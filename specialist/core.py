import collections
import dis
import http.server
import itertools
import pathlib
import sys
import typing
import types
import webbrowser

from . import CODE
from .stats import Stats, SourceChunk
from .instructions import score_instruction
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


def read(path: pathlib.Path) -> typing.Iterable[typing.Tuple[str, Stats]]:
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


def view(
    path: pathlib.Path,
    *,
    writer: typing.Optional[Writer] = None,
    out: pathlib.Path | None,
) -> None:
    """View a code object's source code."""
    if writer is None:
        writer = HTMLWriter(blue=False, dark=False)

    for source, stats in read(path):
        writer.add(source, stats)

    written = writer.emit()
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        out.write_text(written)
        print(f"{path} -> {out}")
    else:
        browse(written)


def browse(page: str) -> None:
    """Open a web browser to display a page."""

    class RequestHandler(http.server.BaseHTTPRequestHandler):
        """A simple handler for a single web page."""

        def do_GET(self) -> None:  # pylint: disable = invalid-name
            """Serve the given HTML."""
            self.send_response(200)
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))

        def log_request(self, *_: object) -> None:
            """Don't log requests."""

    with http.server.HTTPServer(("localhost", 0), RequestHandler) as server:
        webbrowser.open_new_tab(f"http://localhost:{server.server_port}")
        server.handle_request()
