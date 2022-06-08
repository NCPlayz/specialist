import dis
import opcode

from .stats import Stats

SPECIALIZED_INSTRUCTIONS = frozenset(opcode._specialized_instructions)  # type: ignore # attr is defined


def is_superinstruction(instruction: dis.Instruction) -> bool:
    """Check if an instruction is a superinstruction."""
    return "__" in instruction.opname


def score_instruction(
    instruction: dis.Instruction, previous: dis.Instruction | None
) -> "Stats":
    """Score an instruction's importance."""
    if instruction.opname in SPECIALIZED_INSTRUCTIONS:
        if instruction.opname.endswith("_ADAPTIVE"):
            return Stats(adaptive=True)
        return Stats(specialized=True)
    if (
        previous is not None
        and is_superinstruction(previous)
        and not instruction.is_jump_target
    ):
        return Stats(specialized=True)
    return Stats(unquickened=True)
