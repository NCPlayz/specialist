import colorsys
import dataclasses
import html
import json
import typing
from typing_extensions import Self

from .stats import Stats


class Writer(typing.Protocol):
    EXTENSION: typing.ClassVar[str]

    def add(self, source: str, stats: "Stats") -> None:
        ...

    def emit(self) -> str:
        ...

    def copy(self) -> Self:
        ...


class HTMLWriter(Writer):
    """Write HTML for a source code view."""

    EXTENSION: typing.ClassVar[str] = "html"

    def __init__(self, *, blue: bool, dark: bool) -> None:
        self._blue = blue
        self._dark = dark
        background_color, color = ("black", "white") if dark else ("white", "black")
        self._parts = [
            "<!doctype html>",
            "<html>",
            "<head>",
            "<meta http-equiv='content-type' content='text/html;charset=utf-8'/>",
            "</head>",
            f"<body style='background-color:{background_color};color:{color}'>",
            "<pre>",
        ]

    def add(self, source: str, stats: "Stats") -> None:
        """Add a chunk of code to the output."""
        color = self._color(stats)
        attribute = "color" if self._dark else "background-color"
        source = html.escape(source)
        if color != "#ffffff":
            source = f"<span style='{attribute}:{color}'>{source}</span>"
        self._parts.append(source)

    def emit(self) -> str:
        """Emit the HTML."""
        return "".join([*self._parts, "</pre></body></html>"])

    def copy(self) -> Self:
        return HTMLWriter(blue=self._blue, dark=self._dark)

    def _color(self, stats: "Stats") -> str:
        """Compute an RGB color code for this chunk."""
        quickened = stats.specialized + stats.adaptive
        if not quickened:
            return "#ffffff"
        # Red is 0/3, green is 1/3. This gives a hue along the red-green gradient
        # that reflects the hit rate:
        hue = 1 / 3 * stats.specialized / quickened
        if self._blue:
            # This turns our red-green (0/3 to 1/3) gradient into a red-blue (0/3 to
            # -1/3) gradient:
            hue = -hue
        lightness = max(1 / 2, stats.unquickened / (quickened + stats.unquickened))
        # Always fully saturate the color:
        saturation = 1
        rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
        return f"#{int(255 * rgb[0]):02x}{int(255 * rgb[1]):02x}{int(255 * rgb[2]):02x}"


class JSONWriter(Writer):
    EXTENSION: typing.ClassVar[str] = "json"

    def __init__(self, *, indent: int | str | None = None) -> None:
        self._indent = indent
        self._data = []

    def add(self, source: str, stats: "Stats") -> None:
        self._data.append(
            {
                "source": source,
                "stats": dataclasses.asdict(stats),
            }
        )

    def emit(self) -> str:
        """Emit the JSON data"""
        return json.dumps({"data": self._data}, indent=self._indent)

    def copy(self) -> Self:
        return JSONWriter(indent=self._indent)
