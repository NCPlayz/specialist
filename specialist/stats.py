import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class Stats:
    """Statistics about a source chunk."""

    specialized: int = 0
    adaptive: int = 0
    unquickened: int = 0

    def __add__(self, other: "Stats") -> "Stats":
        if not isinstance(other, Stats):
            return NotImplemented
        return Stats(
            specialized=self.specialized + other.specialized,
            adaptive=self.adaptive + other.adaptive,
            unquickened=self.unquickened + other.unquickened,
        )

    def __sub__(self, other: "Stats") -> "Stats":
        if not isinstance(other, Stats):
            return NotImplemented
        return Stats(
            specialized=self.specialized - other.specialized,
            adaptive=self.adaptive - other.adaptive,
            unquickened=self.unquickened - other.unquickened,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SourceChunk:
    """A chunk of source code."""

    start: tuple[int, int]
    stop: tuple[int, int]
    stats: Stats
