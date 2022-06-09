"""Visualize CPython 3.11's specializing, adaptive interpreter."""
import sys
import types
import typing

if sys.version_info < (3, 11) or sys.implementation.name != "cpython":
    raise RuntimeError("Specialist only supports CPython 3.11+!")

CODE = set()


@sys.addaudithook
def audit_imports(event: str, args: "typing.Sequence[object]") -> None:
    """Intercept all exec() calls and grab a reference to the code they execute.

    This is the only way I know of to actually get ahold of module-level code
    objects without modifying the code being run.
    """
    match event, args:
        case "exec", [types.CodeType(co_name="<module>") as code]:
            CODE.add(code)
