import contextlib
import importlib.util
import pathlib
import sys
import typing


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
