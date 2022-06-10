import pathlib
from typing import TYPE_CHECKING, List, TypedDict

from ..writers import JSONPayload, JSONWriter

if TYPE_CHECKING:
    from ..core import AnalysisResults


class Payload(TypedDict):
    path: str
    results: List[JSONPayload]


def data_dict(path: pathlib.Path, result: List["AnalysisResults"]) -> Payload:
    return {
        "path": str(path),
        "results": [JSONWriter.as_dict(source, stats) for source, stats in result],
    }
