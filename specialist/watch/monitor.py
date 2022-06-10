import pathlib
from queue import Queue
from threading import Event, Thread
from typing import TYPE_CHECKING, DefaultDict, List


from .payload import data_dict, Payload

if TYPE_CHECKING:
    from ..core import AnalysisResults


class WatchMonitor(Thread):
    def __init__(self, targets: List[pathlib.Path], /, *, port: int) -> None:
        self._targets = targets
        self._port = port

        self._previous: DefaultDict[
            pathlib.Path, List["AnalysisResults"]
        ] = DefaultDict(list)

        self._queue: Queue[Payload] = Queue()
        self._running = Event()
        super().__init__(name="specialist.watch.monitor")

    def run(self):
        from ..core import _read

        self._running.set()

        while self._running.is_set():
            for t in self._targets:
                result = [r for r in _read(t)]
                previous = self._previous[t]

                if not previous or result != previous:
                    self._previous[t] = result

                    payload = data_dict(t, result)

                    self._queue.put(payload)

    def close(self):
        self._running.clear()

    def start(self):
        from .socket import WatchSocket

        super().start()
        WatchSocket(self._queue, self._running).start()
