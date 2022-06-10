"""Visualize CPython 3.11's specializing, adaptive interpreter."""
import pathlib
import sys
import types
import typing

if sys.version_info < (3, 11) or sys.implementation.name != "cpython":
    raise RuntimeError("Specialist only supports CPython 3.11+!")

CODE: typing.Set[types.CodeType] = set()


from .core import (
    analyze_code as analyze_code,
    analyze_file as analyze_file,
    analyze_module as analyze_module,
    watch as watch,
)
