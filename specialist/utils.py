import contextlib
import http.server
import importlib.util
import pathlib
import sys
from types import CodeType
import types
import typing
import webbrowser

from . import CODE

__all__ = (
    "catch_exceptions",
    "patch_sys_argv",
    "main_file_for_module",
    "browse",
)


@contextlib.contextmanager
def catch_exceptions() -> typing.Generator[list[BaseException], None, None]:
    """Suppress exceptions, and gather them into a list."""
    caught: list[BaseException] = []
    try:
        yield caught
    except BaseException as exception:
        caught.append(exception)


@contextlib.contextmanager
def patch_sys_argv(argv: typing.Iterable[str]) -> typing.Generator[None, None, None]:
    """Patch sys.argv to simulate a command line."""
    sys_argv = sys.argv[1:]
    sys.argv[1:] = argv
    try:
        yield
    finally:
        sys.argv[1:] = sys_argv


def main_file_for_module(module: str) -> pathlib.Path | None:
    """Get the main file for a module."""
    spec = importlib.util.find_spec(module)
    if spec is None:
        return None
    if spec.submodule_search_locations is not None:
        spec = importlib.util.find_spec(f"{module}.__main__")
        if spec is None:
            return None
    if not spec.has_location:
        return None
    assert spec.origin is not None
    return pathlib.Path(spec.origin)


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


def get_code_for_path(path: pathlib.Path) -> CodeType | None:
    """Get the code object for a file."""
    for code in CODE:
        try:
            if path.samefile(code.co_filename):
                return code
        except FileNotFoundError:
            pass
    return None


def validate_targets(
    path: typing.Optional[pathlib.Path], targets: typing.List[pathlib.Path]
) -> typing.List[pathlib.Path]:
    paths = []

    if targets:
        for target in targets:
            if get_code_for_path(target) is not None:
                paths.append(target.resolve())
    elif path is not None:
        paths.append(path.resolve())

    if not paths:
        raise FileNotFoundError("No source files found!")

    return paths


def audit_imports(event: str, args: "typing.Sequence[object]") -> None:
    """Intercept all exec() calls and grab a reference to the code they execute.

    This is the only way I know of to actually get ahold of module-level code
    objects without modifying the code being run.
    """
    match event, args:
        case "exec", [types.CodeType(co_name="<module>") as code]:
            CODE.add(code)


class _Missing:
    __slots__ = ()

    def __repr__(self) -> str:
        return "MISSING"


MISSING: typing.Any = _Missing()
