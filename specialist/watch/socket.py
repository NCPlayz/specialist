import socket
import struct
from threading import Thread, Event
from queue import Empty, Queue

import msgpack

from . import DEFAULT_WATCH_PORT
from ..utils import MISSING
from .payload import Payload


class WatchSocket(Thread):
    def __init__(self, queue: Queue[Payload], running: Event):
        self._socket: socket.socket = MISSING
        self._queue = queue
        self.running = running
        super().__init__(name="specialist.watch.socket")

    def setup(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((socket.gethostname(), DEFAULT_WATCH_PORT))
        self._socket.listen(1)

    def accept(self):
        while self.running.is_set():
            sock, _ = self._socket.accept()

            thread = WatchThread(sock, self._queue, self.running)
            thread.start()

    def run(self):
        self.setup()
        self.accept()


MSG_LEN = 1024

# Payload format:
# 4 bytes for length
# Rest for content


class WatchThread(Thread):
    def __init__(self, sock: socket.socket, queue: Queue[Payload], running: Event):
        self._sock = sock
        self._queue = queue
        self.running = running
        super().__init__(name="specialist.watch.stream")

    def run(self):
        while self.running.is_set():
            try:
                payload = self._queue.get_nowait()
            except Empty:
                continue

            as_bytes = msgpack.packb(payload)
            total_length = len(as_bytes)

            msg = struct.pack("!I", total_length) + as_bytes
            self._sock.sendall(msg)
